# Independent stage controls

The run toolbar controls the whole research; the selected stage has a separate
pause, stop, end, resume/restore and retry card. A failed stage can retry while its
sibling continues. A stage hold persists across restart; whole-run resume does
not remove it. Ending a stage preserves inputs and blocks dependent stages until
that stage is explicitly restored and completed.

Actions use a two-step impact/risk dialog and a server-checked snapshot of the
selected stage plus whole-run pause/control state. Sibling progress does not
invalidate confirmation; changes to the target do. The actions endpoint requires
this snapshot. Completed reports are immutable. Web controls stop local monitoring;
remote research may continue. Resume reuses the submission journal and conversation;
uncertain submissions are never blindly resent. Account cancellation targets the
exact request id; an unconfirmed stop blocks resume. Unfinished account work may
restart and consume quota, explained before confirmation. Manual report import
clears a settled pause; it cannot bypass a cancelled or unconfirmed-stop state.

Run service tests with `PYTHONPATH=modules/multi-model-research/service python -m
pytest modules/multi-model-research/service/tests`. Frontend tests run in an isolated
tree prepared by `scripts/prepare_modules.py`, never overlaid onto the source tree.
