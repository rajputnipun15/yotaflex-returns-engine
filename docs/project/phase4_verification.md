# Phase 4 — curated negative scenarios

This selected report summarizes executed service/database checks from isolated
fixtures. Expected outcomes are authored from rules and known facts; observations
are separate. The valid baseline was preserved.

| Attempt | Observed negative reason | Legitimate control |
| --- | --- | --- |
| Excess remaining quantity | NO_REMAINING_QUANTITY | One remaining unit partially approved |
| Excess remaining entitlement | REFUND_SUCCESS_GUARD | Remaining 100 minor units paid |
| Movement before qualifying inspection | MOVEMENT_REQUIRES_ACCEPTED_DECISION | Two sellable inspected units moved |
| Late request without override | WINDOW_EXPIRED | Approval on inclusive deadline |
| Replay successful payment key | DUPLICATE_PAYMENT_KEY | One successful retry after FAILED zero-paid attempt |

All five prohibited actions were blocked and five controls produced their expected
effects. Paid amounts stayed 100 to 100 in each rejected refund case; no negative
case added payout or restock units. Rejected refund state transitions and rejected
movement insertions left no attempted success event behind. Authorization
rejections legitimately added rejection events without reserving new quantity.

Quantity/deadline decisions use the serialized policy service. Refund ceilings,
successful-key uniqueness and inspection-backed movement use database guards.
Database messages are normalized by the harness, not a production API. Failed
payment retries remain distinct from duplicate successful payouts.

The suite grew from 63 baseline tests to 73 after adding ten focused cases. The
separate checker reopened ten databases per run, checked references, balances,
state history and SQLite integrity, and compared 10/10 logical database digests
and 3/3 JSON files across repeated runs.

The selected [ground truth](../evidence/public/phase4_ground_truth.json),
[observations](../evidence/public/phase4_observations.json) and
[results](../evidence/public/phase4_results.json) describe the retained local
fixtures. Database filenames inside those artifacts are fixture references; run
the documented scripts to recreate them. No fixture databases are published.

These are five curated guard checks, not a meaningful precision, recall, F1 or
false-positive estimate. The exact above-original-purchased and above-original-
paid variants were checked separately in Phase 5 but are not labelled persisted
Phase 4 fixtures. Some upstream fixture entities use valid initial snapshots rather
than every upstream transition. Unsupported overrides, durable auditing of some
rejected SQL actions and other workflow gaps remain disclosed.
