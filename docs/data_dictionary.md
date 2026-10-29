# Data dictionary (implemented Phase 2 schema)

Generated from returns_engine.model; checked against PRAGMA table_info in tests. Phase 3 baseline generation uses the unchanged Phase 2 schema.

All tables are STRICT. All identifiers are NOT NULL primary keys, immutable, case-sensitive and unique per table. All FKs use RESTRICT on update/delete and are indexed. No field has an implicit business default; supply all required values explicitly. Optional means SQL NULL is allowed.

Money is integer minor currency units; currency is inherited from the original Order. UTC timestamps use YYYY-MM-DDTHH:MM:SSZ. SQL checks lexical form; the event utility also validates calendar dates. See schema.md for relationships/transitions and business_rules.md for rules and enforcement boundaries.

Sensitivity: all business data must be invented, public-safe synthetic data. Names, reason/override text and JSON payloads must never contain real personal information, secrets or confidential material. Technical correlation IDs and IDs are public-safe only when synthetic.

## Customer

### Customer.id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: PK. Uniqueness: Unique primary key.
- Default: none.
- Validation: id GLOB 'CUS-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'.
- Meaning: Immutable Customer identifier.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Customer.synthetic_name
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Invented display name; never real personal data.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Customer.state
- Type: TEXT; required (NOT NULL).
- Allowed values: ACTIVE, INACTIVE. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Current lifecycle projection; changes recorded in EventLog.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Customer.created_at
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: UTC second.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: length("created_at")=20 AND "created_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'.
- Meaning: Creation effective time.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

Table constraints (in addition to field/FK/trigger rules):

- Primary key and field constraints; see schema.md for triggers.

## Product

### Product.id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: PK. Uniqueness: Unique primary key.
- Default: none.
- Validation: id GLOB 'PRD-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'.
- Meaning: Immutable Product identifier.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Product.category
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Synthetic category used by return policy.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Product.description
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Synthetic product description.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

Table constraints (in addition to field/FK/trigger rules):

- Primary key and field constraints; see schema.md for triggers.

## ReturnPolicy

### ReturnPolicy.id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: PK. Uniqueness: Unique primary key.
- Default: none.
- Validation: id GLOB 'POL-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'.
- Meaning: Immutable ReturnPolicy identifier.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnPolicy.window_days
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: calendar days.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "window_days" >= 0.
- Meaning: Inclusive delivery-based return window.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnPolicy.excluded_categories_json
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: json_valid(excluded_categories_json) AND json_type(excluded_categories_json)='array'.
- Meaning: JSON array of excluded category strings.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnPolicy.fee_bps
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: basis points.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "fee_bps" >= 0.
- Meaning: Configurable fee rate, not an official policy.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnPolicy.effective_from
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: UTC second.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: length("effective_from")=20 AND "effective_from" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'.
- Meaning: Inclusive policy validity start.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnPolicy.effective_to
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: UTC second.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: length("effective_to")=20 AND "effective_to" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'.
- Meaning: Exclusive policy validity end.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

Table constraints (in addition to field/FK/trigger rules):

- CHECK(fee_bps<=10000)
- CHECK(effective_to IS NULL OR effective_to>effective_from)

## Order

### Order.id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: PK. Uniqueness: Unique primary key.
- Default: none.
- Validation: id GLOB 'ORD-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'.
- Meaning: Immutable Order identifier.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Order.customer_id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> Customer.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Purchasing customer.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Order.currency
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: length(currency)=3 AND currency NOT GLOB '*[^A-Z]*'.
- Meaning: ISO-style synthetic currency code.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Order.placed_at
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: UTC second.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: length("placed_at")=20 AND "placed_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'.
- Meaning: Original purchase time.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Order.delivered_at
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: UTC second.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: length("delivered_at")=20 AND "delivered_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'.
- Meaning: Delivery time; null while pending.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Order.shipping_paid_minor
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: currency minor units.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "shipping_paid_minor" >= 0.
- Meaning: Original paid shipping; refundable only under explicit policy.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Order.state
- Type: TEXT; required (NOT NULL).
- Allowed values: PLACED, FULFILLED, DELIVERED. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Current lifecycle projection; changes recorded in EventLog.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

