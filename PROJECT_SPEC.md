# YotaFlex Returns Engine — project specification

## Purpose and scope

Build an explainable local synthetic retail returns workflow with relational
integrity, explicit decisions/history, exact refund calculations, controlled
negative attempts and reproducible exports. It is an engineering assessment
project, not a deployed commercial platform.

The ten required entities are Customer, Order, OrderLine, ReturnRequest,
ReturnLine, ReturnAuthorization, ReturnShipment, Inspection, Refund and
InventoryDisposition. Supporting tables represent products/policies, quantity
allocations, obligations, movements, attempts and events. Keys, cardinalities and
lifecycle details are in the [schema](docs/project/schema.md) and
[field dictionary](docs/data_dictionary.md).

## Required data and identifiers

Full mode creates exactly 30,000 orders, 5,000 requests and 8,000 return lines.
Starter mode uses the same pipeline at 300/50/80. Default seed is 20261022;
the fixed simulation clock is separate from actual run metadata. Derived
amounts, quantities and decisions come from facts and documented rules.

Preserve ORD-2026-000001, RMA-2026-000001,
RMAL-RMA-2026-000001-01, RTS-2026-000001 and REF-2026-000001.
IDs are immutable and export-consistent. Return-line sequence is 1–99 and embeds
the complete parent RMA. Other prefixes are implementation choices.

## Rules and validation

Evaluate category/window eligibility and remaining returnable quantity under a
serialized reservation transaction. Shipment/receipt and inspection precede
downstream settlement and accepted disposition. Calculate paid allocations,
discounts, tax and fees in precise minor units, subtract successful payouts and
block duplicate successful payment keys. Keep obligations, attempts and successes
distinct, as well as accepted disposition and completed movement.

Retain events for actual state transitions and validate keys, joins, types/enums,
chronology, lifecycle, money, cumulative quantities, inspection/disposition and
reproduction. Synthetic policy assumptions are documented in
[assumptions](docs/project/assumptions.md); no official policy is invented.

The five labelled scenarios and controls use isolated fixtures, separate
rule-authored ground truth and actual service/SQL enforcement. The specific
above-original-purchase variants were additionally probed but not persisted in
the labelled catalogue. Guard checking does not establish detector accuracy.

## Deliverables and evidence

The public package includes executable source, existing tests, configuration,
supported scenario scripts, documentation, one edited prompt history, disclosure,
a starter export example, and one complete canonical full CSV/JSON/SQL ZIP with
manifest and checksums. The archive excludes the SQLite database and private
runtime metadata; regeneration is documented for CLI validation.

The [export contract](docs/project/export_contract.md),
[reproduction guide](docs/project/reproducibility.md),
[92-entry audit](docs/project/final_requirements_audit.md) and
[final report](docs/final_submission_report.md) distinguish current execution
from selected historical evidence. No result is claimed from planning alone.

## Known boundaries and submission

Standalone detection, authenticated overrides, external payment/carrier
integration, warehouse balances, completed exchange replacement and a full
correction/reinspection workflow remain incomplete. Some rejected SQL operations
lack durable application attempt records. Candidate-independent review and
actual company submission have not been established.

AI assistance is substantial and disclosed in
[AI use](docs/ai_usage_disclosure.md); the
[prompt record](docs/ai_prompt_history.md) is edited, not verbatim.
Original prompts, local dataset copies and historical logs are preserved
privately. No development history, personal contribution or deadline is invented.
The original company send timestamp remains unavailable.

The final user instruction authorizes a new public repository named
`yotaflex-returns-engine` after account/destination verification. Existing
repositories must not be overwritten, no force-push is permitted, and publication
must be verified. Current local and remote status is in the final report.
