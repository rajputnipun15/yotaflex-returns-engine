# AI-use disclosure

OpenAI Codex desktop substantially assisted with requirements organization,
database and workflow design, implementation, debugging, tests, synthetic data
generation, validation, analytics, documentation and publication preparation.
The implementation should not be described as written or verified entirely
without AI.

The public [prompt history](ai_prompt_history.md) is a readable edited record of
the available actual requests, not a verbatim transcript. Original wording,
terminal messages and historical evidence are preserved locally. There is one
public prompt-history document; private prompt variants and path-bearing raw logs
are excluded. Prompts from other unavailable tools or sessions cannot be verified
by this record and must be supplied or disclosed by the candidate.

All test and validation results identified as agent-run were executed by Codex.
Candidate code changes, independent review of every rule, and a successful
candidate-run test suite have not been recorded. The candidate's pasted terminal
messages showed a Python version and attempted test commands followed by errors;
they do not establish that independent validation passed.

The code uses Python's standard library and SQLite. It generates synthetic
customers and transactions rather than using real customer data. No complete
external core solution or other person's implementation help is claimed in the
available history. The candidate must understand the code, dependencies, rules,
assumptions and limitations and update this disclosure with any actual personal
review, changes or additional assistance before submission.

Public evidence is selected and, where needed, labelled as redacted or summarized.
Redacted path placeholders are not literal original executable commands. Limited
secret/path screens do not prove that every possible sensitive value is absent.
See [the submission report](final_submission_report.md) for the actual publication
and verification status; preparation alone is not submission to the company.
