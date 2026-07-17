"""hg_workbench — governed Agent Zero Workbench foundation.

The Workbench is a GOVERNANCE ENVELOPE, not an autonomous agent. It records the
product spine as tamper-evident chained receipts:

    user request -> authenticated operator session -> governed workflow run ->
    artifacts/uploads -> model/subagent/persona progress lanes -> steering
    messages -> receipts

Doctrine (enforced, not just documented):
- Every run is created by a verified Keycloak operator (subject UUID is the key);
  the library never sees or stores a raw token — only a sha256 session hash.
- Every run is isolated by `run_id` (INV-RUN-ISO): artifacts, events, and receipts
  carry their run_id; cross-run access is blocked by default (no promotion here).
- Progress/model/subagent/persona events are OBSERVATION, never authority
  (`authority=False`); only governed receipts + verified operator decisions
  authorize anything.
- `external_effects_enabled` is always False; embodied/external actions are
  blocked placeholders. This foundation performs no external effects.
- Settings/persona/temperature/model-route changes are governed config changes:
  high/restricted changes are HELD pending step-up, never silently applied.

This is a local foundation. It is not a production deployment and makes no
production-auth or autonomy claim; the proof records the path, not correctness.
"""
from hg_workbench.models import (
    WorkbenchArtifact, WorkbenchProgressEvent, WorkbenchRun,
    WorkbenchSettingChange, WorkbenchSteeringMessage, WorkbenchSubagentLane,
    PROGRESS_EVENT_TYPES,
)
from hg_workbench.receipts import (
    ArtifactReceipt, ProgressEventReceipt, SettingChangeReceipt,
    SteeringReceipt, WorkbenchReceiptError, WorkbenchRunReceipt,
    verify_run_chain,
)
from hg_workbench.run_store import (
    WorkbenchRunStore, WorkbenchError, RunIsolationError,
)

__all__ = [
    "ArtifactReceipt", "PROGRESS_EVENT_TYPES", "ProgressEventReceipt",
    "RunIsolationError", "SettingChangeReceipt", "SteeringReceipt",
    "WorkbenchArtifact", "WorkbenchError", "WorkbenchProgressEvent",
    "WorkbenchReceiptError", "WorkbenchRun", "WorkbenchRunReceipt",
    "WorkbenchRunStore", "WorkbenchSettingChange", "WorkbenchSteeringMessage",
    "WorkbenchSubagentLane", "verify_run_chain",
]
