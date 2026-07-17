"""Phase 21 no external side effects."""
from __future__ import annotations

import ast
import os
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
PKG = WORKSPACE / "hg_runtime/task_selection"


def test_env_live_writes_off():
    assert os.environ.get("HG_SOCIAL_LIVE_PUBLISH", "false").lower() != "true"


def test_no_publish_in_package_source():
    text = "\n".join(p.read_text(encoding="utf-8") for p in PKG.glob("*.py"))
    assert "publish_live" not in text or "BLOCKED" in text or "blocked" in text


def test_no_empty_pass_stubs():
    for path in PKG.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                body = [n for n in node.body if not isinstance(n, ast.Expr) or not isinstance(n.value, ast.Constant)]
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    raise AssertionError(f"empty stub: {path}:{node.name}")


def test_agent_turn_bridge_attaches_ref():
    from hg_runtime.agent_turn_engine.task_selection_bridge import enrich_turn_receipt_payload
    from hg_runtime.task_selection.task_receipts import TaskSelectionDecision, TaskSelectionReceipt
    from hg_runtime.task_selection.task_selector import TaskSelectionResult
    from hg_runtime.task_selection.schema import TaskSelectionVerdict

    decision = TaskSelectionDecision(
        task_selection_decision_id="d1",
        universe_ref="u1",
        candidate_refs=("c1",),
        refused_candidate_refs=(),
        deferred_candidate_refs=(),
        selection_reason_code="test",
        authority_boundary_ref="ref",
        verdict=TaskSelectionVerdict.GREEN_TASK_SELECTED.value,
        created_at="t",
        selected_candidate_ref="c1",
    ).with_hash()
    receipt = TaskSelectionReceipt(
        task_selection_receipt_id="r1",
        decision_ref="d1",
        external_action_required=False,
        external_action_allowed=False,
        created_at="t",
    ).with_hash()
    result = TaskSelectionResult(
        decision=decision,
        receipt=receipt,
        switch_receipt=None,
        verdict=TaskSelectionVerdict.GREEN_TASK_SELECTED,
        selected=None,
        refused=[],
    )
    out = enrich_turn_receipt_payload({"turn_id": "t1"}, result)
    assert out["task_selection_decision_ref"] == "d1"
    assert out["task_selection_receipt_ref"] == "r1"
