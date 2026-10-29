# Full dataset analytics

Source: `outputs/full_final/returns.db`, checked by Codex against manifest hashes and CSV/JSON exports during the Phase 5 dataset audit. This was an agent-run check, not candidate-independent verification. The fixed-seed synthetic data does not represent observed retail performance. Amounts are integer INR minor units. SQL definitions and machine-readable values are in [the Phase 5 analytics evidence](../evidence/public/analytics.json).

## Volumes

- Order: 30,000 records.
- ReturnRequest: 5,000 records.
- ReturnLine: 8,000 records.
- Inspection: 5,454 records.
- RefundObligation: 4,812 records.
- Refund: 5,281 records.
- InventoryDisposition: 5,454 records.
- InventoryMovement: 5,106 records.
- ReturnShipment: 4,194 records.
- ActionAttempt: 7,591 records.

## Distributions

Each denominator below is the sum of the displayed record counts; attempts, requests, lines and other entities are distinct units. Movement figures are units, not movement records or warehouse stock.

- **request lifecycle states** (denominator 5000): APPROVED: 207, CLOSED: 2,717, INSPECTED: 760, IN_TRANSIT: 244, PARTIALLY_APPROVED: 17, RECEIVED: 273, REJECTED: 526, REQUESTED: 256.
- **return line states** (denominator 8000): APPROVED: 349, INSPECTED: 1,146, PARTIALLY_APPROVED: 3, RECEIVED: 420, REJECTED: 1,177, REQUESTED: 409, SETTLED: 4,116, SHIPPED: 380.
- **authorization decisions** (denominator 7591): ALLOWED: 6,414, BLOCKED: 1,177.
- **authorization reason codes** (denominator 7591): CATEGORY_EXCLUDED: 399, ELIGIBLE: 6,363, NO_REMAINING_QUANTITY: 248, PARTIAL_REMAINING_QUANTITY: 51, WINDOW_EXPIRED: 530.
- **return line customer reasons** (denominator 8000): CHANGED_MIND: 2,253, DAMAGE: 1,215, NOT_AS_EXPECTED: 1,514, SIZE: 3,018.
- **inspection conditions** (denominator 5454): IRREPARABLE: 373, REPAIRABLE: 865, SELLABLE: 4,081, UNSAFE: 135.
- **refund attempt states** (denominator 5281): FAILED: 469, REQUESTED: 240, SUCCEEDED: 4,572.
- **disposition states** (denominator 5454): ACCEPTED: 5,454.
- **disposition actions** (denominator 5454): QUARANTINE: 135, REFURBISH: 865, RESTOCK: 4,081, SCRAP: 373.
- **shipment states** (denominator 4194): DELIVERED: 3,933, MISSING: 261.
- **request resolution** (denominator 5000): EXCHANGE: 600, REFUND: 4,400.
- **movement units by action** (denominator 6676): QUARANTINE: 178, REFURBISH: 1,081, RESTOCK: 4,965, SCRAP: 452.

## Money and integrity

Amounts are gross dataset totals with different denominators; they do not imply every order was returned.
- original order line paid: 1,510,023,317 minor units.
- refund obligations: 102,331,026 minor units.
- successful payouts: 97,710,112 minor units.
- failed paid: 0 minor units.

Independent direct SQL invariants (violation count / relevant entity count):
- Obligations overpaid: 0 / 4812 obligations.
- Duplicate successful payment keys: 0 / 4572 distinct successful payment keys.
- Non-success attempts with payment: 0 / 709 non-success refund attempts.
- Invalid restock movements: 0 / 3816 restock movement records.

## Curated Phase 4 attempts

These are separate fixtures, not rows added to the full baseline. A blocked SQL attempt may be visible only in the observation artifact.
- quantity_negative: BLOCKED / NO_REMAINING_QUANTITY; paid 0 → 0 minor units; restock 0 → 0 units.
- quantity_control: ALLOWED / PARTIAL_REMAINING_QUANTITY; paid 0 → 0 minor units; restock 0 → 0 units.
- excess_negative: BLOCKED / REFUND_SUCCESS_GUARD; paid 100 → 100 minor units; restock 0 → 0 units.
- excess_control: ALLOWED / REFUND_SUCCEEDED; paid 100 → 200 minor units; restock 0 → 0 units.
- inventory_negative: BLOCKED / MOVEMENT_REQUIRES_ACCEPTED_DECISION; paid 0 → 0 minor units; restock 0 → 0 units.
- inventory_control: ALLOWED / RESTOCK_POSTED; paid 0 → 0 minor units; restock 0 → 2 units.
- late_negative: BLOCKED / WINDOW_EXPIRED; paid 0 → 0 minor units; restock 0 → 0 units.
- late_control: ALLOWED / ELIGIBLE; paid 0 → 0 minor units; restock 0 → 0 units.
- duplicate_negative: BLOCKED / DUPLICATE_PAYMENT_KEY; paid 100 → 100 minor units; restock 0 → 0 units.
- duplicate_control: ALLOWED / REFUND_SUCCEEDED; paid 0 → 100 minor units; restock 0 → 0 units.

These 5 negative and 5 control cases validate specific guards; no detector accuracy or false-positive rate is implied. Warehouse on-hand stock and completed exchange replacement are not modeled.