Table constraints (in addition to field/FK/trigger rules):

- CHECK(delivered_at IS NULL OR delivered_at>=placed_at)
- CHECK(state<>'DELIVERED' OR delivered_at IS NOT NULL)

## OrderLine

### OrderLine.id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: PK. Uniqueness: Unique primary key.
- Default: none.
- Validation: id GLOB 'ORL-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'.
- Meaning: Immutable OrderLine identifier.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### OrderLine.order_id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> Order.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Owning purchase.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### OrderLine.product_id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> Product.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Purchased product.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### OrderLine.quantity
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: units.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "quantity" >= 1.
- Meaning: Purchased unit count.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### OrderLine.unit_price_minor
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: currency minor units.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "unit_price_minor" >= 0.
- Meaning: Undiscounted unit price.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### OrderLine.line_discount_minor
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: currency minor units.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "line_discount_minor" >= 0.
- Meaning: Discount specific to this line.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### OrderLine.order_discount_allocated_minor
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: currency minor units.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "order_discount_allocated_minor" >= 0.
- Meaning: Allocated share of order discount.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### OrderLine.tax_minor
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: currency minor units.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "tax_minor" >= 0.
- Meaning: Original tax paid for this line.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### OrderLine.paid_minor
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: currency minor units.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "paid_minor" >= 0.
- Meaning: Net goods amount plus tax, excluding shipping.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

Table constraints (in addition to field/FK/trigger rules):

- CHECK(line_discount_minor+order_discount_allocated_minor<=quantity*unit_price_minor)
- CHECK(paid_minor=quantity*unit_price_minor-line_discount_minor-order_discount_allocated_minor+tax_minor)
- CHECK(typeof(quantity*unit_price_minor)='integer')

## ReturnRequest

### ReturnRequest.id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: PK. Uniqueness: Unique primary key.
- Default: none.
- Validation: id GLOB 'RMA-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'.
- Meaning: Immutable ReturnRequest identifier.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnRequest.order_id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> Order.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Exactly one original order.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnRequest.policy_id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ReturnPolicy.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Policy version used for request decision.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnRequest.requested_at
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: UTC second.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: length("requested_at")=20 AND "requested_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'.
- Meaning: Request submission time.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnRequest.resolution
- Type: TEXT; required (NOT NULL).
- Allowed values: REFUND, EXCHANGE. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Customer-requested resolution.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnRequest.override_reason
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Authorized policy override evidence; null means no override.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnRequest.state
- Type: TEXT; required (NOT NULL).
- Allowed values: REQUESTED, APPROVED, PARTIALLY_APPROVED, REJECTED, IN_TRANSIT, RECEIVED, INSPECTED, CLOSED, CANCELLED. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Current lifecycle projection; changes recorded in EventLog.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

Table constraints (in addition to field/FK/trigger rules):

- Primary key and field constraints; see schema.md for triggers.

## ReturnLine

### ReturnLine.id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: PK. Uniqueness: Unique primary key.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Immutable RMAL identifier embedding the complete parent RMA.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnLine.request_id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ReturnRequest.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Owning return request.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnLine.order_line_id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> OrderLine.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Original purchased line, constrained to request order.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnLine.line_sequence
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: units.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "line_sequence" >= 1.
- Meaning: Two-digit request-local sequence, 1..99.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnLine.requested_quantity
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: units.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "requested_quantity" >= 1.
- Meaning: Requested units; may exceed purchase for auditable invalid requests.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnLine.reason_code
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Customer reason, e.g. DAMAGE or SIZE.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnLine.state
- Type: TEXT; required (NOT NULL).
- Allowed values: REQUESTED, APPROVED, PARTIALLY_APPROVED, REJECTED, SHIPPED, RECEIVED, INSPECTED, SETTLED, CANCELLED. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Current lifecycle projection; changes recorded in EventLog.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

Table constraints (in addition to field/FK/trigger rules):

