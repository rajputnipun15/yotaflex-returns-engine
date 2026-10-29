# Baseline export contract, version 1

Schema version stays 2; no table/field migration was needed for Phase 3.
Operational CSV/JSON use exactly the data dictionary's 139 business/support
columns, plus the two documented bookkeeping tables. IDs are read from SQLite,
not regenerated. Every file is UTF-8, LF, with deterministic row ordering.

## Table files

csv/<Entity>.csv and json/<Entity>.json exist for all 20 physical tables.
CSV headers follow PRAGMA/DDL column order. JSON arrays retain exact field names,
native integer values, text and null; object keys are canonically sorted.
Rows sort by id, or entity for IdSequence, version for SchemaVersion.
CSV NULL is literal backslash-N (`\N`); blank strings are not substituted for
NULL. Generated business strings never equal that sentinel. Money stays integer
minor units; timestamps stay canonical UTC text. No ground-truth labels exist.
Config rejects the sentinel as a region, segment, category or return reason;
export also fails safely if any stored literal equals it, including imported data.

schema.sql is the approved standalone schema. seed.sql is a complete trusted
snapshot import, including history and counters. Run it only against an empty
business database, using foreign keys ON. A temporary CHECK guard rejects any
existing business/counter rows. Within one transaction it suspends triggers,
loads final snapshots and historical events in FK dependency order, then restores
every trigger before commit. STRICT types, field CHECKs, PK/FK and unique indexes
remain active. This is needed because historical previous states differ from
final snapshots; normal workflow writes never suspend triggers. On import error,
roll back the transaction. Tests verify import into a fresh DB, refusal to append
to a populated DB, restored append-only guards and full baseline validation.

## Source sidecars (not database columns)

catalog.json is an array, one row per Product, unique product_id FK -> Product.id.
Each field is required, no defaults; public-safe invented values only:

- product_id TEXT, exact stored identifier.
- name TEXT, equals Product.description (generic invented product name).
- category TEXT, equals Product.category and a configured category key.
- unit_price_minor INTEGER >0, catalog source price within category bounds;
  order prices copy this value. Unit: currency minor units.
- returnable BOOLEAN, the configured synthetic category eligibility flag.
- window_days INTEGER 1..90, category return window in calendar days.

customer_profiles.json is an array, one row per Customer, all fields required:

- customer_id TEXT, unique FK -> Customer.id.
- region TEXT, one of configuration.regions, no real address or personal data.
- segment TEXT, one of configuration.segments, synthetic purchase-frequency group.

These sidecars let the approved minimal schema retain region/segment/catalog
configuration without adding ad hoc columns. Customer.synthetic_name also embeds
the synthetic region/segment for convenient inspection. Source configuration is
fingerprinted in the manifest; this is not an external retail dataset.

## Calculated sidecars (not database columns)

order_totals.json has one required unique order_id FK -> Order.id. Remaining
fields are required nonnegative INTEGER minor units, no defaults:

- goods_paid_minor = sum(OrderLine.paid_minor).
- tax_minor = sum(OrderLine.tax_minor), already included in goods_paid_minor.
- shipping_paid_minor = Order.shipping_paid_minor; not refunded in this baseline.
- total_paid_minor = goods_paid_minor + shipping_paid_minor.

quantity_summary.json has one required unique return_line_id FK -> ReturnLine.id.
All quantity fields are nonnegative INTEGER units, no defaults, except nullable
eligible_quantity (not yet evaluated when request pending/cancelled):

- purchased_quantity: original OrderLine quantity.
- requested_quantity: ReturnLine.requested_quantity.
- eligible_quantity: independent replay of policy and prior reservations at the
  original decision; not a ground-truth label or input to the decision engine.
- authorized_quantity: sum of active/consumed allocation quantities.
- received_quantity: sum of allocated ShipmentLine receipts.
- inspected_quantity: sum of their Inspection batches.
- successfully_refunded_quantity: inspection units whose positive entitlement
  is fully paid, counted once per obligation; pending/failed/zero-entitlement
  obligations contribute zero. Partial monetary payouts would not imply fractional
  unit refunds; this baseline settles whole inspection-batch obligations.

## Manifests and reports

configuration.json is the complete resolved config: version, master seed, scale,
requested counts, fixed business clock, monetary policies and distributions.
manifest.json records seed, scale, schema/generator/config versions/checksum,
requested/actual counts, normalized reproducible command and files entries:
name TEXT relative path, row_count INTEGER or null for non-tabular objects,
sha256 TEXT (64 hex), size_bytes INTEGER. Output path is replaced by <OUTPUT>;
actual command arguments and measured runtime live in run_metadata.json.
New manifests also record generator_source_sha256, a SHA-256 fingerprint of
package source filenames and bytes in stable filename order. Re-export preserves
the original fingerprint; when an older manifest lacks one, it remains null
rather than inventing provenance. A matching artifact checksum does not by itself
establish that the source revision is identical; reproduce reports source identity
as MATCH, DIFFERENT or UNAVAILABLE separately from measured content equality.

source_manifest.json declares fully synthetic provenance, no external datasets,
generator version and configuration SHA-256. It does not claim a third-party
license or official company policy. validation.json and validation.md contain
measured violation numerator/denominator/interpretation, statuses, counts and
coverage. Zero-denominator metrics are NOT VERIFIED/not applicable, never an
invented 100 percent. Overall PASS means no applicable baseline check failed;
it does not establish anomaly-detection performance.

Canonical business/report files are hashed. manifest.json excludes its own
self-hash. returns.db bytes are excluded (SQLite physical layout is not canonical);
reproduce separately checks DB counts and logical rows against canonical JSON.
run_metadata.json is excluded because runtime/environment/command paths vary.
Its file sizes are measured before that metadata file writes itself.

Generation uses a private sibling staging directory and promotes only after all
validation/exports/manifest complete. Existing destinations, even empty ones,
are rejected; choose a fresh path. Failure removes only the owned staging folder.
