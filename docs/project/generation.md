> This describes the baseline design and its synthetic assumptions. Deliberate scenarios were added separately; see [Phase 4 verification](phase4_verification.md).

# Phase 3 generator design and synthetic distributions

The same BaselineGenerator and pipeline.generate implement starter (300/50/80),
full (30000/5000/8000), and custom counts. Counts name Order, ReturnRequest and
ReturnLine separately. Validation rejects impossible counts; it never truncates
required records to make generation pass. Default seed 20261022, overridable CLI.

## Dependency order and history

Customers -> Products/ReturnPolicy -> all Orders -> all OrderLines -> all
ReturnRequests/ReturnLines -> authorizations -> shipment allocations/receipts ->
inspections -> refund obligations/attempts -> disposition decisions/movements.
Initial rows and transitions use the existing event utility. All source request
masters precede any authorization. Request processing follows stable input order;
request times are monotone per original order to make cumulative replay explicit.
All IDs use the existing transactional allocator and return-line formatter.
No independently guessed foreign-key IDs or post-hoc relationship repair.

One local random.Random stream is seeded once. Dictionary categories/weights/
segments sort before sampling; arrays retain their configured order. Equivalent
JSON key ordering cannot alter generated records. No wall clock, set iteration
or uncontrolled random source controls business outputs. Config pins a fixed
as_of (2026-10-22T00:00:00Z); source-derived dates must not exceed it.
New generation manifests also record a stable fingerprint of package source
filenames and bytes. Earlier preflight snapshots did not capture this fingerprint;
matching a seed/configuration alone does not identify their development revision.
Two retained early starter preflights share a seed and config fingerprint but
have different file checksums. Treat those as historical development artifacts;
the final starter and full pairs are separately verified for reproducibility.

Customers register 365..424 days before as_of. Orders are placed far enough
before as_of for the longest configured window plus simulated workflow duration,
with a 120-day uniform age spread and hour variation; delivery is 2..7 days later.
In-window request age is uniform 1..category-window days; late age is window+1..10.
Repeated requests on an order advance by at least one hour. Later normal requests
after an earlier late request may also be rejected; outcomes always follow facts.

## Configurable distributions (synthetic, not industry measurements)

config/default.json records the assumptions. Customer count is orders/divisor,
minimum 1 (default divisor 3). Regions sample uniformly from the configured list;
segment membership samples uniformly, while purchase selection weights default to
OCCASIONAL 1, REGULAR 3, LOYAL 8, creating unequal purchase frequency.

Catalog category weights: clothing 35, footwear 25, electronics 15, home 20,
personal care 5. Catalog creation cycles categories so all exist; purchases use
the weights. Catalog prices sample integer minor units within category bounds.
Names are generic and invented. No external data/images or real personal data.

Purchased quantity weights: 1:55, 2:25, 3:15, 4:5. Order-line count weights:
1:45, 2:30, 3:20, 4:5; count increases if required to support assigned return lines.
Return-line counts are balanced 1..99 per request; a seeded shuffle assigns the
remainder to requests, giving exactly 8000 across 5000 in full mode.
Line discount bps draws [0,0,0,500,1000,1500]; order bps [0,0,0,500,1000].
Repeated zeros deliberately favor no discount. Returned quantities sample between
1 and purchased quantity; the first stratified partial case asks for one unit.

Request reason weights: SIZE 40, CHANGED_MIND 30, NOT_AS_EXPECTED 20, DAMAGE 10.
Normal inspected-condition weights SELLABLE 90, REPAIRABLE 7, IRREPARABLE 3.
Damage weights REPAIRABLE 60, UNSAFE 15, IRREPARABLE 25. These are sampled physical
inputs; routes and amounts are derived, not independently randomized outcomes.

Remaining request workflow/input modes default NORMAL 58, LATE 8,
PENDING_REQUEST 5, PENDING_SHIPMENT 5, MISSING 5, PENDING_INSPECTION 5,
PENDING_REFUND 4, PENDING_MOVEMENT 4, DAMAGE 6. Exchange selection 12%,
provider failure with legitimate retry 10%, eligible split shipment 15%.
Random progress modes are simulated external workflow availability, not policy
decisions. Missing shipments time out after dispatch+3 days and never have receipts.

