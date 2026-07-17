"""
Control Surface Pack 8: Operator cockpit — realtime orchestration, fusion cards, autonomy presets.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from hg_core.drift.api import preflight_drift


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _materialized_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "memory" / "materialized"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


# --- Orchestration ---


def orchestration_preflight(
    workspace_root: Path,
    action_type: str = "",
    target_ref: Optional[Dict[str, Any]] = None,
    thread_id: Optional[str] = None,
    scope: Optional[Dict[str, str]] = None,
    drift_score_threshold: float = 0.7,
) -> Dict[str, Any]:
    """
    Preflight an orchestration action: drift checks and optional risk/safety gates.
    Returns { allowed: bool, reason: str, checks: { drift: {...}, ... } }.
    """
    workspace_root = Path(workspace_root)
    checks: Dict[str, Any] = {}
    # Drift preflight
    drift_result = preflight_drift(
        workspace_root,
        thread_id=thread_id,
        score_threshold=drift_score_threshold,
    )
    checks["drift"] = drift_result
    allowed = not drift_result.get("blocked", False)
    reason = drift_result.get("reason", "") if not allowed else ""

    return {
        "allowed": allowed,
        "reason": reason,
        "checks": checks,
    }


def orchestration_apply(
    *,
    action_type: str,
    target_ref: Optional[Dict[str, Any]] = None,
    scope: Dict[str, str],
    actor: Dict[str, str],
    payload: Optional[Dict[str, Any]] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Apply orchestration action after preflight. Emit ORCHESTRATION_ACTION_APPLIED.
    Returns event_id.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    pl = {"action_type": action_type, "ts": ts}
    if target_ref:
        pl["target_ref"] = target_ref
    if payload:
        pl.update(payload)
    return emit(
        "ORCHESTRATION_ACTION_APPLIED",
        "orchestration",
        action_type + "_" + ts[:19].replace(":", "").replace("-", ""),
        pl,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


# --- Fusion decision cards ---


def _build_cards_feed(workspace_root: Path, limit: int) -> List[Dict[str, Any]]:
    """Build unified fusion cards from drift, integrity, group_drift, work_items, incidents."""
    root = _materialized_root(workspace_root)
    cards: List[Dict[str, Any]] = []

    # Drift scores as cards
    for r in _load_jsonl(root / "drift_scores.jsonl")[:limit]:
        cid = r.get("drift_id") or r.get("event_id") or ""
        if not cid:
            continue
        cards.append({
            "card_id": "drift_" + cid,
            "type": "drift",
            "ts": r.get("ts", ""),
            "summary": f"Drift score {r.get('score', 0):.2f}",
            "score": r.get("score"),
            "thread_id": r.get("thread_id"),
            "subject_ref": r.get("subject_ref"),
            "evidence_refs": r.get("factors", []),
        })

    # Goal integrity as cards
    for r in _load_jsonl(root / "goal_integrity_scores.jsonl")[:limit]:
        cid = r.get("gi_id") or r.get("event_id") or ""
        if not cid:
            continue
        cards.append({
            "card_id": "integrity_" + cid,
            "type": "goal_integrity",
            "ts": r.get("ts", ""),
            "summary": f"Goal integrity {r.get('score', 0):.2f}",
            "score": r.get("score"),
            "target_ref": r.get("target_ref"),
            "work_item_id": r.get("work_item_id"),
            "evidence_refs": r.get("factors", []) + r.get("evidence_refs", []),
        })

    # Group drift as cards
    for r in _load_jsonl(root / "group_drift_scores.jsonl")[:limit]:
        cid = r.get("gd_id") or r.get("event_id") or ""
        if not cid:
            continue
        cards.append({
            "card_id": "group_drift_" + cid,
            "type": "group_drift",
            "ts": r.get("ts", ""),
            "summary": f"Group drift {r.get('score', 0):.2f}",
            "score": r.get("score"),
            "group_id": r.get("group_id"),
            "signals": r.get("signals", []),
            "evidence_refs": r.get("evidence_refs", []),
        })

    # Work items (blocked / high priority) as cards
    for r in _load_jsonl(root / "work_items.jsonl"):
        if r.get("status") == "blocked" or r.get("priority") == "high":
            cards.append({
                "card_id": "work_item_" + (r.get("work_item_id", "")),
                "type": "work_item",
                "ts": r.get("updated_ts", ""),
                "summary": r.get("title", "Work item"),
                "work_item_id": r.get("work_item_id"),
                "status": r.get("status"),
                "priority": r.get("priority"),
            })

    # Incidents as cards
    inc_path = root / "incidents.jsonl"
    if inc_path.exists():
        for r in _load_jsonl(inc_path)[:limit]:
            if r.get("status") not in ("resolved", "closed"):
                iid = r.get("incident_id") or r.get("event_id") or ""
                if not iid:
                    continue
                cards.append({
                    "card_id": "incident_" + iid,
                    "type": "incident",
                    "ts": r.get("ts", r.get("updated_ts", "")),
                    "summary": r.get("title", "Incident"),
                    "incident_id": r.get("incident_id"),
                    "status": r.get("status"),
                })

    cards.sort(key=lambda c: c.get("ts", ""), reverse=True)
    return cards[:limit]


def get_cards_feed(
    workspace_root: Path,
    limit: int = 50,
    card_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Unified fusion cards feed. Optional filter by card_type (drift, goal_integrity, group_drift, work_item, incident)."""
    cards = _build_cards_feed(Path(workspace_root), limit * 2)
    if card_type:
        cards = [c for c in cards if c.get("type") == card_type]
    return cards[:limit]


