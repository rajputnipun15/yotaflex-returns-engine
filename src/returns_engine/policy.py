"""Deterministic eligibility and serialized cumulative quantity reservations."""

from datetime import datetime, timedelta, timezone
import json
from .ids import allocate_id
from .schema import transaction
from .events import record_event

BUSINESS_TZ = timezone(timedelta(hours=5, minutes=30))


def parse_time(value):
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def reserved_quantity(conn, order_line_id):
    # Cancelled/superseded approvals release only if no shipment ever used them.
    return conn.execute('''SELECT COALESCE(SUM(a.approved_quantity),0)
        FROM AuthorizationLine a JOIN ReturnAuthorization h ON h.id=a.authorization_id
        JOIN ReturnLine l ON l.id=a.return_line_id WHERE l.order_line_id=? AND
        (h.state IN ('ISSUED','CONSUMED') OR EXISTS(
          SELECT 1 FROM ShipmentLine s WHERE s.authorization_line_id=a.id))''', (order_line_id,)).fetchone()[0]


def evaluate_line(conn, line_id, config):
    row=conn.execute('''SELECT l.*,r.requested_at,r.override_reason,r.order_id AS request_order,
        o.order_id AS original_order,o.quantity,o.id AS original_id,p.category,h.delivered_at,
        pol.window_days,pol.effective_from,pol.effective_to,pol.excluded_categories_json
        FROM ReturnLine l JOIN ReturnRequest r ON r.id=l.request_id
        JOIN OrderLine o ON o.id=l.order_line_id JOIN Product p ON p.id=o.product_id
        JOIN "Order" h ON h.id=o.order_id JOIN ReturnPolicy pol ON pol.id=r.policy_id
        WHERE l.id=?''',(line_id,)).fetchone()
    if row is None: raise ValueError("Return line/purchase does not exist")
    remaining=max(0,row["quantity"]-reserved_quantity(conn,row["original_id"]))
    result={"requested_quantity":row["requested_quantity"],"available_quantity":remaining,"eligible_quantity":0,"reason_code":"ELIGIBLE"}
    requested=parse_time(row["requested_at"])
    delivered=parse_time(row["delivered_at"]) if row["delivered_at"] else None
    category=config["categories"].get(row["category"])
    if category is None: raise ValueError("Product category missing from policy configuration")
    days=category.get("window_days",row["window_days"])
    deadline=delivered.astimezone(BUSINESS_TZ).date()+timedelta(days=days) if delivered else None
    result["deadline_date"]=deadline.isoformat() if deadline else None
    if row["request_order"] != row["original_order"]: reason="ORDER_LINE_MISMATCH"
    elif not delivered or requested < delivered: reason="NOT_DELIVERED"
    elif requested < parse_time(row["effective_from"]) or (row["effective_to"] and requested >= parse_time(row["effective_to"])): reason="POLICY_NOT_EFFECTIVE"
    elif row["override_reason"]: reason="OVERRIDE_UNSUPPORTED"
    elif not category["returnable"] or row["category"] in json.loads(row["excluded_categories_json"]): reason="CATEGORY_EXCLUDED"
    elif requested.astimezone(BUSINESS_TZ).date() > deadline: reason="WINDOW_EXPIRED"
    elif row["requested_quantity"] > row["quantity"]: reason="QTY_EXCEEDS_PURCHASED"
    elif remaining==0: reason="NO_REMAINING_QUANTITY"
    else:
        result["eligible_quantity"]=min(row["requested_quantity"],remaining)
        reason="PARTIAL_REMAINING_QUANTITY" if result["eligible_quantity"]<row["requested_quantity"] else "ELIGIBLE"
    result["reason_code"]=reason
    return result


