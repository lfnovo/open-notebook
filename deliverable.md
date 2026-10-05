# Fix for issue #1452 — `GET /api/notebooks/{id}` returns 500 on a malformed id

**Repository:** `lfnovo/open-notebook` · **Base commit:** `60e3c21` (main)
**Branch:** `fix/1452-bare-notebook-id-returns-400` · **Commit:** `0a79a63`
**Issue:** [#1452](https://github.com/lfnovo/open-notebook/issues/1452)

---

## 1. Summary

`GET /api/notebooks/abc123` returned **500** with a SurrealDB driver message in the response body. The
notebooks router was the only single-record endpoint that answered 500 for an id it simply could not
parse; `/api/sources`, `/api/notes` and `/api/transformations` all answered 400 for the same request.
The fix routes the parse failure through the error type the rest of the codebase already uses, so all
four now answer 400.

Behaviour is otherwise unchanged: a well-formed id still returns 200, and an id that parses but names
no record still returns 404.

## 2. Root cause

`get_notebook` built its own `RecordID` and handed the raw path segment to `ensure_record_id()`:

```python
# api/routers/notebooks.py:238 (before)
result = await repo_query(query, {"notebook_id": ensure_record_id(notebook_id)})
```

`ensure_record_id` (`open_notebook/database/repository.py:78`) is a thin wrapper over
`RecordID.parse(value)` and deliberately lets the driver's `ValueError` escape. Because
`get_notebook` ends in a catch-all:

```python
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"Error fetching notebook {notebook_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching notebook: {str(e)}")
```

the driver's `ValueError` fell into the last arm. A client-side formatting mistake was reported as a
server error, and `str(e)` put the driver text — which describes the app's internal table naming —
into the response body.

The sibling endpoints never hit this because they do not build the `RecordID` themselves. They call
the domain layer, which validates the id first:

```python
# open_notebook/domain/base.py:111-120 (ObjectModel.get)
table_name = id.split(":")[0] if ":" in id else id
if cls.table_name and cls.table_name == table_name:
    target_class = cls
else:
    found_class = cls._get_class_by_table_name(table_name)
    if not found_class:
        raise InvalidInputError(f"No class found for table {table_name}")
```

That `InvalidInputError` propagates and becomes a 400. `get_notebook` bypassed exactly this step, so
the two families of endpoint disagreed about the same class of client error — which is the substance
of the issue.

## 3. Why HTTP 400 and not 404 / 422

- **400, not 404.** 404 means "this resource does not exist", and the app reserves it for that:
  `get_notebook` raises it on an empty query result, and `api/main.py` maps the domain layer's
  `NotFoundError` to it. An unparseable id never reaches the database, so we cannot claim the notebook
  is absent — we can only say the request was malformed. Returning 404 would also make a typo
  indistinguishable from a deleted notebook.
- **400, not 422.** 422 is used in this codebase for `ConfigurationError` (`api/main.py`), i.e. a
  well-formed request whose *content* conflicts with server state. A path segment that is not a record
  id is a syntax-level error, and 400 is what every sibling endpoint already returns for it. Matching
  the existing behaviour is the point of the fix.
- **400 is also the repo's established convention for this exact case**, which is why the fix
  introduces no new error type and no new status code.

## 4. Reproduction

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8000/api/notebooks/abc123
```

Before, this printed `500` with:

```json
{"detail": "Error fetching notebook: invalid string provided for parse. the expected string format is \"table_name:record_id\""}
```

`notebook:a:b` reproduces the same way (SurrealDB's parse fails with a different message,
`too many values to unpack (expected 2)`).

## 5. The fix

`api/routers/notebooks.py` — one helper plus its single call site:

```python
def _notebook_record_id(notebook_id: str) -> RecordID:
    """Parse a notebook id, raising InvalidInputError (mapped to 400) if malformed.

    `ensure_record_id` lets SurrealDB's parse error escape, and the catch-all
    below would report it as a 500 leaking a driver message. A malformed id is a
    client error, so raise the typed error the sibling single-record endpoints
    already produce through `ObjectModel.get`; the `except OpenNotebookError`
    arm re-raises it and the global handler answers 400.
    """
    try:
        return ensure_record_id(notebook_id)
    except Exception as e:
        # Parsing is pure, so any failure here means "not a record id". A
        # parseable id is left alone: unknown records still 404.
        raise InvalidInputError(
            f"Invalid notebook id: '{notebook_id}' "
            "(expected the format 'notebook:<id>')"
        ) from e
```

This **reuses the existing pattern rather than inventing one**: `InvalidInputError` is the repo's
existing error type (`open_notebook/exceptions.py:19`), the router already imported it, and
`get_notebook` already had the `except OpenNotebookError: raise` arm that lets it through. No new
error class, no new status-code convention, no new import beyond the `RecordID` type hint.

Deliberately unchanged: `_stamp_notebook_view`, the counts query, the 404 branch, and every other
endpoint.

### Endpoint table

Measured in-process against `api.main:app` with `repo_query` mocked.

| Endpoint | Before | After |
|---|---|---|
| `GET /api/notebooks/abc123` | **500** + driver message | **400** `Invalid notebook id: 'abc123' (expected the format 'notebook:<id>')` |
| `GET /api/sources/abc123` | 400 `No class found for table abc123` | 400 (unchanged) |
| `GET /api/notes/abc123` | 400 `No class found for table abc123` | 400 (unchanged) |
| `GET /api/transformations/abc123` | 400 `No class found for table abc123` | 400 (unchanged) |

**One correction to the issue's table.** The issue also lists
`GET /api/episode-profiles/abc123` → 404. That endpoint is not a record-id lookup — it resolves a
profile *by name* (`get_episode_profile(profile_name)`), so the 404 is the live-database behaviour
for an unknown name. In this sandbox no SurrealDB is running, so the request fails at the query and
the router's catch-all returns `500 {"detail": "Failed to fetch episode profile"}`, with
`Errno 111 Connect call failed ('127.0.0.1', 8000)` in the log. I could not reproduce the 404 here,
so `episode-profiles` is **excluded from the new tests** rather than asserted against behaviour I
could not verify. It is out of scope for this fix either way — it never called `ensure_record_id`.

## 6. Verification

### 6.1 Tests added

`tests/test_notebook_id_validation.py` (10 cases), following the mocking style of
`tests/test_crud_404.py`:

| Test | Asserts |
|---|---|
| `test_get_notebook_bare_id_returns_400` | 400, and the driver message is **not** in the body |
| `test_get_notebook_malformed_id_never_touches_the_database` | 400 and `repo_query` never called — a rejected id costs no DB work |
| `test_get_notebook_malformed_id_returns_400[abc123 / notebook:a:b]` | both malformed shapes → 400 |
| `test_get_notebook_prefixed_id_still_works` | `notebook:abc123` → 200, counts intact, both queries carry the parsed id |
| `test_get_notebook_missing_record_still_returns_404` | parseable but unknown id still 404s |
| `test_bare_id_is_a_client_error_on_every_single_record_endpoint[4 paths]` | the cross-endpoint consistency the issue is actually about |

`TestClient` is built with `raise_server_exceptions=False` so an escaping exception surfaces as a 500
response instead of aborting the test.

### 6.2 Test run — after the fix (passing)

```
$ .venv/bin/python -m pytest tests/test_notebook_id_validation.py -v

tests/test_notebook_id_validation.py::test_get_notebook_bare_id_returns_400 PASSED [ 10%]
tests/test_notebook_id_validation.py::test_get_notebook_malformed_id_never_touches_the_database PASSED [ 20%]
tests/test_notebook_id_validation.py::test_get_notebook_malformed_id_returns_400[abc123] PASSED [ 30%]
tests/test_notebook_id_validation.py::test_get_notebook_malformed_id_returns_400[notebook:a:b] PASSED [ 40%]
tests/test_notebook_id_validation.py::test_get_notebook_prefixed_id_still_works PASSED [ 50%]
tests/test_notebook_id_validation.py::test_get_notebook_missing_record_still_returns_404 PASSED [ 60%]
tests/test_notebook_id_validation.py::test_bare_id_is_a_client_error_on_every_single_record_endpoint[/api/notebooks/abc123] PASSED [ 70%]
tests/test_notebook_id_validation.py::test_bare_id_is_a_client_error_on_every_single_record_endpoint[/api/sources/abc123] PASSED [ 80%]
tests/test_notebook_id_validation.py::test_bare_id_is_a_client_error_on_every_single_record_endpoint[/api/notes/abc123] PASSED [ 90%]
tests/test_notebook_id_validation.py::test_bare_id_is_a_client_error_on_every_single_record_endpoint[/api/transformations/abc123] PASSED [100%]

======================= 10 passed, 2 warnings in 13.26s ========================
```

### 6.3 Test run — before the fix (proof the tests catch the bug)

The router change was stashed to put the tree back in its buggy state, and the same file re-run:

```
$ git stash push api/routers/notebooks.py
$ .venv/bin/python -m pytest tests/test_notebook_id_validation.py -v

tests/test_notebook_id_validation.py::test_get_notebook_bare_id_returns_400 FAILED [ 10%]
tests/test_notebook_id_validation.py::test_get_notebook_malformed_id_never_touches_the_database FAILED [ 20%]
tests/test_notebook_id_validation.py::test_get_notebook_malformed_id_returns_400[abc123] FAILED [ 30%]
tests/test_notebook_id_validation.py::test_get_notebook_malformed_id_returns_400[notebook:a:b] FAILED [ 40%]
tests/test_notebook_id_validation.py::test_get_notebook_prefixed_id_still_works PASSED [ 50%]
tests/test_notebook_id_validation.py::test_get_notebook_missing_record_still_returns_404 PASSED [ 60%]
tests/test_notebook_id_validation.py::test_bare_id_is_a_client_error_on_every_single_record_endpoint[/api/notebooks/abc123] FAILED [ 70%]
tests/test_notebook_id_validation.py::test_bare_id_is_a_client_error_on_every_single_record_endpoint[/api/sources/abc123] PASSED [ 80%]
tests/test_notebook_id_validation.py::test_bare_id_is_a_client_error_on_every_single_record_endpoint[/api/notes/abc123] PASSED [ 90%]
tests/test_notebook_id_validation.py::test_bare_id_is_a_client_error_on_every_single_record_endpoint[/api/transformations/abc123] PASSED [100%]

=================================== FAILURES ===================================
____________________ test_get_notebook_bare_id_returns_400 _____________________

>       assert response.status_code == 400
E       assert 500 == 400
E        +  where 500 = <Response [500 Internal Server Error]>.status_code

tests/test_notebook_id_validation.py:46: AssertionError

=========================== short test summary info ============================
FAILED tests/test_notebook_id_validation.py::test_get_notebook_bare_id_returns_400
FAILED tests/test_notebook_id_validation.py::test_get_notebook_malformed_id_never_touches_the_database
FAILED tests/test_notebook_id_validation.py::test_get_notebook_malformed_id_returns_400[abc123]
FAILED tests/test_notebook_id_validation.py::test_get_notebook_malformed_id_returns_400[notebook:a:b]
FAILED tests/test_notebook_id_validation.py::test_bare_id_is_a_client_error_on_every_single_record_endpoint[/api/notebooks/abc123]
=================== 5 failed, 5 passed, 2 warnings in 9.29s ====================
```

The 5 failures are exactly the buggy cases; the 5 that still pass are the ones that must not
regress. The captured stderr shows the driver message reaching the 500 path:

```
2026-10-05 04:28:16.726 | ERROR | api.routers.notebooks:get_notebook:272 - Error fetching notebook abc123: invalid string provided for parse. the expected string format is "table_name:record_id"
```

The fix was restored with `git stash pop` and the full-file diff verified intact.

### 6.4 Regression suite

```
$ .venv/bin/python -m pytest tests/ -k notebook -q
94 passed, 903 deselected, 2 warnings in 12.27s
```

Also clean, since CI gates on it:

```
$ .venv/bin/python -m ruff format --check api/routers/notebooks.py tests/test_notebook_id_validation.py
2 files already formatted
$ .venv/bin/python -m ruff check api/routers/notebooks.py tests/test_notebook_id_validation.py
All checks passed!
```

### 6.5 Error-mapping chain reaches 400

The claim "`InvalidInputError` becomes a 400" is verified at three levels, not assumed:

```
$ .venv/bin/python /tmp/probe1452.py

1. global handler registered for InvalidInputError: True
   -> the handler answers status_code = 400
   -> body: {"detail":"PROBE"}
2. get_notebook converts it locally ('except InvalidInputError'): False
   get_notebook re-raises via 'except OpenNotebookError: raise': True
3. GET /api/notebooks/abc123 -> 400
   detail: Invalid notebook id: 'abc123' (expected the format 'notebook:<id>')
   detail is our InvalidInputError text: True
   leaks driver text: False
```

1. The handler at `api/main.py:308-315` is registered on the app and returns 400 when invoked
   directly.
2. `get_notebook` contains **no** local `except InvalidInputError` arm — so the 400 cannot be coming
   from the router. It re-raises via the pre-existing `except OpenNotebookError` arm, which pins the
   response to the global handler.
3. End-to-end through `TestClient`, the response is 400, the body is our `InvalidInputError` text, and
   the driver string is gone.

## 7. Commit

```
0a79a63  fix(notebooks): a malformed notebook id is a 400, not a 500 (#1452)
```

```
 CHANGELOG.md                         |   1 +
 api/routers/notebooks.py             |  25 ++++++-
 tests/test_notebook_id_validation.py | 125 +++++++++++++++++++++++++++++++++++
 3 files changed, 150 insertions(+), 1 deletion(-)
```

Conventional-commit subject in the repo's voice (`fix(scope): …`, issue number in parens), with a body
that states the cause, the existing convention it reuses, and `Closes #1452`. The one-line
`CHANGELOG.md` entry under `### Fixed` follows the convention that every fix commit in this repo
carries one.

`deliverable.md` is intentionally **not** committed — it is a work artifact, not part of the fix.

## 8. Pull request description

Paste-ready:

````markdown
## Summary

`GET /api/notebooks/{id}` returned **500** when the id was not a well-formed record id
(e.g. `/api/notebooks/abc123`), and the response body leaked the SurrealDB driver's
`invalid string provided for parse. the expected string format is "table_name:record_id"`.

Every other single-record endpoint already answered **400** for the same request. The
inconsistency is the bug.

## Root cause

`get_notebook` built its own `RecordID` and passed the raw path segment to
`ensure_record_id()`, which is a thin wrapper over `RecordID.parse()` and deliberately lets
the driver's `ValueError` escape. The router ends in a catch-all `except Exception` arm that
turns it into a 500 with `str(e)` in the detail.

The sibling endpoints never hit this because they do not build the `RecordID` themselves.
They go through `ObjectModel.get`, which validates the id first and raises `InvalidInputError`
when it cannot resolve a table (`open_notebook/domain/base.py:120`) — that becomes a 400.
The notebooks router skipped exactly that step.

## The fix

Parse the id through a new `_notebook_record_id()` helper that converts a parse failure into
the repo's existing `InvalidInputError`. The `except OpenNotebookError: raise` arm already
present in `get_notebook` lets it reach the global handler in `api/main.py`, which maps
`InvalidInputError` to 400.

No new error type, no new status-code convention — this reuses the pattern the rest of the
codebase already follows.

| Endpoint | Before | After |
|---|---|---|
| `GET /api/notebooks/abc123` | **500** + driver message | **400** |
| `GET /api/sources/abc123` | 400 | 400 (unchanged) |
| `GET /api/notes/abc123` | 400 | 400 (unchanged) |
| `GET /api/transformations/abc123` | 400 | 400 (unchanged) |

Well-formed ids still return 200, and an id that parses but names no record still returns
404 — the 400 only covers ids the database could never have had.

## Testing

`tests/test_notebook_id_validation.py` covers the 400, the absence of the driver text in the
body, that a rejected id never reaches the database, that well-formed ids and the 404 are
unaffected, and that the four single-record endpoints agree.

Verified to fail before the fix and pass after — with the router change stashed, 5 of the 10
cases fail with `assert 500 == 400`; with it applied, all 10 pass.

```
.venv/bin/python -m pytest tests/test_notebook_id_validation.py -v   # 10 passed
.venv/bin/python -m pytest tests/ -k notebook -q                      # 94 passed, 903 deselected
.venv/bin/python -m ruff format --check api/routers/notebooks.py tests/test_notebook_id_validation.py
```

## Notes

- Scope is limited to the notebook id validation. `_stamp_notebook_view`, the counts query and
  all other endpoints are untouched.
- Issue #1451 (duplicate podcast profile name returning 500, should be 409) is a separate
  problem with the same shape and is intentionally **not** addressed here.

Fixes #1452
````
