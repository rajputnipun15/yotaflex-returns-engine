# Architecture

The application runs locally with Python's standard library and SQLite. There is
no web server, external dataset, carrier integration or payment provider. Python
3.11+ and SQLite 3.37+ with JSON functions are required.

`model.py` defines field metadata, constraints and lifecycle transitions.
`schema.py` builds the SQLite schema, enables foreign keys, and provides
transactions with nested savepoints. `ids.py` allocates stable IDs inside the
writer transaction; `events.py` atomically appends history and updates the state
projection. `money.py` provides exact integer/Decimal calculations.

`config.py` validates synthetic policies and scale settings. `policy.py` evaluates
eligibility and serializes cumulative quantity reservations. `generator.py`
creates masters and workflow facts in dependency order. `validation.py` checks
persisted relationships, money, policy decisions and event history independently
of the generator's action sequence. `exports.py` writes canonical files;
`pipeline.py` stages generation and promotes only complete validated output.

The CLI in `__main__.py` exposes `init-db`, `inspect-db`, `generate`, `validate`,
`export` and `reproduce`. The separate Phase 4 scripts create isolated fixtures
and compare expected decisions with actual service/database enforcement.

The schema has 18 business/support tables and two technical tables. An obligation
is separate from a payment attempt, and an accepted disposition is separate from
a movement. Shipment and authorization allocations are quantity-bearing bridges.
The model supports pending work and missing shipments without broken references.

Schema constraints defend structural and posting invariants. Cumulative quantity
reservation depends on the authorization service; bypassing it does not obtain
a universal cross-authorization database constraint. These are bounded simulation
services, not production orchestration.

See [business rules](business_rules.md), [schema](schema.md),
[the unchanged field dictionary](../data_dictionary.md) and
[reproducibility](reproducibility.md).
