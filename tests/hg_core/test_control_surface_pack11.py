"""
Control Surface Pack 11: Integration + naming — response contract, taxonomy, branding, meta API, rename.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hg_core.control_surface import (
    control_pause,
    control_resume,
    explain_block,
)
from hg_core.integration import (
    check_no_disallowed_brand_strings,
    error_response,
    get_branding,
    get_public_class,
    list_taxonomy_mappings,
    paginated_response,
    success_response,
)
from hg_core.ledger.ledger_writer import iterate_events


def _scope_actor():
    return {"type": "run", "id": "test"}, {"agent_id": "ops", "pubkey": "0" * 64, "key_id": "k"}


# ---- Response contract ----
def test_success_response_shape() -> None:
    out = success_response({"x": 1})
    assert out["ok"] is True
    assert out["data"] == {"x": 1}


def test_error_response_shape() -> None:
    out = error_response("ERR", "msg", details={"a": 1}, trace_id="tid")
    assert out["ok"] is False
    assert out["error"]["code"] == "ERR"
    assert out["error"]["message"] == "msg"
    assert out["error"]["details"] == {"a": 1}
    assert out["error"]["trace_id"] == "tid"


def test_paginated_response_shape() -> None:
    out = paginated_response([1, 2], next_cursor="c")
    assert out["items"] == [1, 2]
    assert out["next_cursor"] == "c"


# ---- UI action contract: control actions emit ledger events ----
def test_control_pause_emits_entity_paused(tmp_path: Path) -> None:
    scope, actor = _scope_actor()
    eid = control_pause(
        target={"type": "entity", "id": "e1"},
        scope=scope,
        actor=actor,
        workspace_root=tmp_path,
    )
    assert eid
    events = list(iterate_events(tmp_path, scope_type="run", scope_id="test"))
    assert any(ev.get("action") == "ENTITY_PAUSED" for ev in events)


def test_control_resume_emits_entity_resumed(tmp_path: Path) -> None:
    scope, actor = _scope_actor()
    eid = control_resume(
        target={"type": "entity", "id": "e1"},
        scope=scope,
        actor=actor,
        workspace_root=tmp_path,
    )
    assert eid
    events = list(iterate_events(tmp_path, scope_type="run", scope_id="test"))
    assert any(ev.get("action") == "ENTITY_RESUMED" for ev in events)


# ---- Explainability contract: explain_block shape ----
def test_explain_block_shape_includes_gate_missing_evidence_recommended(tmp_path: Path) -> None:
    out = explain_block(tmp_path, work_item_id="nonexistent")
    assert out is not None
    assert "ref_type" in out
    assert "ref_id" in out
    assert "blocked" in out
    assert "gate" in out
    assert "missing_evidence" in out
    assert "recommended_next_step" in out


def test_explain_block_blocked_item_has_recommended_next_step(tmp_path: Path) -> None:
    (tmp_path / "memory" / "materialized").mkdir(parents=True, exist_ok=True)
    wi_path = tmp_path / "memory" / "materialized" / "work_items.jsonl"
    wi_path.write_text(
        '{"work_item_id": "wi1", "status": "blocked", "updated_ts": "2026-01-01T00:00:00Z"}\n',
        encoding="utf-8",
    )
    out = explain_block(tmp_path, work_item_id="wi1")
    assert out is not None
    assert out.get("blocked") is True
    assert out.get("gate")
    assert isinstance(out.get("missing_evidence"), list)
    assert out.get("recommended_next_step") is not None


# ---- Taxonomy: required event classes covered ----
REQUIRED_PUBLIC_CLASSES = {
    "SwarmLifecycle",
    "WorkItem",
    "GlobalControl",
    "Steering",
    "Drift",
    "Control",
    "Orchestration",
    "Routing",
}


def test_taxonomy_mappings_cover_required_classes() -> None:
    mappings = list_taxonomy_mappings()
    classes = {m["conceptual_class"] for m in mappings}
    for req in REQUIRED_PUBLIC_CLASSES:
        assert req in classes, f"Missing conceptual class: {req}"


def test_get_public_class_for_control_events() -> None:
    assert get_public_class("ENTITY_PAUSED") == "Control"
    assert get_public_class("ENTITY_RESUMED") == "Control"
    assert get_public_class("WORK_ITEM_CREATED") == "WorkItem"
    assert get_public_class("SWARM_CREATED") == "SwarmLifecycle"


# ---- Rename: no disallowed brand strings in code ----
def test_no_disallowed_brand_strings_in_hg_core() -> None:
    root = Path(__file__).resolve().parent.parent.parent
    # Exclude files that define DISALLOWED_BRAND_STRINGS
    exclude = [
        root / "hg_core" / "integration" / "branding.py",
        root / "hg_core" / "integration" / "rename_check.py",
    ]
    passed, violations = check_no_disallowed_brand_strings(
        root, paths=[root / "hg_core"], exclude_paths=exclude
    )
    assert passed, f"Disallowed brand strings found: {violations}"


def test_branding_returns_placeholder_or_version() -> None:
    root = Path(__file__).resolve().parent.parent.parent
    b = get_branding(root)
    assert "project_name" in b
    assert "version" in b
    assert b["version"]


# ---- Meta API (branding) ----
def test_api_meta_branding_shape(tmp_path: Path) -> None:
    from hg_core.control_surface import api_meta_branding

    out = api_meta_branding(tmp_path)
    assert "project_name" in out
    assert "version" in out
