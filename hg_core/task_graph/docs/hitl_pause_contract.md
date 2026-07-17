# HITL Pause Contract

New knobs:
- run_policy.pause_at_checkpoint: bool
- optional: checkpoints.pause_before, checkpoints.pause_after

Behavior:
- At a pausing checkpoint, call overseer checkpoint, persist state, return:
  { ok:true, status:"paused", run_id, checkpoint:{node_id, position}, summary }
- Resume loads state and continues.