coverage_strata=true intentionally fixes the first 12 source/progress cases:
partial, repeated/full, late, excluded category, exchange, pending request,
pending shipment, missing shipment, pending inspection, pending refund,
pending movement, damage. The first paired purchase is returnable with a higher
quantity; selected early orders use returnable categories, and one excluded
category if configured. This ensures useful starter coverage where counts permit.
It changes realized frequencies; configured weights are not promised exact
percentages. Disable strata for unforced sampling. Small custom datasets or
altered catalogs/quantity bounds may not cover every case; measured coverage is
reported. No invalid data or deliberate anomaly is injected by these strata.

## Eligibility and quantities

authorize_request uses BEGIN IMMEDIATE via transaction(), so evaluation and
reservation share the writer lock. For each original line: remaining=purchased
- prior consuming authorizations. ISSUED and CONSUMED consume; REQUESTED has no
allocation; rejected lines consume zero. CANCELLED/SUPERSEDED allocations release
only when never used in a shipment. Shipped history remains conservatively
reserved. The cancellation helper rejects used reservations and cancellations
that would shift later allocated unit positions. No amendment/supersession service
is exposed; the baseline does not generate cancellations/amendments.

Checks: existing purchase, same order, delivered before request, effective policy,
configured category returnability/window, requested <= purchased, available
quantity, no unsupported override. Whole-purchase excess is blocked; ordinary
partial remaining entitlement is approved up to remaining quantity. Repeated
approval of the same request is refused. Decisions/reason codes are persisted
as ActionAttempt plus state events and allocation records. Its payload includes
evaluated quantities/deadline for audit, not oracle labels; decision functions
read original records/config and never read ground-truth or these audit outcomes.
For example, with a 30-day window, delivery on 1 September permits a request
through 1 October inclusive in the configured business timezone. All categories
have explicit window_days; the policy header fallback does not override them.

Eligible, requested, authorized, received, inspected and successfully refunded
quantities are distinct. quantity_summary.json documents each; pending eligibility
is null. Missing shipment remains IN_TRANSIT/SHIPPED with zero receipt, no
inspection/refund/stock movement. Pending requests stay REQUESTED with no approval.

## Financial and downstream baseline

Gross=unit price*quantity; line discounts first, then one order discount allocated
proportionally over line net values using largest remainder and stable line ties.
Tax is HALF_UP basis points on each discounted line (default 0); fees default 0.
Shipping is recorded but not refundable. Every calculation uses integers or
existing precise helpers, never authoritative binary floating point.

Original combined discount and tax are allocated to stable purchased unit
positions by quotient/remainder. Authorization sequence assigns nonoverlapping
unit positions; inspection batches consume those positions in deterministic
order. Batch entitlement=sum(original unit paid)-disclosed rounded fee.
Successful payouts alone reduce remaining obligation balance. Provider failure
creates a FAILED zero-paid attempt; its legitimate retry has a new REF ID and
the same payment key. Pending refund remains REQUESTED with paid zero.

Inspection follows actual receipt. SELLABLE/restock, REPAIRABLE/refurbish,
UNSAFE/quarantine, IRREPARABLE/scrap is deterministic. Acceptance and physical
movement have separate events/records. Pending movement has an accepted decision
without a physical movement. Closed refund requests require settled accepted
lines and completed payment/stock routing; rejected lines remain rejected.

Exchanges reach inspection/disposition but remain pending replacement, with no
cash obligation and no fake completed replacement. A completed exchange engine,
real carrier/payment integrations, correction flows and full inventory balances
are not claimed. Overrides are deliberately unsupported, not authorized by text.

## Validation and safe outputs

Independent validation replays cumulative policy outcomes, allocation/receipt/
inspection limits, original money/tax/discount allocations, batch entitlements,
payout balances, routes/movements and lifecycle history/projections. Metrics have
actual numerator/denominator/interpretation and examples; no oracle is read.
The validator targets generated baselines. If a database has externally corrupted
foreign keys, it reports measured FK violations and explicitly stops before
dependent business checks rather than treating them as passed. Further adversarial
corruption handling remains work for the dedicated anomaly/validation phase.
Exports stream SQLite rows; only source scheduling and bounded non-event maps
are retained in memory. FK indexes support per-line lookups; transactions batch
generation. Event/index/trigger integrity has a real measured cost, recorded in
run_metadata.json. Full outputs are staged and promoted only after validation
and complete exports. See export_contract.md and phase3_verification.md.