- UNIQUE(request_id,line_sequence)
- CHECK(line_sequence<=99)
- CHECK(id='RMAL-'||request_id||'-'||printf('%02d',line_sequence))

## ReturnAuthorization

### ReturnAuthorization.id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: PK. Uniqueness: Unique primary key.
- Default: none.
- Validation: id GLOB 'RAU-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'.
- Meaning: Immutable ReturnAuthorization identifier.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnAuthorization.request_id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ReturnRequest.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Request being authorized.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnAuthorization.issued_at
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: UTC second.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: length("issued_at")=20 AND "issued_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'.
- Meaning: Authorization effective time.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnAuthorization.state
- Type: TEXT; required (NOT NULL).
- Allowed values: ISSUED, SUPERSEDED, CANCELLED, CONSUMED. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Current lifecycle projection; changes recorded in EventLog.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

Table constraints (in addition to field/FK/trigger rules):

- Primary key and field constraints; see schema.md for triggers.

## AuthorizationLine

### AuthorizationLine.id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: PK. Uniqueness: Unique primary key.
- Default: none.
- Validation: id GLOB 'RAL-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'.
- Meaning: Immutable AuthorizationLine identifier.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### AuthorizationLine.authorization_id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ReturnAuthorization.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Approval version header.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### AuthorizationLine.return_line_id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ReturnLine.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Approved requested line.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### AuthorizationLine.approved_quantity
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: units.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "approved_quantity" >= 1.
- Meaning: Reserved/approved units.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

Table constraints (in addition to field/FK/trigger rules):

- UNIQUE(authorization_id,return_line_id)

## ReturnShipment

### ReturnShipment.id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: PK. Uniqueness: Unique primary key.
- Default: none.
- Validation: id GLOB 'RTS-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'.
- Meaning: Immutable ReturnShipment identifier.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnShipment.created_at
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: UTC second.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: length("created_at")=20 AND "created_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'.
- Meaning: Shipment creation time.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnShipment.dispatched_at
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: UTC second.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: length("dispatched_at")=20 AND "dispatched_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'.
- Meaning: Dispatch time; null while pending.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnShipment.delivered_at
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: UTC second.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: length("delivered_at")=20 AND "delivered_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'.
- Meaning: Physical receipt time; null if pending/missing.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ReturnShipment.state
- Type: TEXT; required (NOT NULL).
- Allowed values: CREATED, DISPATCHED, DELIVERED, MISSING. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Current lifecycle projection; changes recorded in EventLog.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

Table constraints (in addition to field/FK/trigger rules):

- CHECK(dispatched_at IS NULL OR dispatched_at>=created_at)
- CHECK(delivered_at IS NULL OR (dispatched_at IS NOT NULL AND delivered_at>=dispatched_at))
- CHECK(state NOT IN ('DISPATCHED','MISSING','DELIVERED') OR dispatched_at IS NOT NULL)
- CHECK(state<>'DELIVERED' OR delivered_at IS NOT NULL)
- CHECK(state<>'MISSING' OR delivered_at IS NULL)

## ShipmentLine

### ShipmentLine.id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: PK. Uniqueness: Unique primary key.
- Default: none.
- Validation: id GLOB 'SHL-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'.
- Meaning: Immutable ShipmentLine identifier.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ShipmentLine.shipment_id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ReturnShipment.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Containing shipment.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ShipmentLine.authorization_line_id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> AuthorizationLine.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Approved quantity being transported.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ShipmentLine.shipped_quantity
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: units.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "shipped_quantity" >= 1.
- Meaning: Allocated shipped units.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ShipmentLine.received_quantity
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: units.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "received_quantity" >= 0.
- Meaning: Actually received units; zero while pending.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

Table constraints (in addition to field/FK/trigger rules):

- UNIQUE(shipment_id,authorization_line_id)
- CHECK(received_quantity<=shipped_quantity)

## Inspection