def authorize_request(conn, request_id, config):
    """One approval per request, evaluated under the same serialized write lock.

    The generator uses only ISSUED/CONSUMED approvals. Amendments are not exposed.
    Pending requests have no reservation; rejected lines have no allocation.
    """
    with transaction(conn):
        request=conn.execute("SELECT * FROM ReturnRequest WHERE id=?",(request_id,)).fetchone()
        if not request or request["state"]!="REQUESTED" or conn.execute("SELECT 1 FROM ReturnAuthorization WHERE request_id=?",(request_id,)).fetchone():
            raise ValueError("Request must be pending and not previously authorized")
        lines=list(conn.execute("SELECT * FROM ReturnLine WHERE request_id=? ORDER BY line_sequence",(request_id,)))
        if not lines: raise ValueError("Request has no return lines")
        header=None
        decisions=[]
        for line in lines:
            decision=evaluate_line(conn,line["id"],config)
            attempt_id=allocate_id(conn,"ActionAttempt")
            conn.execute('''INSERT INTO ActionAttempt(id,ReturnLine_id,action,payload_json,decision,reason_code,attempted_at,correlation_id)
                VALUES(?,?,'AUTHORIZE',?,?,?,?,?)''',(attempt_id,line["id"],json.dumps(decision,sort_keys=True,separators=(",",":")),
                    "ALLOWED" if decision["eligible_quantity"] else "BLOCKED",decision["reason_code"],request["requested_at"],request_id))
            eligible=decision["eligible_quantity"]
            if eligible:
                if header is None:
                    header=allocate_id(conn,"ReturnAuthorization")
                    conn.execute("INSERT INTO ReturnAuthorization VALUES(?,?,?,'ISSUED')",(header,request_id,request["requested_at"]))
                    record_event(conn,"ReturnAuthorization",header,event_type="CREATED",occurred_at=request["requested_at"],reason_code="APPROVAL_ISSUED",correlation_id=request_id)
                allocation=allocate_id(conn,"AuthorizationLine")
                conn.execute("INSERT INTO AuthorizationLine VALUES(?,?,?,?)",(allocation,header,line["id"],eligible))
                record_event(conn,"AuthorizationLine",allocation,event_type="CREATED",occurred_at=request["requested_at"],reason_code="QUANTITY_RESERVED",correlation_id=request_id)
                state="APPROVED" if eligible==line["requested_quantity"] else "PARTIALLY_APPROVED"
            else: state="REJECTED"
            record_event(conn,"ReturnLine",line["id"],event_type="STATE_CHANGED",occurred_at=request["requested_at"],reason_code=decision["reason_code"],correlation_id=request_id,new_state=state,attempt_id=attempt_id)
            decisions.append(decision)
        total=sum(d["eligible_quantity"] for d in decisions)
        requested=sum(d["requested_quantity"] for d in decisions)
        state="REJECTED" if total==0 else ("APPROVED" if total==requested else "PARTIALLY_APPROVED")
        record_event(conn,"ReturnRequest",request_id,event_type="STATE_CHANGED",occurred_at=request["requested_at"],reason_code="ELIGIBILITY_EVALUATED",correlation_id=request_id,new_state=state)
        return header, decisions


def cancel_authorization(conn, authorization_id, occurred_at):
    """Release unconsumed reservations; refuse cancellation that shifts used unit positions."""
    with transaction(conn):
        header=conn.execute("SELECT * FROM ReturnAuthorization WHERE id=?",(authorization_id,)).fetchone()
        if not header or header["state"]!="ISSUED": raise ValueError("Only an issued unused authorization can be cancelled")
        if conn.execute('''SELECT 1 FROM ShipmentLine s JOIN AuthorizationLine a ON a.id=s.authorization_line_id
            WHERE a.authorization_id=?''',(authorization_id,)).fetchone():
            raise ValueError("Cannot release shipped or received quantities")
        if conn.execute('''SELECT 1 FROM AuthorizationLine a JOIN ReturnLine l ON l.id=a.return_line_id
            JOIN AuthorizationLine b ON b.id<>a.id JOIN ReturnLine m ON m.id=b.return_line_id
            WHERE a.authorization_id=? AND m.order_line_id=l.order_line_id AND b.rowid>a.rowid''',(authorization_id,)).fetchone():
            raise ValueError("Later allocations exist; cancellation would shift unit positions")
        record_event(conn,"ReturnAuthorization",authorization_id,event_type="STATE_CHANGED",occurred_at=occurred_at,
            reason_code="UNCONSUMED_RESERVATION_RELEASED",correlation_id=authorization_id,new_state="CANCELLED")
        for line in conn.execute('''SELECT l.id,l.state FROM ReturnLine l JOIN AuthorizationLine a ON a.return_line_id=l.id
            WHERE a.authorization_id=? ORDER BY l.id''',(authorization_id,)).fetchall():
            record_event(conn,"ReturnLine",line["id"],event_type="STATE_CHANGED",occurred_at=occurred_at,
                reason_code="UNCONSUMED_RESERVATION_RELEASED",correlation_id=authorization_id,new_state="CANCELLED")
        record_event(conn,"ReturnRequest",header["request_id"],event_type="STATE_CHANGED",occurred_at=occurred_at,
            reason_code="UNCONSUMED_RESERVATION_RELEASED",correlation_id=authorization_id,new_state="CANCELLED")
