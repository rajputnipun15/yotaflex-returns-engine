# Implemented relational schema, version 2

Executable sources: src/returns_engine/model.py and schema.py. Generated SQL:
docs/schema.sql. Every implemented field is documented in ../data_dictionary.md.
All ten required entity names are preserved, including SQL-quoted "Order".

## Relationships and cardinalities

Every child FK below is mandatory unless explicitly nullable. A parent's children
are 0:N unless the later completed workflow requires them; pending records do not
require fabricated descendants.

- Customer 1:N Order; Product 1:N OrderLine; Order 1:N OrderLine and ReturnRequest.
  Customer/currency of a return derive from its original Order.
- ReturnPolicy 1:N ReturnRequest. Effective interval is inclusive effective_from
  to exclusive nullable effective_to. Policy selection/overlap checks are later.
- ReturnRequest 1:N ReturnLine; OrderLine 1:N ReturnLine. A trigger enforces
  same-order consistency. request_id/line_sequence is unique.
- ReturnRequest 1:N ReturnAuthorization supports amendments. AuthorizationLine
  bridges ReturnAuthorization N:M ReturnLine with unique header/line pair,
  positive quantity, and same-request consistency.
- ReturnShipment N:M AuthorizationLine through ShipmentLine with unique pair and
  shipped/received quantities. ReturnLine is reached through AuthorizationLine.
  Unlike Phase 1's proposal, no redundant request FK exists on the shipment;
  consolidated shipments can span requests without contradictory header links.
- ShipmentLine 1:N Inspection supports inspection batches/split shipments.
  Receipt quantity is ShipmentLine.received_quantity; receipt timestamp is the
  containing ReturnShipment.delivered_at. This minimum model shares one receipt
  timestamp per shipment; a Receipt extension is needed for separate timestamps.
- ReturnLine 1:N RefundObligation. Obligation.inspection_id is nullable for
  pending/blocked cases, unique when present, and must trace to the same line.
  One final obligation covers one inspection batch. Multiple null pending
  obligations are representable; application deduplication is later work.
- RefundObligation 1:N Refund attempts. A stable payment_key groups retries;
  only successful payment keys are globally unique. Multiple distinct partial
  successful payouts must fit obligation and original-line balances.
- ReturnLine 1:N InventoryDisposition; inspection_id nullable for proposed or
  rejected cases, required/matching for acceptance. Inspection 1:N dispositions
  splits quantities across routes. Decision is not physical execution.
- InventoryDisposition 1:0..1 InventoryMovement. Each movement executes the full
  accepted quantity exactly once. Partial movement means smaller dispositions.
- Each of the 16 non-audit business/support targets has 1:N EventLog and ActionAttempt. Exactly one typed
  nullable target FK must be populated. EventLog.attempt_id is also nullable;
  application must correlate target/action/correlation_id. EventHistory view
  derives entity_type/entity_id without storing contradictory duplicate fields.

## IDs, allocation and concurrency

Prescribed/tested: ORD-2026-000001, RMA-2026-000001,
RMAL-RMA-2026-000001-01, RTS-2026-000001, REF-2026-000001.
Counters 1..999999; ReturnLine sequence 1..99. SQL validates exact digit patterns
and parent embedding; PKs are immutable and case-sensitive.

Implementation-only prefixes: CUS Customer, ORL OrderLine, PRD Product, POL
ReturnPolicy, RAU ReturnAuthorization, RAL AuthorizationLine, SHL ShipmentLine,
INS Inspection, RFO RefundObligation, DSP InventoryDisposition, MOV
InventoryMovement, EVT EventLog, ATT ActionAttempt. Format PREFIX-2026-000001.
ORL refines the longer provisional Phase 1 OrderLine ID; no existing data changed.
Later exports must reuse these IDs, never independently regenerate FKs.

allocate_id requires a caller transaction. transaction() uses BEGIN IMMEDIATE;
SQLite serializes writers. IdSequence advances atomically, skips manually
imported occupied IDs and rejects exhaustion. Rollback also rolls allocation back;
uncommitted IDs can be reused. Committed reservations may create gaps. Tests use
two competing writer connections. make_id only formats; it does not reserve.
Return-line sequences must be chosen inside the same write transaction; the
unique request/sequence constraint rejects races. Distributed allocation and
merging independently generated databases are outside this local scope.

## SQLite integrity

