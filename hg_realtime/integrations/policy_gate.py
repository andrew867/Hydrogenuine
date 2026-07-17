from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any, Dict

@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str = ""

class PolicyGate:
    def allow_run(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        workflow_id: str,
        resolved_inputs: Dict[str, Any],
        correlation_id: str,
    ) -> PolicyDecision:
        try:
            from hg_core.gate.service import release_gate_enforced
        except Exception:
            release_gate_enforced = lambda: (  # type: ignore[misc, assignment]
                (os.environ.get("HG_RELEASE_GATE_ENFORCED") or "1").strip().lower()
                not in {"0", "false", "off", "no"}
            )
        if release_gate_enforced():
            try:
                from hg_core.gate import enforce_release_gate

                result = enforce_release_gate(workflow_family=workflow_id, target_kind="workflow", target_id=workflow_id)
                if not result.get("ok"):
                    return PolicyDecision(False, str(result.get("reason") or "blocked by release gate"))
            except Exception as exc:
                return PolicyDecision(False, f"release gate error: {exc}")
        return PolicyDecision(True, "")
