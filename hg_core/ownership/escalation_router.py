"""Escalation: choose primary or fallback approver from availability."""
from __future__ import annotations
from typing import Any, Dict

from .availability_registry import AvailabilityRegistry


def choose_approver(
    approver_spec: Dict[str, Any],
    escalation_spec: Dict[str, Any],
    avail: AvailabilityRegistry,
) -> Dict[str, Any]:
    """
    Return first available approver: primary from approver_spec, else first in escalation_spec.chain.
    Returns {"ok": True, "approver": {...}, "route": "primary"|"fallback"} or
            {"ok": False, "error": "NO_AVAILABLE_APPROVER", "approver": {"kind": "policy", "value": "default_fail_closed"}}.
    """
    if approver_spec.get("kind") == "principal":
        pid = approver_spec.get("value")
        if pid and avail.is_available(pid):
            return {"ok": True, "approver": {"kind": "principal", "value": pid}, "route": "primary"}

    for step in escalation_spec.get("chain") or []:
        if step.get("kind") == "principal" and avail.is_available(step.get("value")):
            return {"ok": True, "approver": step, "route": "fallback"}

    return {
        "ok": False,
        "error": "NO_AVAILABLE_APPROVER",
        "approver": {"kind": "policy", "value": "default_fail_closed"},
    }
