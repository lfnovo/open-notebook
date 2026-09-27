# Research controls and confirmation boundaries

The research module offers four explicit lifecycle operations without deleting reports:

- `pause`: finish in-flight work, stop scheduling later stages/retries.
- `stop`: persist scheduling halt, cancel owned account requests, stop browser monitoring. Resume unfinished stages later.
- `cancel`: same cancellation, then end the workflow. Only explicit `restore` can restart it.
- `resume` / `restore`: preserve completed report hashes, retry unfinished account stages from their saved immutable input, reconcile browser submission journals.

Stopping is asynchronous: `stopping` → `stopped` / `cancelled` or `stop_failed`. Resume and per-stage retry are rejected until stop is confirmed. Cancellation failure leaves the workflow paused, with an actionable error. A result completed during cancellation remains saved. Automatic retries cannot restart ended or stopped workflows. State survives research-service restarts.

Account calls have a unique per-attempt request ID. An authenticated bridge endpoint cancels only that request's queued entry and owned process group, including its children. Cancel-before-submit tombstones prevent a late HTTP request from launching. Durable request markers prevent replay after bridge restart; a potentially orphaned process is reported as unconfirmed, never claimed as stopped. No account tokens or research content are stored in these markers. Legacy untracked calls cannot be killed by this endpoint; wait for completion before upgrading.

Web provider computation is remote. Cancelling local orchestration does **not** prove remote cancellation or recover quota. A browser command already delivered can finish. The existing journal remains intact and is reconciled on resume; uncertain submissions must not be blindly repeated. No provider DOM stop-button guessing was added.

The UI requires two explicit confirmations for lifecycle changes and manual retries. Review cards show effects, affected stages, retained report count, account restart cost and browser reconnection limitations. The final step requires a separate explicit click; cancelling, Escape or backing out performs no mutation. Changed stage state invalidates previously accepted risk. Pending requests lock submission against double clicks. Export and opening saved notebooks remain immediate, read-only actions.

Validation uses synthetic providers for workflow races, real local subprocess trees for bridge cancellation and DOM-based UI interaction tests. No paid provider research is created for testing.
