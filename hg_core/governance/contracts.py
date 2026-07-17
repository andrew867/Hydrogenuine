"""
Governance contracts: who can approve what, delegation bounds, response times, escalation routes.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from hg_core.policy_registry import get_policy_version, list_policy_registry
from hg_core.drift.safeguards import apply_mimicry_safeguard

MIMICRY_POLICY_KEY = "mimicry_controls"


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def publish_governance_contract(
    *,
    contract: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    contract_id: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Write contract artifact (approvers, delegation_bounds, response_times, escalation_routes, stake_requirements), emit GOVERNANCE_CONTRACT_PUBLISHED.
    Returns contract_id.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    cid = contract_id or "gc_" + hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()[:16]
    path = workspace_root / "artifacts" / "governance" / "contracts" / f"{cid}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({**contract, "contract_id": cid, "ts": ts}, indent=2, ensure_ascii=False), encoding="utf-8")
    emit(
        "GOVERNANCE_CONTRACT_PUBLISHED",
        "governance_contract",
        cid,
        {"contract_id": cid, "ts": ts, "contract_artifact_id": str(path)},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return cid


def record_approval_policy_applied(
    *,
    contract_id: str,
    decision_id: Optional[str] = None,
    action_id: Optional[str] = None,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit APPROVAL_POLICY_APPLIED (which contract governed a decision/action). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload = {"contract_id": contract_id, "ts": ts}
    if decision_id:
        payload["decision_id"] = decision_id
    if action_id:
        payload["action_id"] = action_id
    obj_id = f"apa_{contract_id}_{ts.replace(':', '').replace('-', '')[:12]}"
    return emit(
        "APPROVAL_POLICY_APPLIED",
        "approval_policy",
        obj_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def create_delegation_contract(
    *,
    from_agent_id: str,
    to_agent_id: str,
    work_item_ref: Optional[str] = None,
    constraints: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit DELEGATION_CONTRACT_CREATED (handoff with constraints). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    dc_id = "dc_" + hashlib.sha256(f"{from_agent_id}:{to_agent_id}:{ts}".encode()).hexdigest()[:16]
    payload = {"delegation_contract_id": dc_id, "from_agent_id": from_agent_id, "to_agent_id": to_agent_id, "ts": ts, "constraints": constraints}
    if work_item_ref:
        payload["work_item_ref"] = work_item_ref
    return emit(
        "DELEGATION_CONTRACT_CREATED",
        "delegation_contract",
        dc_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def record_escalation_route_taken(
    *,
    escalation_id: Optional[str] = None,
    paged_agent_ids: List[str],
    reason: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    incident_id: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit ESCALATION_ROUTE_TAKEN (who was paged, why). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    eid = escalation_id or "escal_" + hashlib.sha256(f"{paged_agent_ids}:{ts}".encode()).hexdigest()[:16]
    payload = {"escalation_id": eid, "paged_agent_ids": paged_agent_ids, "reason": reason, "ts": ts}
    if incident_id:
        payload["incident_id"] = incident_id
    return emit(
        "ESCALATION_ROUTE_TAKEN",
        "escalation",
        eid,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def _coerce_float(value: Any, default: float, *, minimum: float = 0.0, maximum: float = 1.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = default
    return max(minimum, min(maximum, numeric))


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if not text:
        return default
    return text in {"1", "true", "yes", "on", "y", "grounded", "separated", "required", "active"}


def _normalize_mimicry_content(content: dict[str, Any] | None) -> dict[str, Any]:
    content = content if isinstance(content, dict) else {}
    return {
        "max_mimicry_depth": _coerce_float(content.get("max_mimicry_depth"), 0.65),
        "max_emotional_intensity": _coerce_float(content.get("max_emotional_intensity"), 0.6),
        "require_grounding": _coerce_bool(content.get("require_grounding"), True),
        "separate_voice_from_belief": _coerce_bool(content.get("separate_voice_from_belief"), True),
        "inject_contradiction_checks": _coerce_bool(content.get("inject_contradiction_checks"), True),
        "voice_directives": [str(item).strip() for item in (content.get("voice_directives") or []) if str(item).strip()],
        "belief_directives": [str(item).strip() for item in (content.get("belief_directives") or []) if str(item).strip()],
    }


def build_mimicry_policy_summary(policy_key: str = MIMICRY_POLICY_KEY) -> dict[str, Any]:
    rows = list_policy_registry()
    policy_row = next((row for row in rows if str(row.get("policy_key") or "").strip() == policy_key), None)
    if not policy_row:
        return {
            "status": "missing",
            "policy_key": policy_key,
            "policy_version_id": None,
            "policy_version_number": None,
            "policy_title": None,
            "policy_category": None,
            "policy_state": None,
            "summary": "no mimicry policy configured",
            "limits": _normalize_mimicry_content({}),
            "safeguard_summary": {
                "status": "missing",
                "summary": "mimicry controls unavailable",
                "safeguards": [],
                "cautions": [],
            },
            "voice_belief_separated": True,
            "grounding_required": True,
            "contradiction_checks_required": True,
        }
    current_version_id = str(policy_row.get("current_version_id") or "").strip() or None
    version = get_policy_version(current_version_id) if current_version_id else None
    content = {}
    if isinstance(version, dict):
        try:
            content = json.loads(str(version.get("content_json") or "{}"))
        except Exception:
            content = {}
    limits = _normalize_mimicry_content(content)
    safeguard_summary = apply_mimicry_safeguard(
        features={
            "thread_id": policy_key,
            "work_item_id": policy_key,
            "actor_id": "governance",
            "voice_strength": limits["max_mimicry_depth"],
            "emotional_intensity": limits["max_emotional_intensity"],
            "grounded": limits["require_grounding"],
            "voice_belief_separated": limits["separate_voice_from_belief"],
            "contradiction_checks": limits["inject_contradiction_checks"],
        },
        policy={
            "policy_key": policy_key,
            "max_mimicry_depth": limits["max_mimicry_depth"],
            "max_emotional_intensity": limits["max_emotional_intensity"],
            "require_grounding": limits["require_grounding"],
            "separate_voice_from_belief": limits["separate_voice_from_belief"],
            "inject_contradiction_checks": limits["inject_contradiction_checks"],
        },
    )
    state = str(policy_row.get("state") or "").strip().lower()
    status = "ready" if current_version_id and state == "active" else ("caution" if current_version_id else "missing")
    if safeguard_summary.get("status") == "blocked":
        status = "blocked"
    summary_parts = [
        f"max depth {limits['max_mimicry_depth']:.2f}",
        f"max emotion {limits['max_emotional_intensity']:.2f}",
    ]
    if limits["require_grounding"]:
        summary_parts.append("grounding required")
    if limits["separate_voice_from_belief"]:
        summary_parts.append("voice separated from belief")
    if limits["inject_contradiction_checks"]:
        summary_parts.append("contradiction checks enabled")
    return {
        "status": status,
        "policy_key": policy_key,
        "policy_version_id": current_version_id,
        "policy_version_number": policy_row.get("version_number"),
        "policy_title": policy_row.get("title"),
        "policy_category": policy_row.get("category"),
        "policy_state": policy_row.get("state"),
        "change_summary": policy_row.get("change_summary"),
        "limits": limits,
        "voice_belief_separated": bool(limits["separate_voice_from_belief"]),
        "grounding_required": bool(limits["require_grounding"]),
        "contradiction_checks_required": bool(limits["inject_contradiction_checks"]),
        "safeguard_summary": safeguard_summary,
        "summary": "; ".join(summary_parts),
    }


def load_contract(workspace_root: Path, contract_id: str) -> Optional[Dict[str, Any]]:
    """Load governance contract artifact by contract_id."""
    path = workspace_root / "artifacts" / "governance" / "contracts" / f"{contract_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
