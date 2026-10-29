> This describes the baseline design and its synthetic assumptions. Deliberate scenarios were added separately; see [Phase 4 verification](phase4_verification.md).

# Configurable assumptions; not official YotaFlex policy

No official return duration, rate, exclusion list, tax jurisdiction or fee is
specified. The following defaults are implemented as synthetic configuration;
they are not official company policies.

- Seed 20261022 is a user mandate (brief example). Full counts 30,000/5,000/8,000;
  starter is 300/50/80. All ID years are 2026 under Phase 2 instruction.
- Window 30 calendar days inclusive from delivery, interpreted in Asia/Calcutta.
  UTC storage YYYY-MM-DDTHH:MM:SSZ; the default simulated as-of is
  2026-10-22T00:00:00Z, independent of seed.
- Exclusions are configurable; no official categories claimed. ReturnPolicy JSON
  must be an array; later application verifies category-string elements.
- Synthetic INR, two-decimal precision; integer minor units, Decimal HALF_UP.
  No floats in authoritative financial calculations. Any configured currency
  code remains a synthetic three-letter label modeled with two decimal places;
  the generator does not infer real-world currency-specific minor-unit scales.
- Store line discount and allocated order discount separately. Original order
  discount total later equals sum of allocated line discounts; there is no
  redundant order total column. Allocate original discounts/tax to stable unit
  positions using quotient/remainder, so partial sums reconcile exactly.
- Default tax/fee zero. ReturnPolicy.fee_bps supports synthetic configurable fees;
  obligation stores fee deducted from entitlement. No legal tax compliance claim.
- Shipping paid recorded on Order; shipping refunds excluded from minimum scope.
  Add a separate shipping obligation if enabled later.
- Refund after accepted finalized inspection, one final obligation per batch.
  Damage refundability differs from resale condition. Failed/blocked attempts
  do not consume entitlement; retries share logical key and have distinct IDs.
- Approved quantities reserve stock entitlement; cancellation releases only
  unconsumed reservations. Aggregate enforcement is implemented for the bounded baseline service.
- Restock requires SELLABLE (SQL enforced). The baseline maps remaining routes:
  REPAIRABLE/refurbish, UNSAFE/quarantine, IRREPARABLE/scrap.
- Exchange emits a pending-replacement observation, with no cash refund for the
  same units; actual replacement fulfillment remains open. Missing shipment stays exception without
  fabricated receipt. Override needs authority/evidence, not only free text.
- Consolidated multi-request shipments supported via allocations. One receipt
  timestamp per shipment, multiple inspections. Movement executes full accepted
  decision once; split decisions for partial physical execution.

Open questions: original send timestamp/timezone and actual deadline; override
authority; tax/fees/shipping; exchanges; damaged/lost goods; reinspection and
corrections; corrupt-data fixture versus blocked-action requirements. FAQ Q11
permits documented reasonable assumptions; these values are not company policy.


## Phase 3 adopted synthetic configuration

config/default.json and the resolved output configuration make these assumptions
executable, not official company policy. Fixed seed/clock, INR minor units, zero
default tax/fees, shipping excluded, 30-day fallback and category windows are
implemented/tested. Clothing/home 30 days, footwear 45, electronics 15; personal
care excluded. Category fields and distributions are configurable.
The policy header's window_days is a fallback metadata default; all configured
categories explicitly specify window_days and those values determine eligibility.
Change the category-specific field to change that category's actual window.

Customer regions/segments and catalog source prices are documented sidecars.
Weighted category/quantity/discount/reason/condition distributions and explicit
first-12 coverage strata are synthetic design choices, not retail statistics.
The strata can be disabled and realized frequencies are measured. All random
dictionary keys are sorted before sampling. See generation.md for exact weights.

Source values, unit allocations, fees, events and baseline exports are now
implemented; prior references to those as future work are historical Phase 2
context. Overrides remain rejected; exchanges await replacement; full correction,
amendment and lost-shipment compensation policy are not implemented. No deliberate
anomaly data or oracle is injected in this phase.
