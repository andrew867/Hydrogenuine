"""OEA Phase 1 stub executor — accepts UEAK commits only."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from hg_runtime.contract import Event, draft, stable_id


class OEAStubExecutor:
    """Records stub effect evidence for UEAK-committed actions only."""

    handler_id = "oea.phase1.stub_executor"

    def __init__(self) -> None:
        self.effect_records: List[Dict[str, Any]] = []

    @property
    def audit_records(self) -> List[Dict[str, Any]]:
        return self.effect_records

    def dispatch_committed(
        self, committed_events: Sequence[Event]
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for committed in committed_events:
            if committed["type"] != "UEAK_EXECUTION_COMMITTED":
                continue
            payload = committed.get("payload", {})
            commit_ref = str(payload["commit_ref"])
            request_id = str(payload["request_id"])
            effect_class = str(payload.get("effect_class", "unknown"))
            action = dict(payload.get("action", {}))
            record = {
                "commit_ref": commit_ref,
                "request_id": request_id,
                "effect_class": effect_class,
                "action_type": action.get("action_type"),
                "status": "stub_logged",
            }
            self.effect_records.append(record)
            results.append(
                draft(
                    "OEA_EFFECT_STUB_RECORDED",
                    record,
                    causal_parents=[committed["event_id"]],
                )
            )
            receipt_id = stable_id("receipt", commit_ref)
            results.append(
                draft(
                    "EFFECT_RECEIPTED",
                    {
                        "receipt_id": receipt_id,
                        "commit_ref": commit_ref,
                        "request_id": request_id,
                        "effect_class": effect_class,
                        "status": "stub_logged",
                        "action_type": action.get("action_type"),
                        "executor_mode": "stub",
                    },
                    causal_parents=[committed["event_id"]],
                )
            )
        return results


__all__ = ["OEAStubExecutor"]
