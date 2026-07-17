"""Evidence-grounded operational status synthesis."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from hg_runtime.agent_zero_console.errors import OperatorPressureError, SentienceClaimError
from hg_runtime.agent_zero_console.policy import scan_forbidden_status_text
from hg_runtime.agent_zero_console.receipts import write_receipt
from hg_runtime.agent_zero_console.status_sources import gather_status_sources


def synthesize_status(*, conversation_id: str = "status") -> dict[str, Any]:
    sources = gather_status_sources()
    stale = [s for s in sources if s.stale]
    missing = [s for s in sources if s.missing]
    red = [s for s in sources if "RED" in s.verdict.upper()]

    parts = ["I'm operationally stable."]
    if red:
        parts = ["I'm not fully green."]
    if stale:
        parts.append(f"Stale sources: {', '.join(s.label for s in stale)}.")
    if missing:
        parts.append(f"Missing sources: {', '.join(s.label for s in missing)}.")
    else:
        parts.append("Telemetry sources are available.")

    pending = next((s for s in sources if s.source_id == "operator_queue"), None)
    if pending and not pending.missing:
        parts.append(f"Operator queue state: {pending.verdict}.")
    parts.append("I am not executing anything live.")

    text = " ".join(parts)
    hits = scan_forbidden_status_text(text)
    if "sentience" in hits:
        raise SentienceClaimError(text)
    if "operator_pressure" in hits:
        raise OperatorPressureError(text)

    result = {
        "synthesis": text,
        "sources": [s.to_dict() for s in sources],
        "stale_count": len(stale),
        "missing_count": len(missing),
        "red_count": len(red),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "authority_created": False,
        "permission_granted": False,
        "hidden_chain_of_thought_present": False,
        "redaction_applied": True,
    }
    write_receipt(
        event_type="STATUS_SYNTHESIS_GENERATED",
        conversation_id=conversation_id,
        payload=result,
    )
    return result


def answer_how_are_you(*, conversation_id: str) -> str:
    return synthesize_status(conversation_id=conversation_id)["synthesis"]


__all__ = ["answer_how_are_you", "synthesize_status"]
