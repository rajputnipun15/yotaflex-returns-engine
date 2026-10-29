"""Independent baseline checks and measured metrics; no ground-truth input."""

from collections import Counter, defaultdict
from datetime import timedelta
from functools import lru_cache
import json
import re

from .ids import PREFIXES
from .model import TABLES, TARGETS, TRANSITIONS
from .money import basis_points, allocate_proportional
from .policy import parse_time, BUSINESS_TZ
from .schema import quote


@lru_cache(maxsize=200000)
def valid_time(value):
    try:
        return parse_time(value).strftime("%Y-%m-%dT%H:%M:%SZ")==value
    except (TypeError,ValueError): return False


def validate(conn, config):
    """Recompute policy, money, quantities and event replay from persisted sources.

    Metrics are violation counts, not quality claims about unknown anomalies.
    Applicable zero-denominator checks are NOT VERIFIED, not 100 percent.
    """
    metrics=[]
    def metric(name, violations, denominator, interpretation, examples=()):
        metrics.append({"check_id":name,"numerator":violations,"denominator":denominator,
            "interpretation":interpretation,"status":"FAIL" if violations else ("PASS" if denominator else "NOT VERIFIED"),
            "examples":list(examples)[:10]})
    def sqlcheck(name, sql, denominator, interpretation):
        rows=conn.execute(sql).fetchall()
        metric(name,len(rows),denominator,interpretation,[list(r) for r in rows[:10]])

    data={t:{r["id"]:dict(r) for r in conn.execute(f'SELECT * FROM {quote(t)} ORDER BY id')} for t in TABLES if t!="EventLog"}
    counts={t:len(data[t]) if t in data else conn.execute("SELECT count(*) FROM EventLog").fetchone()[0] for t in TABLES}
    counts["IdSequence"]=conn.execute("SELECT count(*) FROM IdSequence").fetchone()[0]
    counts["SchemaVersion"]=conn.execute("SELECT count(*) FROM SchemaVersion").fetchone()[0]
    integrity=[r[0] for r in conn.execute("PRAGMA integrity_check")]
    metric("SQLITE_INTEGRITY",int(integrity!=["ok"]),1,"Failed SQLite integrity check / one database integrity check",integrity if integrity!=["ok"] else ())
    expected={"Order":config["counts"]["orders"],"ReturnRequest":config["counts"]["requests"],"ReturnLine":config["counts"]["return_lines"]}
    metric("EXACT_CORE_COUNTS",sum(counts[k]!=v for k,v in expected.items()),3,"Mismatched named entity counts / 3 required entity counts")
    fk=conn.execute("PRAGMA foreign_key_check").fetchall()
    fk_denominator=0
    structural_bad=0; cells=0; bad_ids=[]; date_bad=[]; dates=0
    for table,fields in TABLES.items():
        # EventLog is streamed rather than retained as hundreds of thousands of wide rows.
        records=conn.execute(f'SELECT * FROM {quote(table)} ORDER BY id') if table=="EventLog" else data[table].values()
        for raw in records:
            row=dict(raw)
            identifier=row["id"]
            if table=="ReturnLine":
                good=identifier==f"RMAL-{row['request_id']}-{row['line_sequence']:02d}" and 1<=row["line_sequence"]<=99
            else: good=bool(re.fullmatch(PREFIXES[table]+r"-2026-[0-9]{6}",identifier)) and not identifier.endswith("000000")
            if not good: bad_ids.append(identifier)
            for field in fields:
                value=row[field.name]; cells+=1
                bad=(value is None and field.required)
                if value is not None:
                    bad|=type(value) is not (int if field.sql_type=="INTEGER" else str)
                    if field.values: bad|=value not in field.values
                    if field.sql_type=="TEXT": bad|=not value.strip()
                    if field.ref: fk_denominator+=1
                    if field.unit=="UTC second":
                        dates+=1
                        if not valid_time(value) or value>config["as_of"]: date_bad.append([table,identifier,field.name])
                structural_bad+=bool(bad)
    metric("FK_INTEGRITY",len(fk),fk_denominator,"Unresolved non-null references / evaluated non-null references",[list(r) for r in fk[:10]])
    if fk:
        # Relationship-dependent replay must not dereference missing parents.
        # Return measured structural evidence without misrepresenting skipped
        # business checks as passed; the CLI reports this as a validation failure.
        return {"scope":"structural validation stopped before relationship-dependent baseline checks",
            "status":"FAIL","row_counts":counts,"metrics":metrics,"coverage":{},
            "quantity_summary":[],"order_totals":[],
            "incomplete_checks_reason":"Foreign-key violations prevent safe policy, financial, lifecycle and quantity replay."}
    metric("REQUIRED_TYPES_ENUMS",structural_bad,cells,"Invalid field cells / evaluated field cells")
    metric("IDENTIFIER_FORMATS",len(bad_ids),sum(counts[t] for t in TABLES),"Malformed identifiers / business-support rows",bad_ids)
    metric("CALENDAR_AND_AS_OF",len(date_bad),dates,"Invalid calendar or future timestamps / non-null business timestamps",date_bad)
    duplicates=0
    for table in TABLES:
        duplicates+=conn.execute(f'SELECT count(*)-count(DISTINCT id) FROM {quote(table)}').fetchone()[0]
    metric("PK_UNIQUENESS",duplicates,sum(counts[t] for t in TABLES),"Repeated identifiers / business-support rows")
    sqlcheck("SAME_ORDER",'''SELECT l.id FROM ReturnLine l JOIN ReturnRequest r ON r.id=l.request_id
        JOIN OrderLine o ON o.id=l.order_line_id WHERE r.order_id<>o.order_id''',counts["ReturnLine"],"Cross-order return lines / return lines")
    sqlcheck("AUTHORIZATION_MEMBERSHIP",'''SELECT a.id FROM AuthorizationLine a JOIN ReturnAuthorization h ON h.id=a.authorization_id
        JOIN ReturnLine l ON l.id=a.return_line_id WHERE h.request_id<>l.request_id OR a.approved_quantity>l.requested_quantity''',counts["AuthorizationLine"],"Invalid request/line allocations / authorization lines")
    sqlcheck("SHIPPED_ALLOCATION_LIMIT",'''SELECT a.id FROM AuthorizationLine a JOIN ShipmentLine s ON s.authorization_line_id=a.id
        GROUP BY a.id HAVING SUM(s.shipped_quantity)>a.approved_quantity''',counts["AuthorizationLine"],"Over-shipped allocations / authorization lines")
    sqlcheck("INSPECTED_RECEIPT_LIMIT",'''SELECT s.id FROM ShipmentLine s JOIN Inspection i ON i.shipment_line_id=s.id
        GROUP BY s.id HAVING SUM(i.inspected_quantity)>s.received_quantity''',counts["ShipmentLine"],"Over-inspected receipts / shipment lines")

    orders=data["Order"]; original=data["OrderLine"]; requests=data["ReturnRequest"]; lines=data["ReturnLine"]
    by_order=defaultdict(list); by_request=defaultdict(list); by_line_auth=defaultdict(list)
    for line in original.values(): by_order[line["order_id"]].append(line)
    for line in lines.values(): by_request[line["request_id"]].append(line)
    for a in data["AuthorizationLine"].values(): by_line_auth[a["return_line_id"]].append(a)
    allocation_ships=defaultdict(list); shipment_inspections=defaultdict(list); line_obligations=defaultdict(list); payouts=Counter()
    for s in data["ShipmentLine"].values(): allocation_ships[s["authorization_line_id"]].append(s)
    for i in data["Inspection"].values(): shipment_inspections[i["shipment_line_id"]].append(i)
    for o in data["RefundObligation"].values(): line_obligations[o["return_line_id"]].append(o)
    for r in data["Refund"].values(): payouts[r["obligation_id"]]+=r["paid_minor"]
    active={}
    for a in data["AuthorizationLine"].values():
        header=data["ReturnAuthorization"][a["authorization_id"]]
        active[a["id"]]=header["state"] in ("ISSUED","CONSUMED") or bool(allocation_ships[a["id"]])

    policy_errors=[]; remaining_used=Counter(); quantity_summary=[]; offsets={}
    policy_rows=data["ReturnPolicy"]
    for request in sorted(requests.values(),key=lambda r:(r["requested_at"],r["id"])):
        order=orders[request["order_id"]]
        policy=policy_rows[request["policy_id"]]
        for line in sorted(by_request[request["id"]],key=lambda r:r["line_sequence"]):
            purchase=original[line["order_line_id"]]
            category=data["Product"][purchase["product_id"]]["category"]
            cat=config["categories"][category]
            delivered=parse_time(order["delivered_at"]) if order["delivered_at"] else None
            date=parse_time(request["requested_at"])
            eligible=0
            allowed=(delivered is not None and date>=delivered and request["override_reason"] is None and cat["returnable"]
                and category not in json.loads(policy["excluded_categories_json"])
                and policy["effective_from"]<=request["requested_at"] and (policy["effective_to"] is None or request["requested_at"]<policy["effective_to"]))
            if allowed and date.astimezone(BUSINESS_TZ).date()<=delivered.astimezone(BUSINESS_TZ).date()+timedelta(days=cat["window_days"]) and line["requested_quantity"]<=purchase["quantity"]:
                eligible=min(line["requested_quantity"],max(0,purchase["quantity"]-remaining_used[purchase["id"]]))
            allocations=sorted((a for a in by_line_auth[line["id"]] if active[a["id"]]),key=lambda a:a["id"])
            authorized=sum(a["approved_quantity"] for a in allocations)
            if request["state"] in ("REQUESTED","CANCELLED"):
                if authorized or line["state"] not in ("REQUESTED","CANCELLED","REJECTED"): policy_errors.append(line["id"])
                evaluated=None
            else:
                if authorized!=eligible or (not authorized and line["state"]!="REJECTED"): policy_errors.append(line["id"])
                evaluated=eligible
            for allocation in allocations:
                offsets[allocation["id"]]=remaining_used[purchase["id"]]
                remaining_used[purchase["id"]]+=allocation["approved_quantity"]
            shipments=[s for a in allocations for s in allocation_ships[a["id"]]]
            inspections=[i for s in shipments for i in shipment_inspections[s["id"]]]
            refunded=sum(data["Inspection"][o["inspection_id"]]["inspected_quantity"] for o in line_obligations[line["id"]]
                if o["inspection_id"] and o["entitlement_minor"]>0 and payouts[o["id"]]==o["entitlement_minor"])
            quantity_summary.append({"return_line_id":line["id"],"purchased_quantity":purchase["quantity"],"requested_quantity":line["requested_quantity"],
                "eligible_quantity":evaluated,"authorized_quantity":authorized,"received_quantity":sum(s["received_quantity"] for s in shipments),
                "inspected_quantity":sum(i["inspected_quantity"] for i in inspections),"successfully_refunded_quantity":refunded})
    metric("ELIGIBILITY_REPLAY",len(policy_errors),counts["ReturnLine"],"Incorrect policy/quantity outcomes / return lines",policy_errors)
    over=[key for key,total in remaining_used.items() if total>original[key]["quantity"]]
    metric("CUMULATIVE_RESERVATIONS",len(over),counts["OrderLine"],"Over-reserved original lines / purchased order lines",over)
    invalid_ladder=[q["return_line_id"] for q in quantity_summary if not 0<=q["successfully_refunded_quantity"]<=q["inspected_quantity"]<=q["received_quantity"]<=q["authorized_quantity"]<=q["requested_quantity"]<=q["purchased_quantity"]]
    metric("QUANTITY_RECONCILIATION",len(invalid_ladder),counts["ReturnLine"],"Broken purchased/requested/authorized/received/inspected/refunded quantity ladders / return lines",invalid_ladder)

    money_bad=[]; order_bad=[]; totals=[]
    for order in orders.values():
        purchased=sorted(by_order[order["id"]],key=lambda r:r["id"])
        if not purchased: order_bad.append(order["id"]); continue
        net=[l["quantity"]*l["unit_price_minor"]-l["line_discount_minor"] for l in purchased]
        allocated=sum(l["order_discount_allocated_minor"] for l in purchased)
        expected_alloc=allocate_proportional(allocated,net)
        if allocated not in {basis_points(sum(net),rate) for rate in config["order_discount_bps"]} or expected_alloc!=[l["order_discount_allocated_minor"] for l in purchased]: order_bad.append(order["id"])
        for line,amount in zip(purchased,net):
            taxable=amount-line["order_discount_allocated_minor"]
            expected_tax=basis_points(taxable,config["tax_bps"])
            if line["tax_minor"]!=expected_tax or line["paid_minor"]!=taxable+expected_tax or line["line_discount_minor"] not in {basis_points(line["quantity"]*line["unit_price_minor"],r) for r in config["line_discount_bps"]}: money_bad.append(line["id"])
        totals.append({"order_id":order["id"],"goods_paid_minor":sum(l["paid_minor"] for l in purchased),"tax_minor":sum(l["tax_minor"] for l in purchased),
            "shipping_paid_minor":order["shipping_paid_minor"],"total_paid_minor":sum(l["paid_minor"] for l in purchased)+order["shipping_paid_minor"]})
    metric("LINE_FINANCIALS",len(money_bad),counts["OrderLine"],"Incorrect line discounts/tax/paid values / purchased lines",money_bad)
    metric("ORDER_DISCOUNT_ALLOCATION",len(order_bad),counts["Order"],"Incorrect order discount allocations or missing lines / orders",order_bad)
    entitlements={}; inspection_units={}; allocation_batches=defaultdict(list)
    for inspection in data["Inspection"].values():
        ship=data["ShipmentLine"][inspection["shipment_line_id"]]
        allocation_batches[ship["authorization_line_id"]].append(inspection)
    for allocation_id,batches in allocation_batches.items():
        allocation=data["AuthorizationLine"][allocation_id]; line=lines[allocation["return_line_id"]]; purchase=original[line["order_line_id"]]
        qty=purchase["quantity"]
        discount=purchase["line_discount_minor"]+purchase["order_discount_allocated_minor"]
        d,dr=divmod(discount,qty); t,tr=divmod(purchase["tax_minor"],qty)
        units=[purchase["unit_price_minor"]-d-(i<dr)+t+(i<tr) for i in range(qty)]
        start=offsets.get(allocation_id,0)
        for inspection in sorted(batches,key=lambda r:(r["inspected_at"],r["id"])):
            gross=sum(units[start:start+inspection["inspected_quantity"]]); start+=inspection["inspected_quantity"]
            fee=basis_points(gross,config["fee_bps"])
            entitlements[inspection["id"]]=(gross-fee,fee)
            inspection_units[inspection["id"]]=gross
    entitlement_bad=[]; balance_bad=[]
    for obligation in data["RefundObligation"].values():
        if obligation["inspection_id"] and (obligation["entitlement_minor"],obligation["fee_minor"])!=entitlements.get(obligation["inspection_id"]): entitlement_bad.append(obligation["id"])
        if payouts[obligation["id"]]>obligation["entitlement_minor"]: balance_bad.append(obligation["id"])
    metric("REFUND_ENTITLEMENTS",len(entitlement_bad),counts["RefundObligation"],"Incorrect inspection-unit entitlements/fees / obligations",entitlement_bad)
    metric("REFUND_BALANCES",len(balance_bad),counts["RefundObligation"],"Overpaid obligations / obligations",balance_bad)
    paid_by_original=Counter(); payment_keys=Counter(); refund_bad=[]
    for refund in data["Refund"].values():
        obligation=data["RefundObligation"][refund["obligation_id"]]
        line=lines[obligation["return_line_id"]]
        paid_by_original[line["order_line_id"]]+=refund["paid_minor"]
        if refund["state"]=="SUCCEEDED":
            payment_keys[refund["payment_key"]]+=1
            ins=data["Inspection"].get(obligation["inspection_id"])
            if not ins or ins["state"]!="FINALIZED" or refund["attempted_at"]<ins["inspected_at"] or refund["paid_minor"]!=refund["requested_minor"] or refund["paid_minor"]<=0: refund_bad.append(refund["id"])
        elif refund["paid_minor"]!=0: refund_bad.append(refund["id"])
    metric("REFUND_POSTING_PREREQUISITES",len(refund_bad),counts["Refund"],"Invalid successful/failed payout facts / refund attempts",refund_bad)
    metric("DUPLICATE_SUCCESSFUL_PAYMENTS",sum(n-1 for n in payment_keys.values() if n>1),sum(payment_keys.values()),"Repeated successful logical payment keys / successful payouts")
    metric("ORIGINAL_PAID_CEILING",sum(total>original[key]["paid_minor"] for key,total in paid_by_original.items()),counts["OrderLine"],"Original lines refunded above paid / purchased lines")

    route={"SELLABLE":"RESTOCK","REPAIRABLE":"REFURBISH","UNSAFE":"QUARANTINE","IRREPARABLE":"SCRAP"}
    disposition_bad=set(); used=Counter(); dispositions_by_line=defaultdict(list); dispositions_by_inspection=defaultdict(list)
    for d in data["InventoryDisposition"].values():
        dispositions_by_line[d["return_line_id"]].append(d)
        ins=data["Inspection"].get(d["inspection_id"])
        if d["state"]=="ACCEPTED":
            used[d["inspection_id"]]+=d["quantity"]
            dispositions_by_inspection[d["inspection_id"]].append(d["id"])
            if not ins or ins["state"]!="FINALIZED" or route[ins["condition"]]!=d["action"] or d["decided_at"]<ins["inspected_at"]: disposition_bad.add(d["id"])
    for inspection_id,quantity in used.items():
        if quantity>data["Inspection"][inspection_id]["inspected_quantity"]:
            disposition_bad.update(dispositions_by_inspection[inspection_id])
    metric("DISPOSITION_PREREQUISITES",len(disposition_bad),counts["InventoryDisposition"],"Invalid route/evidence/quantity decisions / dispositions",sorted(disposition_bad))
    movement_bad=set(); movement_counts=Counter(); movement_ids_by_disposition=defaultdict(list)
    for movement in data["InventoryMovement"].values():
        d=data["InventoryDisposition"][movement["disposition_id"]]; movement_counts[d["id"]]+=1
        movement_ids_by_disposition[d["id"]].append(movement["id"])
        if d["state"]!="ACCEPTED" or movement["quantity"]!=d["quantity"] or movement["moved_at"]<d["decided_at"]: movement_bad.add(movement["id"])
    for disposition_id,n in movement_counts.items():
        if n>1: movement_bad.update(movement_ids_by_disposition[disposition_id])
    metric("PHYSICAL_MOVEMENTS",len(movement_bad),counts["InventoryMovement"],"Invalid or repeated physical movements / movements",sorted(movement_bad))

    chronological=[]
    for order in orders.values():
        customer=data["Customer"][order["customer_id"]]
        if customer["created_at"]>order["placed_at"] or (order["delivered_at"] and order["delivered_at"]<order["placed_at"]): chronological.append(order["id"])
    for a in data["ReturnAuthorization"].values():
        if a["issued_at"]<requests[a["request_id"]]["requested_at"]: chronological.append(a["id"])
    for s in data["ShipmentLine"].values():
        shipment=data["ReturnShipment"][s["shipment_id"]]; authorization=data["ReturnAuthorization"][data["AuthorizationLine"][s["authorization_line_id"]]["authorization_id"]]
        if shipment["created_at"]<authorization["issued_at"] or (s["received_quantity"] and (shipment["state"]!="DELIVERED" or not shipment["delivered_at"])): chronological.append(s["id"])
    for i in data["Inspection"].values():
        s=data["ShipmentLine"][i["shipment_line_id"]]; shipment=data["ReturnShipment"][s["shipment_id"]]
        if not shipment["delivered_at"] or i["inspected_at"]<shipment["delivered_at"]: chronological.append(i["id"])
    metric("CROSS_ENTITY_DATES",len(chronological),counts["Order"]+counts["ReturnAuthorization"]+counts["ShipmentLine"]+counts["Inspection"],"Broken parent/child chronology / applicable parent-child timestamp checks",chronological)
    pending_bad=set()
    for r in requests.values():
        if r["state"] in ("REQUESTED","REJECTED"):
            if any(by_line_auth[l["id"]] for l in by_request[r["id"]]): pending_bad.add(r["id"])
        elif r["state"]=="CANCELLED":
            if any(active[a["id"]] for l in by_request[r["id"]] for a in by_line_auth[l["id"]]): pending_bad.add(r["id"])
        if r["resolution"]=="EXCHANGE" and any(line_obligations[l["id"]] for l in by_request[r["id"]]): pending_bad.add(r["id"])
    metric("PENDING_REJECTED_EXCHANGE",len(pending_bad),counts["ReturnRequest"],"Unauthorized descendants or exchange cash obligations / requests",sorted(pending_bad))
    aggregate_bad=set(); settled_bad=[]
    for request in requests.values():
        child=by_request[request["id"]]
        accepted=[l for l in child if any(active[a["id"]] for a in by_line_auth[l["id"]])]
        required_states={"CLOSED":{"SETTLED"},"INSPECTED":{"INSPECTED","SETTLED"},
            "RECEIVED":{"RECEIVED","INSPECTED","SETTLED"},"IN_TRANSIT":{"APPROVED","PARTIALLY_APPROVED","SHIPPED","RECEIVED","INSPECTED","SETTLED"}}
        if request["state"] in required_states and (not accepted or any(l["state"] not in required_states[request["state"]] for l in accepted)):
            aggregate_bad.add(request["id"])
        if request["state"]=="CLOSED" and request["resolution"]!="REFUND": aggregate_bad.add(request["id"])
    summaries={q["return_line_id"]:q for q in quantity_summary}
    for line in lines.values():
        if line["state"]!="SETTLED": continue
        q=summaries[line["id"]]
        obligations=line_obligations[line["id"]]
        decisions=dispositions_by_line[line["id"]]
        obligation_quantity=sum(data["Inspection"][o["inspection_id"]]["inspected_quantity"] for o in obligations if o["inspection_id"])
        if q["authorized_quantity"]<=0 or requests[line["request_id"]]["resolution"]!="REFUND" or obligation_quantity!=q["inspected_quantity"] or not (q["authorized_quantity"]==q["received_quantity"]==q["inspected_quantity"]) or any(payouts[o["id"]]!=o["entitlement_minor"] for o in obligations) or sum(d["quantity"] for d in decisions if movement_counts[d["id"]])!=q["inspected_quantity"]:
            settled_bad.append(line["id"])
    metric("AGGREGATE_REQUEST_PROGRESS",len(aggregate_bad),counts["ReturnRequest"],"Request stages inconsistent with accepted child progress / requests",sorted(aggregate_bad))
    metric("SETTLEMENT_PREREQUISITES",len(settled_bad),sum(l["state"]=="SETTLED" for l in lines.values()),"Settled lines with incomplete receipt/inspection/payment/movement / settled lines",settled_bad)

    replay={}; previous_time={}; creations=Counter(); event_bad=[]
    for e in conn.execute("SELECT id,entity_type,entity_id,event_type,previous_state,new_state,occurred_at FROM EventHistory ORDER BY id"):
        key=(e["entity_type"],e["entity_id"])
        bad=e["occurred_at"]<previous_time.get(key,"")
        if e["event_type"]=="CREATED":
            creations[key]+=1
            bad|=creations[key]!=1 or e["previous_state"] is not None
            replay[key]=e["new_state"]
        elif e["event_type"]=="STATE_CHANGED":
            bad|=key not in replay or replay.get(key)!=e["previous_state"] or e["new_state"] not in TRANSITIONS.get(e["entity_type"],{}).get(e["previous_state"],())
            replay[key]=e["new_state"]
        else: bad|=key not in replay or e["previous_state"] is not None or e["new_state"] is not None
        previous_time[key]=e["occurred_at"]
        if bad: event_bad.append(e["id"])
    projection_bad=[]
    for table in TARGETS:
        for row in data[table].values():
            key=(table,row["id"])
            if creations[key]!=1 or ("state" in row and replay.get(key)!=row["state"]): projection_bad.append([table,row["id"]])
    metric("EVENT_REPLAY",len(event_bad),counts["EventLog"],"Invalid/reordered event transitions / events",event_bad)
    metric("EVENT_PROJECTIONS",len(projection_bad),sum(counts[t] for t in TARGETS),"Missing creation history or mismatched final projection / traceable records",projection_bad)
    coverage={"request_states":dict(sorted(Counter(r["state"] for r in requests.values()).items())),
        "inspection_conditions":dict(sorted(Counter(i["condition"] for i in data["Inspection"].values()).items())),
        "exchange_requests":sum(r["resolution"]=="EXCHANGE" for r in requests.values()),
        "partial_requested_lines":sum(q["requested_quantity"]<q["purchased_quantity"] for q in quantity_summary),
        "partially_authorized_lines":sum(0<q["authorized_quantity"]<q["requested_quantity"] for q in quantity_summary),
        "missing_shipments":sum(s["state"]=="MISSING" for s in data["ReturnShipment"].values()),
        "failed_payment_attempts":sum(r["state"]=="FAILED" for r in data["Refund"].values())}
    return {"scope":"valid baseline only; deliberate anomalies and detection recall not evaluated","status":"FAIL" if any(m["status"]=="FAIL" for m in metrics) else "PASS",
        "row_counts":counts,"metrics":metrics,"coverage":coverage,
        "quantity_summary":sorted(quantity_summary,key=lambda q:q["return_line_id"]),"order_totals":totals}
