# Final submission preparation report

Report date: 29 October 2026 (Asia/Calcutta client date).
Status: **public repository verified**.
Repository: [rajputnipun15/yotaflex-returns-engine](https://github.com/rajputnipun15/yotaflex-returns-engine).
Owner: **rajputnipun15**. Visibility: **public**. Default and verified branch:
**main**. The initial published commit verified independently was
**347a5e64bd7b2b9f63a216baca38b1de019d9937**. This verification report update
follows that commit; the hash identifies the verified publication snapshot, not
the report update's own commit. No project submission to the company is claimed.

## What is prepared

The explicit public scope contains unchanged application source, configuration
and all existing tests; the two scenario runners; schema and dictionary;
curated architecture/rules/requirements/phase reports; selected evidence; one
[edited prompt-history file](ai_prompt_history.md) and
[AI disclosure](ai_usage_disclosure.md); one starter export example; and one
complete canonical full CSV/JSON/SQL archive.

The full ZIP is **18,134,074 bytes** and contains the 50 unchanged manifest-listed
files plus the original manifest. Every member was reread and hash-checked.
[Archive/member hashes](../artifacts/full/archive_checksums.json) identify the
actual data delivered. The archive omits the SQLite database and private runtime
metadata; those are excluded from the original manifest's canonical hashes.
The starter example also matches its 50 manifest-listed hashes.

All original local datasets, exact prompt records and historical logs remain
locally preserved. Publication excludes raw prompt variants, private path-bearing
logs, source-material extracts whose publication rights are not established,
duplicate datasets, SQLite databases, caches, temporary files and local-only
verification tools. The inaccessible local starter directory was not inspected
and is excluded. Public reports are labelled curated summaries where they replace
full historical logs; no private evidence was overwritten.

## Actual verification

All final commands ran in a fresh temporary copy of the selected public files
with source execution through `PYTHONPATH=src`. Python was 3.12.14 and SQLite
3.53.1. Temporary/interpreter paths are redacted in
[command records](evidence/public/commands.json); no command result is invented.

- `python -m unittest discover -s tests -v`: exit 0; **73 tests, 0 failures,
  0 errors, 0 skips**. [Actual log](evidence/public/final_tests.log).
- Root CLI help and help for init-db, inspect-db, generate, validate, export and
  reproduce: exit 0 each.
- Fresh schema initialization and inspection: exit 0 each.
- Starter generation, dataset validation and database inspection: exit 0 each.
- Re-export to a fresh destination: exit 0.
- Second identical-seed starter generation and reproduction comparison: exit 0 each.
- Two fresh Phase 4 scenario runs and the independent scenario comparison:
  exit 0 each.

These are 19 successful commands in total. The
[machine-readable final summary](evidence/public/final_verification.json) identifies
the environment, tests, scope and source hashes. A clean public-source copy was
tested; a public GitHub clone has not been tested.

No new full dataset was generated. Full-generation syntax was checked against
CLI help, but that expensive command was not rerun. The included archive was
packaged from existing validated full exports and screened across all member
bytes for selected path/token patterns. A new full SQL restore was not performed;
historical full restore evidence and the current small-fixture SQL restore tests
are distinguished in the phase reports. Limited screening is not a proof that
every possible sensitive value is absent.

## Local Git and connection status

The original workspace had no Git repository. The final instruction authorizes
initialization in that project root and a truthful initial publication snapshot.
Git is now initialized in that project root on branch **main**. The verified
content snapshot commit is **36313a30f0f3f149741ea31252ae3398a4afa940**,
created with 115 explicitly reviewed files. This report's status update is a
subsequent documentation commit; the hash above identifies the tested content
snapshot, not a claim to be the later report commit's own hash.

The staged file list exactly matched the explicit
[publication inventory](evidence/public/publication_inventory.json). Staged blob
bytes matched reviewed files, tested source hashes matched, the largest file was
the 18.1 MB full archive, and no private paths or raw prompt folder were staged.
Eight representative private paths were checked as ignored. The final whitespace
check passed with Git configured for the preserved CRLF endings; the default
check had reported those line endings as whitespace. No source reformatting was
performed. Project-scoped trust and elevated local Git operations handled the
sandbox's ownership/config-lock restrictions without changing global trust.

During initial preparation, the installed GitHub plugin exposed no account or
repository operations, the GitHub CLI was unavailable and the noninteractive
credential lookup found no usable credential. Initial publication was therefore
blocked. The user subsequently supplied the repository URL after performing the
manual publishing steps. The initial repository creation and push were not
performed by this agent.

The supplied public URL has now been checked using unauthenticated GitHub API/raw
requests and the remote Git ref. The API reports `private: false`, visibility
`public`, owner `rajputnipun15` and default branch `main`. The remote main ref
matched the prepared local commit. Its 115-file tree and every Git blob ID matched
the reviewed local snapshot, with no private prompt folder, local outputs or
preparation directories present.

The public README matched the prepared text; all 35 checked local links and
anchors resolved in the published tree. GitHub returned rendered README HTML
containing the project title. Browser visual appearance and client-rendered
Mermaid layout were not independently inspected. The publicly downloaded full
archive was 18,134,074 bytes and matched its recorded SHA-256. The repository
contains the single consolidated prompt history, AI disclosure, source, tests,
configuration, reports and selected evidence. Results are preserved in
[GitHub verification evidence](evidence/public/github_verification.json).

## Publication follow-up

The local origin is the user-provided HTTPS repository URL. The repository has
already been published; do not create a duplicate repository or replace its
history. This follow-up adds one verification-evidence file, bringing the reviewed
inventory to 116 files, without changing source or tests. Any push of the update
must be a normal fast-forward push to `main`, with no force-push. The original
GitHub connector tools remain
unavailable in this chat; public API and supported local Git operations provide
the verification and update path. No license was invented or added.

## Data use and remaining assessment actions

The [main README](../README.md) documents starter/full generation, validation,
exports and reproduction. The full ZIP delivers exports, not a ready-to-validate
SQLite folder. Generate a fresh database or use a correctly configured SQL restore
for CLI validation. Private duplicate datasets are not published.

The standalone detector, authenticated overrides, external payments, warehouse
balance ledger and completed exchange replacement remain unimplemented. Some
rejected SQL actions have only scenario observations. Above-original-purchase
boundary variants are not labelled persisted fixtures. See the
[92-entry historical audit](project/final_requirements_audit.md).

The candidate must review and understand the solution, disclose any actual
personal review/additional AI use, confirm the original deadline and submit the
verified public repository URL through the instructed recruitment channel.
No claim is made that these actions or a company submission have happened.
