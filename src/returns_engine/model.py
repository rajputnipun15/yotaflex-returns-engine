"""Declarative field metadata: one source for SQLite DDL and the dictionary."""

from dataclasses import dataclass
from .ids import PREFIXES


@dataclass(frozen=True)
class Field:
    name: str
    sql_type: str
    meaning: str
    required: bool = True
    ref: str | None = None
    values: tuple[str, ...] = ()
    check: str | None = None
    unit: str = "none"
    default: str | None = None


def text(name, meaning, *, required=True, ref=None, values=(), check=None, default=None):
    return Field(name, "TEXT", meaning, required, ref, tuple(values), check, default=default)


def integer(name, meaning, *, minimum=0, required=True, unit="units"):
    return Field(name, "INTEGER", meaning, required, check=f'"{name}" >= {minimum}', unit=unit)


def money(name, meaning):
    return integer(name, meaning, unit="currency minor units")


def timestamp(name, meaning, *, required=True):
    # strftime alone accepts some impossible dates; application validates calendar dates.
    rule = (f'length("{name}")=20 AND "{name}" GLOB '
            "'[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'")
    return Field(name, "TEXT", meaning, required, check=rule, unit="UTC second")


def fk(name, parent, meaning, required=True):
    return text(name, meaning, ref=parent, required=required)


def state(*values):
    return text("state", "Current lifecycle projection; changes recorded in EventLog.", values=values)


def fields(entity, *columns):
    prefix = PREFIXES[entity]
    pattern = prefix + "-2026-" + "[0-9]" * 6
    return (text("id", f"Immutable {entity} identifier.",
                 check=f"id GLOB '{pattern}' AND substr(id,-6)<>'000000'"), *columns)