STRICT types; required fields, nonblank text, PK/UNIQUE/indexed FK RESTRICT;
enums; ID immutability; positive/nonnegative quantities/money; basic timestamp
shape/local chronology; JSON syntax; order-line gross/discount/tax/paid equality
and integer multiplication overflow check. connect enables/verifies FKs on every
application connection; external clients must enable them too.

Triggers check same-order return lines, same-request authorizations, shipped
quantity within each allocation, inspections within received quantities, matching
inspection/return line, finalized inspection for successful refund, obligation
and original-line paid ceilings, unique successful payment key, finalized
inspection/quantity/sellability for accepted restock, and one accepted full-qty
movement. Rejected excessive attempts remain auditable with no payout.

EventLog/ActionAttempt/InventoryMovement are append-only. Terminal Refund,
Inspection and InventoryDisposition cannot be updated/deleted. Used OrderLine,
ShipmentLine, AuthorizationLine and ReturnPolicy evidence is frozen;
RefundObligation freezes after its first attempt. Corrections need new linked
evidence; a correction workflow remains later work.

## Lifecycle allowlist

- Customer ACTIVE -> INACTIVE; INACTIVE -> ACTIVE.
- Order PLACED -> FULFILLED -> DELIVERED.
- ReturnRequest REQUESTED -> APPROVED/PARTIALLY_APPROVED/REJECTED/CANCELLED;
  APPROVED or PARTIALLY_APPROVED -> IN_TRANSIT/CANCELLED;
  IN_TRANSIT -> RECEIVED -> INSPECTED -> CLOSED.
- ReturnLine REQUESTED -> APPROVED/PARTIALLY_APPROVED/REJECTED/CANCELLED;
  APPROVED or PARTIALLY_APPROVED -> SHIPPED/CANCELLED;
  SHIPPED -> RECEIVED -> INSPECTED -> SETTLED.
- ReturnAuthorization ISSUED -> SUPERSEDED/CANCELLED/CONSUMED.
- ReturnShipment CREATED -> DISPATCHED -> DELIVERED/MISSING.
- Inspection RECORDED -> FINALIZED.
- Refund REQUESTED -> REJECTED/FAILED/SUCCEEDED; retry creates a new row.
- InventoryDisposition PROPOSED -> REJECTED/ACCEPTED; physical execution is a
  separate InventoryMovement, replacing the provisional POSTED state.

record_event validates target, calendar date and transition, then atomically
appends event and updates projection, including related value changes. Failure
rolls back event, reserved ID and projection. SQL requires a matching latest event
for state updates and rejects forbidden pairs/backdated per-target events.
CREATED captures initial state; OBSERVED cannot change state. Same-second history
order follows insertion rowid. Timestamps are explicit, never wall-clock defaults.

Trusted initial/import fixtures can start in any valid enum. Raw SQL can append
a transition event without applying its projection; use record_event for atomic
business operations. The Phase 3 generator records initial events and replays generated history; imported raw SQL still requires full validation. Aggregate progress and business prerequisites have measured baseline checks.

## Application enforcement boundary

Implemented: FK-enabled connections, transaction/savepoints, atomic ID counters,
calendar validation for event timestamps, transition utility, exact money helpers.
Phase 3 adds cumulative reservations, restricted cancellation, window/exclusion checks, unit entitlements, baseline generation, replay and export reproducibility. SQL guards remain defense in depth: a supplied partial-unit entitlement is not proved correct by its SQL ceiling, so independent baseline validation recomputes it. Override authority, amendments/corrections, completed exchanges and anomaly truth remain pending.


## Phase 3 implementation update (supersedes the pending list above)

No schema migration: 20 physical tables, schema version 2 and existing field
constraints remain unchanged. The master-first generator uses all required
entities plus the existing supporting tables. Catalog prices/returnability and
customer region/segment configuration are sidecars, not new database columns.

policy.authorize_request now serializes cumulative reservations, evaluates
window/category/policy/quantity checks and records decisions/allocations/events.
Unit-based entitlements, normal refunds and dispositions are generated from
source records. The validation module independently replays baseline policy and
event histories, reconciles quantities/money and checks aggregate progress.
CSV/JSON/SQL snapshot exports and actual-file reproducibility are implemented.
See generation.md, export_contract.md and phase3_verification.md for current scope.

Cancellation supports only an unused ISSUED authorization with no later unit
allocations; it cancels header/request/accepted lines and releases reservations.
Amendment/supersession, authorized overrides, exchange replacement, correction
workflows, dedicated anomaly/oracle and physical inventory balances remain open.
