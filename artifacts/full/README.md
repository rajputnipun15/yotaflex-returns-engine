# Canonical full export

`yotaflex-full-20261022.zip` contains the 50 unchanged manifest-listed files of
the retained full baseline plus its unchanged manifest. These are the actual
complete CSV, JSON and SQL exports, not only evidence that exports once existed.
The archive was built from existing files without regenerating the full dataset.
Its members were reread and SHA-256 checked against the originals.

The archive contains 30,000 orders, 5,000 requests and 8,000 return lines, plus
supporting tables, schema, seed SQL, config, source manifest and validation reports.
`archive_checksums.json` records its byte size, archive hash, member sizes and
member hashes. The separate manifest/config/validation files here provide a quick
review without extracting the archive.

The SQLite database and private `run_metadata.json` are excluded. Those are
checksum exclusions in the original manifest. To use the current dataset validation
CLI, generate a database with the documented full command or perform a correctly
configured SQL restore. A new full restore was not performed during publication
preparation; the historical restore and current small-fixture restore tests are
separately identified in the verification reports.

Only one canonical full archive is included. Historical/repeat full datasets and
all private originals remain local. Limited content screening does not guarantee
that every possible sensitive value is absent.