TABLES = {
    "Customer": fields("Customer", text("synthetic_name", "Invented display name; never real personal data."),
        state("ACTIVE", "INACTIVE"), timestamp("created_at", "Creation effective time.")),
    "Product": fields("Product", text("category", "Synthetic category used by return policy."),
        text("description", "Synthetic product description.")),
    "ReturnPolicy": fields("ReturnPolicy", integer("window_days", "Inclusive delivery-based return window.", unit="calendar days"),
        text("excluded_categories_json", "JSON array of excluded category strings.", check="json_valid(excluded_categories_json) AND json_type(excluded_categories_json)='array'"),
        integer("fee_bps", "Configurable fee rate, not an official policy.", unit="basis points"),
        timestamp("effective_from", "Inclusive policy validity start."), timestamp("effective_to", "Exclusive policy validity end.", required=False)),
    "Order": fields("Order", fk("customer_id", "Customer", "Purchasing customer."),
        text("currency", "ISO-style synthetic currency code.", check="length(currency)=3 AND currency NOT GLOB '*[^A-Z]*'"),
        timestamp("placed_at", "Original purchase time."), timestamp("delivered_at", "Delivery time; null while pending.", required=False),
        money("shipping_paid_minor", "Original paid shipping; refundable only under explicit policy."), state("PLACED", "FULFILLED", "DELIVERED")),
    "OrderLine": fields("OrderLine", fk("order_id", "Order", "Owning purchase."), fk("product_id", "Product", "Purchased product."),
        integer("quantity", "Purchased unit count.", minimum=1), money("unit_price_minor", "Undiscounted unit price."),
        money("line_discount_minor", "Discount specific to this line."), money("order_discount_allocated_minor", "Allocated share of order discount."),
        money("tax_minor", "Original tax paid for this line."), money("paid_minor", "Net goods amount plus tax, excluding shipping.")),
    "ReturnRequest": fields("ReturnRequest", fk("order_id", "Order", "Exactly one original order."),
        fk("policy_id", "ReturnPolicy", "Policy version used for request decision."), timestamp("requested_at", "Request submission time."),
        text("resolution", "Customer-requested resolution.", values=("REFUND", "EXCHANGE")),
        text("override_reason", "Authorized policy override evidence; null means no override.", required=False),
        state("REQUESTED", "APPROVED", "PARTIALLY_APPROVED", "REJECTED", "IN_TRANSIT", "RECEIVED", "INSPECTED", "CLOSED", "CANCELLED")),
    "ReturnLine": (text("id", "Immutable RMAL identifier embedding the complete parent RMA."),
        fk("request_id", "ReturnRequest", "Owning return request."), fk("order_line_id", "OrderLine", "Original purchased line, constrained to request order."),
        integer("line_sequence", "Two-digit request-local sequence, 1..99." , minimum=1),
        integer("requested_quantity", "Requested units; may exceed purchase for auditable invalid requests.", minimum=1),
        text("reason_code", "Customer reason, e.g. DAMAGE or SIZE."),
        state("REQUESTED", "APPROVED", "PARTIALLY_APPROVED", "REJECTED", "SHIPPED", "RECEIVED", "INSPECTED", "SETTLED", "CANCELLED")),
    "ReturnAuthorization": fields("ReturnAuthorization", fk("request_id", "ReturnRequest", "Request being authorized."),
        timestamp("issued_at", "Authorization effective time."), state("ISSUED", "SUPERSEDED", "CANCELLED", "CONSUMED")),
    "AuthorizationLine": fields("AuthorizationLine", fk("authorization_id", "ReturnAuthorization", "Approval version header."),
        fk("return_line_id", "ReturnLine", "Approved requested line."), integer("approved_quantity", "Reserved/approved units.", minimum=1)),
    "ReturnShipment": fields("ReturnShipment", timestamp("created_at", "Shipment creation time."),
        timestamp("dispatched_at", "Dispatch time; null while pending.", required=False),
        timestamp("delivered_at", "Physical receipt time; null if pending/missing.", required=False),
        state("CREATED", "DISPATCHED", "DELIVERED", "MISSING")),
    "ShipmentLine": fields("ShipmentLine", fk("shipment_id", "ReturnShipment", "Containing shipment."),
        fk("authorization_line_id", "AuthorizationLine", "Approved quantity being transported."),
        integer("shipped_quantity", "Allocated shipped units.", minimum=1), integer("received_quantity", "Actually received units; zero while pending.")),
    "Inspection": fields("Inspection", fk("shipment_line_id", "ShipmentLine", "Specific received allocation/batch."),
        integer("inspected_quantity", "Units inspected in this batch.", minimum=1),
        text("condition", "Physical result for this batch.", values=("SELLABLE", "REPAIRABLE", "UNSAFE", "IRREPARABLE")),
        timestamp("inspected_at", "Inspection effective time."), state("RECORDED", "FINALIZED")),
    "RefundObligation": fields("RefundObligation", fk("return_line_id", "ReturnLine", "Return line entitled to this settlement."),
        fk("inspection_id", "Inspection", "Inspection evidence for entitlement; absent for pending/blocked cases.", required=False),
        money("entitlement_minor", "Permitted refund ceiling derived later from original unit allocations."),
        money("fee_minor", "Disclosed fee already deducted in entitlement.")),
    "Refund": fields("Refund", fk("obligation_id", "RefundObligation", "Stable obligation shared across retries."),
        text("payment_key", "Logical idempotency key; retries reuse it."), money("requested_minor", "Attempted amount, including blocked excessive requests."),
        money("paid_minor", "Actual successful payout; zero on pending/failed/rejected attempts."),
        timestamp("attempted_at", "Attempt effective time."), text("reason_code", "Decision/error reason; null while pending.", required=False),
        state("REQUESTED", "REJECTED", "FAILED", "SUCCEEDED")),
    "InventoryDisposition": fields("InventoryDisposition", fk("return_line_id", "ReturnLine", "Goods subject to decision, also allows pre-inspection blocked attempts."),
        fk("inspection_id", "Inspection", "Inspection evidence; optional until decision accepted.", required=False),
        text("action", "Proposed route; not proof of stock movement.", values=("RESTOCK", "REFURBISH", "QUARANTINE", "SCRAP")),
        integer("quantity", "Units proposed for routing.", minimum=1), timestamp("decided_at", "Decision time."),
        text("reason_code", "Decision explanation.", required=False), state("PROPOSED", "REJECTED", "ACCEPTED")),
    "InventoryMovement": fields("InventoryMovement", fk("disposition_id", "InventoryDisposition", "Accepted decision physically executed once."),
        integer("quantity", "Units actually moved.", minimum=1), timestamp("moved_at", "Physical movement time.")),
}

# Real nullable typed FKs avoid unchecked polymorphic event/attempt references.
TARGETS = tuple(TABLES)
TARGET_FIELDS = tuple(fk(name + "_id", name, f"Referenced {name}; exactly one typed target is set.", required=False) for name in TARGETS)
TABLES["ActionAttempt"] = fields("ActionAttempt", *TARGET_FIELDS,
    text("action", "Attempted business operation, without oracle labels."), text("payload_json", "Ordinary action input.", check="json_valid(payload_json)"),
    text("decision", "Evaluated decision.", values=("PENDING", "ALLOWED", "BLOCKED", "FAILED")),
    text("reason_code", "Decision reason.", required=False), timestamp("attempted_at", "Attempt effective time."),
    text("correlation_id", "Groups one atomic business operation; not an entity FK."))
