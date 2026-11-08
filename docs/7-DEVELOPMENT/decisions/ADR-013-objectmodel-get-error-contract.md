# ADR-013: ObjectModel.get raises NotFoundError only for a missing record

- **Status**: Accepted
- **Date**: 2026-10
- **Related**: #1363, PR #1364

## Context

`ObjectModel.get()` is the shared fetch boundary for every domain model. It wrapped **every** exception from `repo_query` as `NotFoundError("Object with id ... not found - {e}")`, including connection errors and the `RuntimeError` that `repo_query` re-raises for retriable SurrealDB v2 transaction conflicts. Callers treat `NotFoundError` as permanent: routers map it to 404, and since #1363 the background commands treat it as a non-retryable job failure. Under the old wrapping, a transient database hiccup would have been reported as "not found" and never retried.

## Decision

**`ObjectModel.get()` raises `NotFoundError` only when the record does not exist.** `InvalidInputError` (empty id, unknown table) passes through unchanged. Any other failure is raised as `DatabaseOperationError`, chained to the original exception.

Consequences for callers:

- **Commands:** `NotFoundError` means "the record was deleted" and is permanent. `process_source` and `run_transformation` have it in `stop_on`. `DatabaseOperationError` stays retryable.
- **API:** a missing record is still 404. A database failure during a fetch becomes a 500 (`OpenNotebookError` handler) instead of a misleading 404.

## Alternatives considered

- **Keep the wrapping and catch `NotFoundError` per command**: rejected, because it makes every transient conflict permanent, exactly the failure the worker's retries exist for.
- **Match the error message to tell the two apart**: rejected as fragile string coupling.
- **Return `None` for a missing record**: rejected. It's a larger API change, and the `if not x` guards would have to come back everywhere.

## Consequences

- A command can safely treat `NotFoundError` as permanent (deleted before or during processing) without starving the queue on DB conflicts.
- API clients see 500, not 404, for database outages on single-record fetches. That's correct, but it's visible if a client relied on the old 404.
- New fetch helpers should follow the same split: "missing" vs "failed".
