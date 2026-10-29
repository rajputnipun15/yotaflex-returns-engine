# Starter export example

This example contains the 50 unchanged manifest-listed deterministic files from
the retained starter baseline, its manifest and this explanation. The source
hashes were verified before and after copying. It contains 300 orders, 50 return
requests and 80 return lines; all names and transactions are synthetic.

CSV, JSON, schema and SQL seed exports are included. The SQLite database and
machine-specific runtime metadata are excluded. This folder therefore cannot be
passed directly to the current dataset validation CLI, which expects `returns.db`.
Generate a fresh starter database with the [main README](../../README.md) to run
that workflow. SQL restore semantics are documented in the
[export contract](../../docs/project/export_contract.md).
