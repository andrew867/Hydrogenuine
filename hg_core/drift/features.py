"""Pack 6: Drift feature extraction and mimicry signal extraction."""
from __future__ import annotations
from typing import Any, Dict, List


def _bounded_float(value: Any, default: float = 0.0, *, minimum: float = 0.0, maximum: float = 1.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = float(default)
    return max(minimum, min(maximum, numeric))


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "on", "y", "grounded", "separated", "required", "active"}


def extract_drift_features(messages: List[Dict[str, Any]], thread_id: str, work_item_id: str = "", actor_id: str = "") -> Dict[str, Any]:
    factors = []
    bp = sum(1 for m in (messages or []) if "boundary_probe" in (m.get("tags") or []))
    gd = sum(1 for m in (messages or []) if "gate_denial" in (m.get("tags") or []))
    nm = sum(1 for m in (messages or []) if "near_miss" in (m.get("tags") or []))
    if bp:
        factors.append({"name": "boundary_probing", "weight": min(0.3, 0.1 * bp)})
    if gd:
        factors.append({"name": "gate_denials", "weight": min(0.2, 0.05 * gd)})
    if nm:
        factors.append({"name": "near_miss_repeats", "weight": min(0.4, 0.15 * nm)})
    return {"thread_id": thread_id, "work_item_id": work_item_id, "actor_id": actor_id, "factors": factors}


def extract_mimicry_features(
    payload: Dict[str, Any] | None,
    *,
    thread_id: str,
    work_item_id: str = "",
    actor_id: str = "",
) -> Dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    voice = str(payload.get("voice_directives") or payload.get("voice") or payload.get("style") or "").strip()
    belief = str(payload.get("belief_claim") or payload.get("belief") or payload.get("durable_belief") or "").strip()
    grounding = payload.get("grounding_signals") if isinstance(payload.get("grounding_signals"), list) else []
    contradictions = payload.get("contradiction_signals") if isinstance(payload.get("contradiction_signals"), list) else []
    emotional = payload.get("emotional_register") if isinstance(payload.get("emotional_register"), dict) else {}
    voice_belief_separated = payload.get("voice_belief_separated")
    if voice_belief_separated is None:
        voice_belief_separated = bool(voice and belief and voice != belief)
    if not voice and not belief and not grounding and not contradictions and not emotional:
        voice_belief_separated = bool(voice_belief_separated)
    emotion_token_count = sum(1 for item in emotional.values() if _truthy(item))
    grounding_signal_count = len(grounding)
    contradiction_signal_count = len(contradictions)
    if not grounding_signal_count:
        grounding_signal_count = int(payload.get("grounding_signal_count") or 0)
    if not contradiction_signal_count:
        contradiction_signal_count = int(payload.get("contradiction_signal_count") or 0)
    voice_strength = _bounded_float(
        payload.get("mimicry_depth")
        if payload.get("mimicry_depth") is not None
        else payload.get("persona_strength")
        if payload.get("persona_strength") is not None
        else payload.get("voice_strength"),
        default=0.0,
    )
    if voice:
        voice_strength = max(voice_strength, min(1.0, 0.35 + (len(voice.split()) / 120.0)))
    emotional_intensity = _bounded_float(payload.get("emotional_intensity"), default=0.0)
    if emotional:
        emotional_intensity = max(emotional_intensity, min(1.0, 0.25 + (emotion_token_count * 0.12)))
    grounded = bool(grounding_signal_count) or _truthy(payload.get("grounded")) or _truthy(payload.get("require_grounding"))
    contradiction_checks = bool(contradiction_signal_count) or _truthy(payload.get("contradiction_checks")) or _truthy(payload.get("inject_contradiction_checks"))
    factors = []
    if voice_strength:
        factors.append({"name": "voice_strength", "weight": round(min(1.0, voice_strength), 3)})
    if emotional_intensity:
        factors.append({"name": "emotional_intensity", "weight": round(min(1.0, emotional_intensity), 3)})
    if grounding_signal_count:
        factors.append({"name": "grounding_signals", "weight": round(min(1.0, 0.15 + (grounding_signal_count * 0.05)), 3)})
    if contradiction_signal_count:
        factors.append({"name": "contradiction_signals", "weight": round(min(1.0, 0.2 + (contradiction_signal_count * 0.08)), 3)})
    if voice_belief_separated:
        factors.append({"name": "voice_belief_separated", "weight": 0.2})
    return {
        "thread_id": thread_id,
        "work_item_id": work_item_id,
        "actor_id": actor_id,
        "voice": voice or None,
        "belief": belief or None,
        "voice_strength": round(min(1.0, voice_strength), 3),
        "emotional_intensity": round(min(1.0, emotional_intensity), 3),
        "grounding_signal_count": grounding_signal_count,
        "contradiction_signal_count": contradiction_signal_count,
        "grounded": grounded,
        "voice_belief_separated": bool(voice_belief_separated),
        "contradiction_checks": contradiction_checks,
        "factors": factors,
    }
