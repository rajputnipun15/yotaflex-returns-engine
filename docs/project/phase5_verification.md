# Phase 5 — final business validation and analytics

This public summary distinguishes selected inherited evidence from the final
verification run. Phase 5's baseline and final suites each passed 73 tests with
zero failures, errors and skips. No new full dataset was generated.

The retained starter and full baseline validators passed. CSV/DB parity covered
4,550 starter rows and 463,617 full rows; logical JSON hashes, identifiers, foreign
keys and manifests were checked. Full counts were 30,000 orders, 5,000 requests
and 8,000 lines. All 400 manifest hashes across eight retained datasets still
matched Phase 3 closure. The final full/repeat pair matched 50/50 files.

Phase 4's final/repeat fixtures and new reproduced fixtures passed their checks.
Two additional ephemeral probes blocked a 3-unit request against a 2-unit purchase
with QTY_EXCEEDS_PURCHASED and a 201-minor-unit success against 200 originally
paid/entitled with refund_success_guard. They did not create an authorization,
payout or residual success event. Those variants are not persisted in the labelled
Phase 4 catalogue.

The full-data analytics record 5,454 inspections, 4,812 obligations, 5,281 refund
attempts, 5,454 dispositions, 5,106 movements, 261 missing shipments and 600
exchange requests. See [analytics](analytics_summary.md) for denominators and
the selected [machine-readable calculations](../evidence/public/analytics.json).
The selected [baseline audit](../evidence/public/baseline_audit.json) retains
counts, checks and hashes without machine-specific raw command logs.

The README workflow was executed locally with fresh output names; Phase 5 did not
verify a clean Git checkout or repeat a full SQL restore. The current final
preparation reruns supported commands and tests separately, as documented in the
[submission report](../final_submission_report.md).

The assessment can be prepared for submission with clearly disclosed partial work.
Missing detector/override/payment/stock-ledger/replacement capabilities are not
implemented merely to improve a completion count. Candidate-independent review,
deadline confirmation and actual company submission remain unrecorded.