### Inspection.id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: PK. Uniqueness: Unique primary key.
- Default: none.
- Validation: id GLOB 'INS-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'.
- Meaning: Immutable Inspection identifier.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Inspection.shipment_line_id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ShipmentLine.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Specific received allocation/batch.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Inspection.inspected_quantity
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: units.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "inspected_quantity" >= 1.
- Meaning: Units inspected in this batch.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Inspection.condition
- Type: TEXT; required (NOT NULL).
- Allowed values: SELLABLE, REPAIRABLE, UNSAFE, IRREPARABLE. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Physical result for this batch.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Inspection.inspected_at
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: UTC second.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: length("inspected_at")=20 AND "inspected_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'.
- Meaning: Inspection effective time.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Inspection.state
- Type: TEXT; required (NOT NULL).
- Allowed values: RECORDED, FINALIZED. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Current lifecycle projection; changes recorded in EventLog.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

Table constraints (in addition to field/FK/trigger rules):

- Primary key and field constraints; see schema.md for triggers.

## RefundObligation

### RefundObligation.id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: PK. Uniqueness: Unique primary key.
- Default: none.
- Validation: id GLOB 'RFO-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'.
- Meaning: Immutable RefundObligation identifier.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### RefundObligation.return_line_id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ReturnLine.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Return line entitled to this settlement.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### RefundObligation.inspection_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> Inspection.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Inspection evidence for entitlement; absent for pending/blocked cases.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### RefundObligation.entitlement_minor
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: currency minor units.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "entitlement_minor" >= 0.
- Meaning: Permitted refund ceiling derived later from original unit allocations.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### RefundObligation.fee_minor
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: currency minor units.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "fee_minor" >= 0.
- Meaning: Disclosed fee already deducted in entitlement.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

Table constraints (in addition to field/FK/trigger rules):

- UNIQUE(inspection_id)

## Refund

### Refund.id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: PK. Uniqueness: Unique primary key.
- Default: none.
- Validation: id GLOB 'REF-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'.
- Meaning: Immutable Refund identifier.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Refund.obligation_id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> RefundObligation.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Stable obligation shared across retries.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Refund.payment_key
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Logical idempotency key; retries reuse it.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Refund.requested_minor
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: currency minor units.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "requested_minor" >= 0.
- Meaning: Attempted amount, including blocked excessive requests.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Refund.paid_minor
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: currency minor units.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "paid_minor" >= 0.
- Meaning: Actual successful payout; zero on pending/failed/rejected attempts.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Refund.attempted_at
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: UTC second.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: length("attempted_at")=20 AND "attempted_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'.
- Meaning: Attempt effective time.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Refund.reason_code
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Decision/error reason; null while pending.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### Refund.state
- Type: TEXT; required (NOT NULL).
- Allowed values: REQUESTED, REJECTED, FAILED, SUCCEEDED. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Current lifecycle projection; changes recorded in EventLog.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

Table constraints (in addition to field/FK/trigger rules):

- CHECK((state='SUCCEEDED' AND paid_minor=requested_minor AND paid_minor>0) OR (state<>'SUCCEEDED' AND paid_minor=0))
- CHECK(state='REQUESTED' OR reason_code IS NOT NULL)
- UNIQUE(payment_key) WHERE state='SUCCEEDED'; failed/blocked retries may repeat the key.

## InventoryDisposition

### InventoryDisposition.id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: PK. Uniqueness: Unique primary key.
- Default: none.
- Validation: id GLOB 'DSP-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'.
- Meaning: Immutable InventoryDisposition identifier.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### InventoryDisposition.return_line_id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ReturnLine.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Goods subject to decision, also allows pre-inspection blocked attempts.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### InventoryDisposition.inspection_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> Inspection.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Inspection evidence; optional until decision accepted.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### InventoryDisposition.action
- Type: TEXT; required (NOT NULL).
- Allowed values: RESTOCK, REFURBISH, QUARANTINE, SCRAP. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Proposed route; not proof of stock movement.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### InventoryDisposition.quantity
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: units.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "quantity" >= 1.
- Meaning: Units proposed for routing.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### InventoryDisposition.decided_at
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: UTC second.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: length("decided_at")=20 AND "decided_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'.
- Meaning: Decision time.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### InventoryDisposition.reason_code
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Decision explanation.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### InventoryDisposition.state
- Type: TEXT; required (NOT NULL).
- Allowed values: PROPOSED, REJECTED, ACCEPTED. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Current lifecycle projection; changes recorded in EventLog.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