TABLES["EventLog"] = fields("EventLog", *TARGET_FIELDS,
    fk("attempt_id", "ActionAttempt", "Related audited action, if any.", required=False),
    text("event_type", "Creation, state transition or observation.", values=("CREATED", "STATE_CHANGED", "OBSERVED")),
    text("previous_state", "Prior lifecycle state; null for creation/observation.", required=False),
    text("new_state", "Resulting state; null for stateless observation.", required=False),
    timestamp("occurred_at", "Effective event time, not volatile runtime clock."), text("reason_code", "Explicit explanation."),
    text("correlation_id", "Groups events in one atomic transaction."))

CONSTRAINTS = {
    "ReturnPolicy": ["CHECK(fee_bps<=10000)", "CHECK(effective_to IS NULL OR effective_to>effective_from)"],
    "Order": ["CHECK(delivered_at IS NULL OR delivered_at>=placed_at)", "CHECK(state<>'DELIVERED' OR delivered_at IS NOT NULL)"],
    "OrderLine": ["CHECK(line_discount_minor+order_discount_allocated_minor<=quantity*unit_price_minor)",
        "CHECK(paid_minor=quantity*unit_price_minor-line_discount_minor-order_discount_allocated_minor+tax_minor)",
        "CHECK(typeof(quantity*unit_price_minor)='integer')"],
    "ReturnLine": ["UNIQUE(request_id,line_sequence)", "CHECK(line_sequence<=99)",
        "CHECK(id='RMAL-'||request_id||'-'||printf('%02d',line_sequence))"],
    "AuthorizationLine": ["UNIQUE(authorization_id,return_line_id)"],
    "ShipmentLine": ["UNIQUE(shipment_id,authorization_line_id)", "CHECK(received_quantity<=shipped_quantity)"],
    "ReturnShipment": ["CHECK(dispatched_at IS NULL OR dispatched_at>=created_at)",
        "CHECK(delivered_at IS NULL OR (dispatched_at IS NOT NULL AND delivered_at>=dispatched_at))",
        "CHECK(state NOT IN ('DISPATCHED','MISSING','DELIVERED') OR dispatched_at IS NOT NULL)",
        "CHECK(state<>'DELIVERED' OR delivered_at IS NOT NULL)", "CHECK(state<>'MISSING' OR delivered_at IS NULL)"],
    "RefundObligation": ["UNIQUE(inspection_id)"],
    "Refund": ["CHECK((state='SUCCEEDED' AND paid_minor=requested_minor AND paid_minor>0) OR (state<>'SUCCEEDED' AND paid_minor=0))",
        "CHECK(state='REQUESTED' OR reason_code IS NOT NULL)"],
    "InventoryDisposition": ["CHECK(state<>'ACCEPTED' OR inspection_id IS NOT NULL)"],
    "InventoryMovement": ["UNIQUE(disposition_id)"],
}
for _table in ("ActionAttempt", "EventLog"):
    CONSTRAINTS[_table] = ["CHECK(" + "+".join(f'("{t}_id" IS NOT NULL)' for t in TARGETS) + "=1)"]

TRANSITIONS = {
    "Customer": {"ACTIVE": ("INACTIVE",), "INACTIVE": ("ACTIVE",)},
    "Order": {"PLACED": ("FULFILLED",), "FULFILLED": ("DELIVERED",)},
    "ReturnRequest": {"REQUESTED": ("APPROVED", "PARTIALLY_APPROVED", "REJECTED", "CANCELLED"),
        "APPROVED": ("IN_TRANSIT", "CANCELLED"), "PARTIALLY_APPROVED": ("IN_TRANSIT", "CANCELLED"),
        "IN_TRANSIT": ("RECEIVED",), "RECEIVED": ("INSPECTED",), "INSPECTED": ("CLOSED",)},
    "ReturnLine": {"REQUESTED": ("APPROVED", "PARTIALLY_APPROVED", "REJECTED", "CANCELLED"),
        "APPROVED": ("SHIPPED", "CANCELLED"), "PARTIALLY_APPROVED": ("SHIPPED", "CANCELLED"),
        "SHIPPED": ("RECEIVED",), "RECEIVED": ("INSPECTED",), "INSPECTED": ("SETTLED",)},
    "ReturnAuthorization": {"ISSUED": ("SUPERSEDED", "CANCELLED", "CONSUMED")},
    "ReturnShipment": {"CREATED": ("DISPATCHED",), "DISPATCHED": ("DELIVERED", "MISSING")},
    "Inspection": {"RECORDED": ("FINALIZED",)},
    "Refund": {"REQUESTED": ("REJECTED", "FAILED", "SUCCEEDED")},
    "InventoryDisposition": {"PROPOSED": ("REJECTED", "ACCEPTED")},
}
