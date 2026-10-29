# Business rules and enforcement

All policies are synthetic assumptions, not official retail or tax rules.
Category windows, exclusions, tax, fees, seed and distributions are in
`config/default.json`. Timestamps are canonical UTC text; return deadlines use
inclusive local calendar days in Asia/Calcutta.

## Eligibility and quantities

The policy service checks purchase existence, same-order membership, delivery,
policy-effective dates, category returnability, the category window, requested
quantity and earlier consuming reservations. An over-purchased request is rejected.
Where the request fits the purchase but exceeds the remaining quantity, the service
can partially approve only what remains. Exhausted quantity is blocked.

Evaluation and reservation use the same serialized write transaction. ISSUED and
CONSUMED authorizations consume quantity; pending and rejected requests do not.
An unused cancellation can release a reservation, while shipped evidence remains
consuming. Amendments and a complete correction workflow are not exposed.

## Money

Order-line paid amount equals purchased quantity times unit price, minus line and
allocated order discounts, plus tax. Authoritative money uses integer minor units,
with Decimal/string conversion and HALF_UP rounding where needed. Binary floating
point is rejected by the money conversion utility.

Order discounts use proportional largest-remainder allocation. Combined original
discount and tax are split across stable unit positions; approved batches consume
non-overlapping positions. Entitlement is the paid allocation minus the disclosed
fee. Shipping refunds are excluded. The default tax and fee rates are zero.

A RefundObligation groups attempts against one entitlement. Only successful
payouts reduce the remaining balance. A successful Refund must have a finalized
matching inspection, valid timing, a positive amount within obligation and original
order-line ceilings, and a payment key without an earlier success. Failed retries
use separate REF records and can reuse the logical key. SQL guards defend ceilings;
application calculations derive the legitimate entitlement.

## Inspection, disposition and movements

Inspected quantity cannot exceed received quantity. Accepted dispositions require
matching finalized inspection, chronological consistency and remaining batch
quantity. RESTOCK additionally requires SELLABLE condition. The baseline routes
REPAIRABLE to REFURBISH, UNSAFE to QUARANTINE and IRREPARABLE to SCRAP.

InventoryMovement records execution of one accepted disposition at its full
quantity once. It is not a stock-on-hand ledger. An accepted routing decision by
itself does not prove that a movement happened.

## Events, negative attempts and boundaries

The event utility writes the event and state projection atomically. A failed
transition rolls back the state, amount, event and ID allocation. Terminal or used
financial/receipt evidence is protected from silent changes.

The five isolated [negative scenarios](phase4_verification.md) attempt prohibited
actions through existing enforcement paths. Authorization rejections have durable
attempt records; some directly rejected refund/inventory SQL actions are instead
captured by scenario observations outside the rejected transaction. Normal baseline
late/excluded requests are valid rejection outcomes, not corrupted records.

Overrides are rejected as unsupported. Exchange requests keep replacement pending
and do not generate cash obligations for those units. External payments, a warehouse
balance ledger, full reinspection/corrections and completed replacement fulfillment
remain unimplemented. Guard checks are not a standalone anomaly detector.