Table constraints (in addition to field/FK/trigger rules):

- CHECK(state<>'ACCEPTED' OR inspection_id IS NOT NULL)

## InventoryMovement

### InventoryMovement.id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: PK. Uniqueness: Unique primary key.
- Default: none.
- Validation: id GLOB 'MOV-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'.
- Meaning: Immutable InventoryMovement identifier.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### InventoryMovement.disposition_id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> InventoryDisposition.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Accepted decision physically executed once.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### InventoryMovement.quantity
- Type: INTEGER; required (NOT NULL).
- Allowed values: Integer. Unit: units.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: "quantity" >= 1.
- Meaning: Units actually moved.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### InventoryMovement.moved_at
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: UTC second.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: length("moved_at")=20 AND "moved_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'.
- Meaning: Physical movement time.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

Table constraints (in addition to field/FK/trigger rules):

- UNIQUE(disposition_id)

## ActionAttempt

### ActionAttempt.id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: PK. Uniqueness: Unique primary key.
- Default: none.
- Validation: id GLOB 'ATT-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'.
- Meaning: Immutable ActionAttempt identifier.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.Customer_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> Customer.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced Customer; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.Product_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> Product.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced Product; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.ReturnPolicy_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ReturnPolicy.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced ReturnPolicy; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.Order_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> Order.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced Order; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.OrderLine_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> OrderLine.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced OrderLine; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.ReturnRequest_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ReturnRequest.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced ReturnRequest; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.ReturnLine_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ReturnLine.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced ReturnLine; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.ReturnAuthorization_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ReturnAuthorization.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced ReturnAuthorization; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.AuthorizationLine_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> AuthorizationLine.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced AuthorizationLine; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.ReturnShipment_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ReturnShipment.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced ReturnShipment; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.ShipmentLine_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ShipmentLine.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced ShipmentLine; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.Inspection_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> Inspection.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced Inspection; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.RefundObligation_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> RefundObligation.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced RefundObligation; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.Refund_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> Refund.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced Refund; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.InventoryDisposition_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> InventoryDisposition.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced InventoryDisposition; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.InventoryMovement_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> InventoryMovement.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced InventoryMovement; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.action
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Attempted business operation, without oracle labels.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.payload_json
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: json_valid(payload_json).
- Meaning: Ordinary action input.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.decision
- Type: TEXT; required (NOT NULL).
- Allowed values: PENDING, ALLOWED, BLOCKED, FAILED. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Evaluated decision.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.reason_code
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Decision reason.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.attempted_at
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: UTC second.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: length("attempted_at")=20 AND "attempted_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'.
- Meaning: Attempt effective time.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### ActionAttempt.correlation_id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Groups one atomic business operation; not an entity FK.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

Table constraints (in addition to field/FK/trigger rules):

- CHECK(("Customer_id" IS NOT NULL)+("Product_id" IS NOT NULL)+("ReturnPolicy_id" IS NOT NULL)+("Order_id" IS NOT NULL)+("OrderLine_id" IS NOT NULL)+("ReturnRequest_id" IS NOT NULL)+("ReturnLine_id" IS NOT NULL)+("ReturnAuthorization_id" IS NOT NULL)+("AuthorizationLine_id" IS NOT NULL)+("ReturnShipment_id" IS NOT NULL)+("ShipmentLine_id" IS NOT NULL)+("Inspection_id" IS NOT NULL)+("RefundObligation_id" IS NOT NULL)+("Refund_id" IS NOT NULL)+("InventoryDisposition_id" IS NOT NULL)+("InventoryMovement_id" IS NOT NULL)=1)

## EventLog