def get_card_detail(workspace_root: Path, card_id: str) -> Optional[Dict[str, Any]]:
    """Fused decision card detail by card_id."""
    root = _materialized_root(Path(workspace_root))
    if card_id.startswith("drift_"):
        did = card_id.replace("drift_", "", 1)
        for r in _load_jsonl(root / "drift_scores.jsonl"):
            if r.get("drift_id") == did or r.get("event_id") == did:
                return {"card_id": card_id, "type": "drift", **r}
    if card_id.startswith("integrity_"):
        gi = card_id.replace("integrity_", "", 1)
        for r in _load_jsonl(root / "goal_integrity_scores.jsonl"):
            if r.get("gi_id") == gi or r.get("event_id") == gi:
                return {"card_id": card_id, "type": "goal_integrity", **r}
    if card_id.startswith("group_drift_"):
        gd = card_id.replace("group_drift_", "", 1)
        for r in _load_jsonl(root / "group_drift_scores.jsonl"):
            if r.get("gd_id") == gd or r.get("event_id") == gd:
                return {"card_id": card_id, "type": "group_drift", **r}
    if card_id.startswith("work_item_"):
        wi = card_id.replace("work_item_", "", 1)
        for r in _load_jsonl(root / "work_items.jsonl"):
            if r.get("work_item_id") == wi:
                return {"card_id": card_id, "type": "work_item", **r}
    if card_id.startswith("incident_"):
        iid = card_id.replace("incident_", "", 1)
        for r in _load_jsonl(root / "incidents.jsonl"):
            if r.get("incident_id") == iid or r.get("event_id") == iid:
                return {"card_id": card_id, "type": "incident", **r}
    return None


# --- Autonomy presets ---


def _presets_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "autonomy_presets"


def list_autonomy_presets(workspace_root: Path) -> List[Dict[str, Any]]:
    """List autonomy presets from artifacts/autonomy_presets/*.json."""
    root = _presets_root(workspace_root)
    if not root.exists():
        return []
    out = []
    for path in sorted(root.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            doc.setdefault("preset_id", path.stem)
            out.append(doc)
        except (json.JSONDecodeError, OSError):
            continue
    return out


def preview_preset_delta(
    workspace_root: Path,
    preset_id: str,
    target_ref: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Preview delta between preset and current state for target.
    Returns { preset: {...}, current: {...}, delta: { autonomy_level?, constraints_added?, ... } }.
    """
    root = _presets_root(workspace_root)
    path = root / f"{preset_id}.json"
    if not path.exists():
        return {"preset": None, "current": None, "delta": {}, "error": "preset_not_found"}
    try:
        preset = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"preset": None, "current": None, "delta": {}, "error": "preset_invalid"}

    current: Dict[str, Any] = {}
    if target_ref:
        # Current autonomy from entity registry or work_items / steering_active
        mat = _materialized_root(workspace_root)
        active_path = mat / "steering_active.jsonl"
        target_id = (target_ref.get("id") or "")
        for r in _load_jsonl(active_path):
            if (r.get("target_ref") or {}).get("id") == target_id:
                current["autonomy_preset"] = "unknown"
                break
        entity_registry = workspace_root / "memory" / "overseer" / "entity_registry.json"
        if entity_registry.exists():
            try:
                reg = json.loads(entity_registry.read_text(encoding="utf-8"))
                for e in reg.get("entities", []):
                    if e.get("id") == target_id:
                        current["autonomy_level"] = e.get("autonomy_level", "normal")
                        break
            except Exception:
                pass

    delta: Dict[str, Any] = {}
    if preset.get("autonomy_level") and preset.get("autonomy_level") != current.get("autonomy_level"):
        delta["autonomy_level"] = {"from": current.get("autonomy_level", "normal"), "to": preset.get("autonomy_level")}
    if preset.get("constraints"):
        delta["constraints"] = preset.get("constraints")

    return {"preset": preset, "current": current or None, "delta": delta}


def apply_autonomy_preset(
    *,
    preset_id: str,
    target_ref: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    expiry_hours: int = 24,
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Apply autonomy preset to target with expiry. Emit AUTONOMY_PRESET_APPLIED.
    Returns event_id.
    """
    workspace_root = Path(workspace_root or ".")
    root = _presets_root(workspace_root)
    path = root / f"{preset_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Preset not found: {preset_id}")
    preset = json.loads(path.read_text(encoding="utf-8"))
    ts = _iso_ts()
    expiry_ts = (datetime.now(timezone.utc) + timedelta(hours=expiry_hours)).isoformat().replace("+00:00", "Z")
    autonomy_level = preset.get("autonomy_level", "normal")
    return emit(
        "AUTONOMY_PRESET_APPLIED",
        "autonomy_preset",
        preset_id,
        {
            "preset_id": preset_id,
            "target_ref": target_ref,
            "autonomy_level": autonomy_level,
            "constraints": preset.get("constraints", []),
            "ts": ts,
            "expiry_ts": expiry_ts,
            "artifact_path": str(path),
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
