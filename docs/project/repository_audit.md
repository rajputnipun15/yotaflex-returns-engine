# Public repository scope and exclusions

The publication scope is an explicit per-file list, not the entire local workspace.
It includes unchanged application source/configuration, all existing test files,
the two scenario scripts, the field dictionary and SQL schema, curated project
documents, selected evidence, one edited prompt-history document, AI disclosure,
one starter export example and one canonical full export ZIP.

Raw original prompts, local audit tools, source-material extracts, temporary files,
caches, virtual environments, SQLite databases, duplicate full/starter datasets
and path-bearing raw evidence are excluded. Original data, source records and
historical logs remain in the local workspace. A local `outputs/my_starter`
directory was access-denied; its contents remain unverified and are excluded.

Some public reports are concise summaries of private historical evidence rather
than byte-identical raw logs. They are labelled accordingly. The public prompt
history is edited from actual records and does not assert verbatim wording or
unrecorded candidate contributions. No publication license is invented; any
licensing decision requires the owner's review.

The full canonical data is delivered as one compressed archive, including actual
CSV, JSON and SQL exports with the original manifest. The large original JSON and
database files are not separately put into ordinary Git. The archive's member
hashes match the retained originals. This avoids both duplicate datasets and the
claim that a manifest alone delivers full exports.

The staging inventory and content screens check paths, file sizes, required files,
links, checksums and selected secret/account-name patterns. Such screens do not
prove the absence of every sensitive value. Application source and tests were not
rewritten. Current Git and remote publication status is recorded in
[the final submission report](../final_submission_report.md).
