# Characterization tests (WP0 regression tripwire)

These tests capture the **current** behavior of the critical paths as of the
`upstream-base` fork point. They are a tripwire for the commercialization work
packages, not a specification of desired behavior.

Covered paths (per WP0 of the master implementation plan):

| Path | File |
|---|---|
| Notebook create/read/update/delete cycle | `test_notebook_crud_characterization.py` |
| Source ingestion (file upload + URL) | `test_source_ingestion_characterization.py` |
| Search — text and vector | `test_search_characterization.py` |
| Chat over a notebook | `test_chat_execute_characterization.py` |

## Rules for these tests

- **They assert what the code does today, not what it should do.** Where current
  behavior is arguably wrong, the test says so in a comment rather than
  asserting the "correct" value. Do not "fix" a characterization test to make it
  express better behavior.
- When a work package **intentionally** changes one of these behaviors, update
  the test in the same commit as the behavior change, and say so in the commit
  message. An unexplained diff here means an accidental regression.
- They mock at the domain/repository boundary (the pattern the rest of
  `tests/` uses), so they run in CI without a live SurrealDB. They exercise the
  real routers, real request parsing and real response models — the API contract
  — but not real persistence.
