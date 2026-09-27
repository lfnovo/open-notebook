# ADR-016: Explicitly skip an unavailable parallel research contribution

- **Status**: Accepted
- **Date**: 2026-09-24

## Context

A provider can exhaust an account quota while other providers have completed useful reports. Repeated attempts cannot replenish that quota. Cancelling one stage previously kept every dependent stage blocked, leaving no explicit way to continue with reduced evidence.

## Decision

Add a user-confirmed `skipped` state for a settled parallel contribution with no report. Require at least one completed peer report. Never skip the combined brief or final decision. Reject changes after a dependent input has been frozen or submitted. A running request must be stopped and its cancellation confirmed first.

Keep the stage and its audit record, with no fabricated report. Include `skipped_stages` in subsequent evidence packets and instruct every later output to disclose the absent contribution. Preserve all existing report bytes and digests. Skipped stages satisfy dependency barriers but do not count as reports or corroboration. They cannot be restored or overwritten within the same run.

The UI distinguishes Skip from Pause, Stop and End. An impact review, risk acknowledgement and final confirmation precede the mutation. Quota exhaustion is excluded from transient retry scheduling. Provider-reported reset times are preserved by the account bridge across restarts.

## Alternatives considered

- Automatic provider omission: rejected because it changes the evidence scope without consent.
- Marking an empty report completed: rejected because it fabricates successful research.
- Reducing the model or bypassing account limits: rejected because it changes the requested service and does not fix quota handling.

## Consequences

Research can continue with explicitly reduced provider coverage. Missing evidence remains visible in machine packets, human reports and exports. This preserves existing data; it does not prove that fewer independent investigations provide equivalent coverage. Additional policy and UX work is tracked in [the development plan](../research-availability-plan.md).