### EventLog.id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: PK. Uniqueness: Unique primary key.
- Default: none.
- Validation: id GLOB 'EVT-2026-[0-9][0-9][0-9][0-9][0-9][0-9]' AND substr(id,-6)<>'000000'.
- Meaning: Immutable EventLog identifier.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.Customer_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> Customer.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced Customer; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.Product_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> Product.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced Product; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.ReturnPolicy_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ReturnPolicy.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced ReturnPolicy; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.Order_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> Order.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced Order; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.OrderLine_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> OrderLine.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced OrderLine; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.ReturnRequest_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ReturnRequest.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced ReturnRequest; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.ReturnLine_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ReturnLine.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced ReturnLine; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.ReturnAuthorization_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ReturnAuthorization.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced ReturnAuthorization; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.AuthorizationLine_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> AuthorizationLine.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced AuthorizationLine; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.ReturnShipment_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ReturnShipment.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced ReturnShipment; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.ShipmentLine_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ShipmentLine.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced ShipmentLine; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.Inspection_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> Inspection.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced Inspection; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.RefundObligation_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> RefundObligation.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced RefundObligation; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.Refund_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> Refund.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced Refund; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.InventoryDisposition_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> InventoryDisposition.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced InventoryDisposition; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.InventoryMovement_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> InventoryMovement.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Referenced InventoryMovement; exactly one typed target is set.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.attempt_id
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: FK -> ActionAttempt.id. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Related audited action, if any.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.event_type
- Type: TEXT; required (NOT NULL).
- Allowed values: CREATED, STATE_CHANGED, OBSERVED. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Creation, state transition or observation.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.previous_state
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Prior lifecycle state; null for creation/observation.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.new_state
- Type: TEXT; optional (nullable).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Resulting state; null for stateless observation.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.occurred_at
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: UTC second.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: length("occurred_at")=20 AND "occurred_at" GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'.
- Meaning: Effective event time, not volatile runtime clock.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.reason_code
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Explicit explanation.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

### EventLog.correlation_id
- Type: TEXT; required (NOT NULL).
- Allowed values: Nonblank text when non-null. Unit: none.
- Key: neither. Uniqueness: No standalone uniqueness unless specified in table constraints below.
- Default: none.
- Validation: STRICT storage type; enum and referential constraints where specified.
- Meaning: Groups events in one atomic transaction.
- Public export: synthetic values only; free text/JSON requires sensitivity review.

Table constraints (in addition to field/FK/trigger rules):

- CHECK(("Customer_id" IS NOT NULL)+("Product_id" IS NOT NULL)+("ReturnPolicy_id" IS NOT NULL)+("Order_id" IS NOT NULL)+("OrderLine_id" IS NOT NULL)+("ReturnRequest_id" IS NOT NULL)+("ReturnLine_id" IS NOT NULL)+("ReturnAuthorization_id" IS NOT NULL)+("AuthorizationLine_id" IS NOT NULL)+("ReturnShipment_id" IS NOT NULL)+("ShipmentLine_id" IS NOT NULL)+("Inspection_id" IS NOT NULL)+("RefundObligation_id" IS NOT NULL)+("Refund_id" IS NOT NULL)+("InventoryDisposition_id" IS NOT NULL)+("InventoryMovement_id" IS NOT NULL)=1)

## Internal bookkeeping

SchemaVersion.version: required INTEGER PK, exactly 2; technical migration marker, not business data.
IdSequence.entity: required TEXT PK, allocator entity name; IdSequence.last_value: required INTEGER 1..999999, last reserved counter. No default. Writer transaction required. These are technical tables, not assessment entities.

## Phase 3 export extensions

CSV/JSON table exports use exactly the fields above (including technical table fields). CSV column order follows DDL; JSON fields retain their names, use native integers/nulls and canonical sorted keys. CSV NULL is the literal backslash-N sentinel. No floats or ground-truth labels are added.

Sidecar and calculated export fields are NOT database columns. Their types, references, units and derivations are separately documented in export_contract.md: catalog.json, customer_profiles.json, quantity_summary.json, order_totals.json, configuration.json, manifest.json, validation.json and source_manifest.json. No schema migration was needed.
