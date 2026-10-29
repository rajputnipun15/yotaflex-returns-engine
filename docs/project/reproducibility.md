# Reproducibility and package use

Use the main README commands from the repository root. The default seed is
20261022; the configuration fixes the synthetic clock at 2026-10-22T00:00:00Z.
Starter and full modes share the generator. Seed/configuration equality alone
does not prove identical historical source revisions.

Generate two fresh starter destinations with the same seed/config, then run the
CLI `reproduce` command. It rehashes actual deterministic artifacts and compares
logical database content and counts. `manifest.json` does not hash itself, SQLite
physical bytes are excluded, and runtime metadata is volatile. New manifests
record source fingerprints; older retained manifests may report source identity
as UNAVAILABLE even when their content matches.

The included [starter example](../../examples/starter/README.md) and
[full archive](../../artifacts/full/README.md) are export snapshots, not folders
containing a ready-to-validate `returns.db`. Generate a fresh dataset for the CLI
workflow. Alternatively, a correctly configured SQL restore can recreate the
database; restore only to an empty target with foreign keys enabled and roll back
on any error. The test suite covers SQL restore on small generated fixtures.

The full archive contains all 50 canonical source files plus the original manifest.
Its [archive/member checksums](../../artifacts/full/archive_checksums.json) were
verified by rereading the ZIP. It does not include the original SQLite database
or private runtime metadata. Extracted files can be compared with the manifest;
the full dataset need not be regenerated merely to inspect its exports.

Phase 4 reproduction is separate: run the scenario script twice, then the scenario
validator. The checker compares the three JSON artifacts and logical SQL dumps
of ten fixtures per run. Ground truth does not serve as input to the enforcement
operation. There is no statistical detector-accuracy claim.

Historical Phase 3/5 audits are summarized in the phase reports. Current final
commands, exit codes and test output are recorded in
[the submission report](../final_submission_report.md) and selected public evidence.
