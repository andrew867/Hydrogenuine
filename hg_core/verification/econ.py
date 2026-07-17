"""
Pack 5: Verifier economics — pricing, verification budget, verifier set selection.
VERIFIER_PRICE_UPDATED, VERIFICATION_BUDGET_DEBITED, VERIFIER_SET_SELECTED, VERIFICATION_BUDGET_INSUFFICIENT.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_sources(workspace_root: Path) -> List[Dict[str, Any]]:
    """Load registered sources from artifacts (and optional independence_group)."""
    root = workspace_root / "artifacts" / "verification" / "sources"
    if not root.exists():
        return []
    out = []
    for p in root.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            sid = data.get("source_id") or p.stem
            data.setdefault("independence_group", data.get("scope_domain") or sid)
            out.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return out


def get_verifier_price(
    source_id: str,
    workspace_root: Path,
    surge_factor: float = 1.0,
) -> float:
    """Base price from source artifact; multiply by surge_factor for load."""
    root = workspace_root / "artifacts" / "verification" / "sources"
    path = root / f"{source_id}.json"
    base = 1.0
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            base = float(data.get("base_price", 1.0))
        except (json.JSONDecodeError, OSError, TypeError):
            pass
    return round(base * surge_factor, 2)


def update_verifier_price(
    *,
    source_id: str,
    base_price: float,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Write price to source artifact (or new price artifact), emit VERIFIER_PRICE_UPDATED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    root = workspace_root / "artifacts" / "verification" / "sources"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{source_id}.json"
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    data["source_id"] = source_id
    data["base_price"] = base_price
    data.setdefault("name", data.get("name", source_id))
    data["price_updated_ts"] = ts
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return emit(
        "VERIFIER_PRICE_UPDATED",
        "verifier_price",
        source_id,
        {"source_id": source_id, "base_price": base_price, "artifact_id": str(path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def _get_budget_balance(workspace_root: Path, scope: Dict[str, str], budget_key: str) -> Tuple[float, float]:
    """Return (initial, total_debited) for verification budget from ledger."""
    from hg_core.ledger.ledger_writer import iter_events_by_scope
    scope_type = scope.get("type") or "global"
    scope_id = scope.get("id") or "default"
    initial = 0.0
    total_debited = 0.0
    for _st, _sid, ev in iter_events_by_scope(workspace_root):
        if _st != scope_type or _sid != scope_id:
            continue
        action = ev.get("action")
        payload = ev.get("payload") or {}
        if action == "VERIFICATION_BUDGET_INITIALIZED" and payload.get("budget_key") == budget_key:
            initial = float(payload.get("initial_balance", 0))
        elif action == "VERIFICATION_BUDGET_DEBITED" and payload.get("budget_key") == budget_key:
            total_debited += float(payload.get("amount", 0))
    return initial, total_debited


def init_verification_budget(
    *,
    budget_key: str,
    initial_balance: float,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit VERIFICATION_BUDGET_INITIALIZED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "VERIFICATION_BUDGET_INITIALIZED",
        "verification_budget",
        budget_key,
        {"budget_key": budget_key, "initial_balance": initial_balance, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def get_verification_budget_status(
    workspace_root: Path,
    scope: Dict[str, str],
    budget_key: str = "default",
) -> Tuple[float, float, float]:
    """Return (current_balance, initial_balance, total_debited)."""
    initial, total_debited = _get_budget_balance(workspace_root, scope, budget_key)
    return max(0.0, initial - total_debited), initial, total_debited


def debit_verification_budget(
    *,
    budget_key: str,
    amount: float,
    action_id: str,
    selection_id: Optional[str] = None,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    Debit verification budget. Returns (success, event_id_or_reason).
    If insufficient, does not debit and returns (False, event_id for VERIFICATION_BUDGET_INSUFFICIENT).
    """
    workspace_root = Path(workspace_root or ".")
    balance, _, _ = get_verification_budget_status(workspace_root, scope, budget_key)
    if balance < amount:
        ts = _iso_ts()
        ev_id = emit(
            "VERIFICATION_BUDGET_INSUFFICIENT",
            "verification_budget",
            budget_key,
            {"budget_key": budget_key, "required": amount, "balance": balance, "action_id": action_id, "ts": ts},
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        return False, ev_id
    ts = _iso_ts()
    ev_id = emit(
        "VERIFICATION_BUDGET_DEBITED",
        "verification_budget",
        budget_key,
        {"budget_key": budget_key, "amount": amount, "action_id": action_id, "selection_id": selection_id or "", "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return True, ev_id


def select_verifier_set(
    *,
    action_id: str,
    workspace_root: Path,
    scope: Dict[str, str],
    actor: Dict[str, str],
    min_robustness: float = 0.0,
    min_independence_groups: int = 1,
    budget_key: str = "default",
    max_cost: Optional[float] = None,
    surge_factor: float = 1.0,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Select a set of verifiers meeting robustness/diversity within budget.
    Returns (selection_payload, selection_id) or (None, insufficient_reason).
    selection_payload has sources (source_id, price, independence_group), estimated_cost, expected_robustness.
    """
    sources = _load_sources(workspace_root)
    if not sources:
        return None, "no_sources"
    balance, _, _ = get_verification_budget_status(workspace_root, scope, budget_key)
    if max_cost is None:
        max_cost = balance
    # Build candidates with price and independence_group
    candidates: List[Dict[str, Any]] = []
    for s in sources:
        sid = s.get("source_id") or ""
        if not sid:
            continue
        price = get_verifier_price(sid, workspace_root, surge_factor)
        grp = s.get("independence_group") or sid
        reliability = float(s.get("reliability_score", 1.0))
        candidates.append({"source_id": sid, "price": price, "independence_group": grp, "reliability": reliability})
    # Greedy: pick one per independence group (diversity) up to max_cost
    selected: List[Dict[str, Any]] = []
    used_groups: set = set()
    total_cost = 0.0
    candidates.sort(key=lambda x: (-x["reliability"], x["price"]))
    for c in candidates:
        if len(used_groups) >= min_independence_groups and total_cost >= max_cost * 0.5:
            break
        if c["independence_group"] in used_groups and len(used_groups) >= min_independence_groups:
            continue
        if total_cost + c["price"] > max_cost:
            continue
        selected.append({"source_id": c["source_id"], "price": c["price"], "independence_group": c["independence_group"]})
        used_groups.add(c["independence_group"])
        total_cost += c["price"]
    if len(used_groups) < min_independence_groups or (min_robustness > 0 and len(selected) < 1):
        return None, "insufficient_diversity_or_robustness"
    expected_robustness = min(1.0, 0.3 + 0.4 * len(used_groups) + 0.2 * len(selected)) if selected else 0.0
    ts = _iso_ts()
    selection_id = "vsel_" + hashlib.sha256(f"{action_id}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "verification" / "selections"
    root.mkdir(parents=True, exist_ok=True)
    rationale_path = root / f"{selection_id}.json"
    rationale_path.write_text(
        json.dumps({
            "selection_id": selection_id,
            "action_id": action_id,
            "sources": selected,
            "estimated_cost": round(total_cost, 2),
            "expected_robustness": round(expected_robustness, 2),
            "ts": ts,
        }, indent=2),
        encoding="utf-8",
    )
    payload = {
        "selection_id": selection_id,
        "action_id": action_id,
        "sources": selected,
        "estimated_cost": round(total_cost, 2),
        "expected_robustness": round(expected_robustness, 2),
        "ts": ts,
        "rationale_artifact_id": str(rationale_path),
    }
    emit(
        "VERIFIER_SET_SELECTED",
        "verifier_selection",
        selection_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return payload, selection_id


def select_verifier_set_and_debit(
    *,
    action_id: str,
    workspace_root: Path,
    scope: Dict[str, str],
    actor: Dict[str, str],
    min_robustness: float = 0.0,
    min_independence_groups: int = 1,
    budget_key: str = "default",
    surge_factor: float = 1.0,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Select verifier set and debit budget. Returns (selection_id, event_id) or (None, insufficient_reason).
    """
    workspace_root = Path(workspace_root)
    result, sel_id_or_reason = select_verifier_set(
        action_id=action_id,
        workspace_root=workspace_root,
        scope=scope,
        actor=actor,
        min_robustness=min_robustness,
        min_independence_groups=min_independence_groups,
        budget_key=budget_key,
        surge_factor=surge_factor,
    )
    if result is None:
        return None, sel_id_or_reason
    cost = result["estimated_cost"]
    ok, ev_or_id = debit_verification_budget(
        budget_key=budget_key,
        amount=cost,
        action_id=action_id,
        selection_id=result["selection_id"],
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    if not ok:
        return None, ev_or_id
    return result["selection_id"], ev_or_id
