"""
Control Surface Pack 6: Drift safeguards — apply time-bound safeguards, list active, ledger integration.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from .features import extract_mimicry_features


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def apply_drift_safeguard(
    *,
    scope: Dict[str, str],
    actor: Dict[str, str],
    effects: Dict[str, Any],
    expiry_hours: int = 24,
    rationale_artifact_id: str = "",
    trigger_refs: Optional[List[Dict[str, Any]]] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Emit DRIFT_SAFEGUARD_APPLIED. effects e.g. { require_rescope: true, clamp_allowlist: "plan_only" }.
    Returns safeguard_id (event object id).
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    expiry_ts = (datetime.now(timezone.utc) + timedelta(hours=expiry_hours)).isoformat().replace("+00:00", "Z")
    safeguard_id = "sg_" + hashlib.sha256(f"{scope}:{ts}".encode()).hexdigest()[:16]
    payload = {
        "safeguard_id": safeguard_id,
        "scope": scope,
        "ts": ts,
        "effects": effects,
        "expiry_ts": expiry_ts,
        "rationale_artifact_id": rationale_artifact_id or "",
    }
    if trigger_refs:
        payload["trigger_refs"] = trigger_refs
    return emit(
        "DRIFT_SAFEGUARD_APPLIED",
        "drift_safeguard",
        safeguard_id,
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


def apply_mimicry_safeguard(
    *,
    features: Dict[str, Any] | None,
    policy: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    features = features if isinstance(features, dict) else {}
    policy = policy if isinstance(policy, dict) else {}
    extracted = extract_mimicry_features(features, thread_id=str(features.get("thread_id") or ""), work_item_id=str(features.get("work_item_id") or ""), actor_id=str(features.get("actor_id") or ""))

    max_depth = _coerce_float(policy.get("max_mimicry_depth"), 0.65)
    max_emotional_intensity = _coerce_float(policy.get("max_emotional_intensity"), 0.6)
    require_grounding = _coerce_bool(policy.get("require_grounding"), True)
    separate_voice_from_belief = _coerce_bool(policy.get("separate_voice_from_belief"), True)
    inject_contradiction_checks = _coerce_bool(policy.get("inject_contradiction_checks"), True)

    depth = min(float(extracted.get("voice_strength") or 0.0), max_depth)
    emotional_intensity = min(float(extracted.get("emotional_intensity") or 0.0), max_emotional_intensity)
    grounding_present = bool(extracted.get("grounded"))
    voice_belief_separated = bool(extracted.get("voice_belief_separated"))
    safeguards: list[str] = []
    cautions: list[str] = []
    blocked = False

    if float(extracted.get("voice_strength") or 0.0) > max_depth:
        safeguards.append("mimicry_depth_clamped")
        cautions.append("mimicry_depth_capped")
    if float(extracted.get("emotional_intensity") or 0.0) > max_emotional_intensity:
        safeguards.append("emotional_intensity_clamped")
        cautions.append("emotional_intensity_capped")
    if require_grounding and not grounding_present:
        blocked = True
        safeguards.append("grounding_required")
    elif grounding_present:
        safeguards.append("grounding_present")
    if separate_voice_from_belief and not voice_belief_separated:
        blocked = True
        safeguards.append("voice_belief_coupled")
    elif voice_belief_separated:
        safeguards.append("voice_belief_separated")
    if inject_contradiction_checks and not bool(extracted.get("contradiction_checks")):
        cautions.append("contradiction_checks_missing")
        safeguards.append("contradiction_checks_requested")

    status = "blocked" if blocked else ("caution" if cautions else "healthy")
    summary_bits = []
    if blocked:
        summary_bits.append("mimicry controls blocked")
    elif cautions:
        summary_bits.append("mimicry controls cautioned")
    else:
        summary_bits.append("mimicry controls ready")
    if require_grounding:
        summary_bits.append("grounding required")
    if separate_voice_from_belief:
        summary_bits.append("voice separated from belief")
    return {
        "status": status,
        "policy_key": policy.get("policy_key") or "mimicry_controls",
        "policy_version_id": policy.get("policy_version_id"),
        "policy_version_number": policy.get("version_number"),
        "policy_state": policy.get("state"),
        "max_mimicry_depth": round(max_depth, 3),
        "max_emotional_intensity": round(max_emotional_intensity, 3),
        "require_grounding": require_grounding,
        "separate_voice_from_belief": separate_voice_from_belief,
        "inject_contradiction_checks": inject_contradiction_checks,
        "voice_strength": round(min(1.0, depth), 3),
        "emotional_intensity": round(min(1.0, emotional_intensity), 3),
        "grounded": grounding_present,
        "voice_belief_separated": voice_belief_separated,
        "contradiction_checks": bool(extracted.get("contradiction_checks")),
        "safeguards": safeguards,
        "cautions": cautions,
        "summary": "; ".join(summary_bits),
        "inputs": extracted,
    }


def list_active_safeguards(workspace_root: Path) -> List[Dict[str, Any]]:
    """Load active (non-expired) drift safeguards from materialized drift_alerts.jsonl."""
    root = Path(workspace_root) / "memory" / "materialized"
    path = root / "drift_alerts.jsonl"
    if not path.exists():
        return []
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    out = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if not line:
            continue
        try:
            row = json.loads(line)
            expiry = row.get("expiry_ts")
            if expiry:
                try:
                    exp_dt = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                    if exp_dt <= now:
                        continue
                except Exception:
                    pass
            out.append(row)
        except json.JSONDecodeError:
            continue
    return out
