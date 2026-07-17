"""Auto-approval rule tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from hg_runtime.auto_approval_rules.evaluator import AutoApprovalEvaluator
from hg_runtime.auto_approval_rules.policy import is_forbidden_rule_action_type
from hg_runtime.auto_approval_rules.revocation import revoke_rule
from hg_runtime.auto_approval_rules.schema import AGENT0_ID, AutoApprovalRuleDecision, AutoApprovalRuleStatus
from hg_runtime.auto_approval_rules.store import AutoApprovalRuleStore
from hg_runtime.exciton_action_model.action_types import AgentActionType
from hg_runtime.exciton_action_model.adapters import _base_request
from hg_runtime.operator_action_queue.queue import OperatorQueueRuntime
from hg_runtime.operator_action_queue.store import OperatorQueueStore


def _store(tmp_path):
    root = tmp_path / "aar"
    return AutoApprovalRuleStore(root / "rules.json", root / "receipts.jsonl")


def _queue(tmp_path):
    root = tmp_path / "oq"
    return OperatorQueueRuntime(
        OperatorQueueStore(root / "q.json", root / "r.jsonl"),
    )


def test_rule_creation_requires_expiry(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(Exception):
        store.create_rule(
            title="t",
            description="d",
            action_type="status_refresh",
            allowed_surfaces=["exciton"],
            max_risk_class="read_only",
            created_by_operator_ref="local-operator",
            expires_at="",
        )


def test_rule_creation_requires_operator_ref(tmp_path):
    store = _store(tmp_path)
    exp = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    with pytest.raises(Exception):
        store.create_rule(
            title="t",
            description="d",
            action_type="status_refresh",
            allowed_surfaces=["exciton"],
            max_risk_class="read_only",
            created_by_operator_ref=AGENT0_ID,
            expires_at=exp,
        )


def test_no_wildcard_action_type(tmp_path):
    store = _store(tmp_path)
    exp = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    with pytest.raises(Exception):
        store.create_rule(
            title="t",
            description="d",
            action_type="*",
            allowed_surfaces=["exciton"],
            max_risk_class="read_only",
            created_by_operator_ref="local-operator",
            expires_at=exp,
        )


@pytest.mark.parametrize(
    "action_type",
    ["status_refresh", "proof_open", "social_draft"],
)
def test_allowed_candidates(action_type):
    assert not is_forbidden_rule_action_type(action_type)


@pytest.mark.parametrize(
    "action_type",
    ["social_post", "web_form_submit", "web_login", "web_purchase", "shell_command", "memory_mutation", "source_patch"],
)
def test_forbidden_types(action_type):
    assert is_forbidden_rule_action_type(action_type)


def test_stop_blocks_auto_approval(tmp_path, monkeypatch):
    soak = tmp_path / ".hg-local" / "soak"
    soak.mkdir(parents=True)
    (soak / "STOP").write_text("1")
    import hg_runtime.operator_action_queue.stop_panic_policy as spp

    monkeypatch.setattr(spp, "WORKSPACE", tmp_path)
    store = _store(tmp_path)
    q = _queue(tmp_path)
    exp = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    store.create_rule(
        title="t",
        description="d",
        action_type="status_refresh",
        allowed_surfaces=["exciton"],
        max_risk_class="read_only",
        created_by_operator_ref="local-operator",
        expires_at=exp,
    )
    item = q.enqueue(_base_request(AgentActionType.STATUS_REFRESH))
    ev = AutoApprovalEvaluator(store, workspace=tmp_path).evaluate_for_queue_item(item)
    assert ev.decision == AutoApprovalRuleDecision.AUTO_APPROVE_STOP_BLOCKED


def test_panic_blocks(tmp_path, monkeypatch):
    soak = tmp_path / ".hg-local" / "soak"
    soak.mkdir(parents=True)
    (soak / "PANIC").write_text("1")
    import hg_runtime.operator_action_queue.stop_panic_policy as spp

    monkeypatch.setattr(spp, "WORKSPACE", tmp_path)
    store = _store(tmp_path)
    q = _queue(tmp_path)
    exp = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    store.create_rule(
        title="t",
        description="d",
        action_type="status_refresh",
        allowed_surfaces=["exciton"],
        max_risk_class="read_only",
        created_by_operator_ref="local-operator",
        expires_at=exp,
    )
    item = q.enqueue(_base_request(AgentActionType.STATUS_REFRESH))
    ev = AutoApprovalEvaluator(store, workspace=tmp_path).evaluate_for_queue_item(item)
    assert ev.decision == AutoApprovalRuleDecision.AUTO_APPROVE_PANIC_BLOCKED


def test_revocation_enforced(tmp_path):
    store = _store(tmp_path)
    exp = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    rule = store.create_rule(
        title="t",
        description="d",
        action_type="proof_open",
        allowed_surfaces=["proof"],
        max_risk_class="read_only",
        created_by_operator_ref="local-operator",
        expires_at=exp,
    )
    revoke_rule(store, rule.rule_id, operator_ref="local-operator", reason="test")
    assert store.get_rule(rule.rule_id).status == AutoApprovalRuleStatus.REVOKED


def test_no_authority_created(tmp_path):
    store = _store(tmp_path)
    exp = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    rule = store.create_rule(
        title="t",
        description="d",
        action_type="status_refresh",
        allowed_surfaces=["exciton"],
        max_risk_class="read_only",
        created_by_operator_ref="local-operator",
        expires_at=exp,
    )
    p = rule.to_payload()
    assert p["authority_created"] is False
    assert p["permission_granted"] is False


def test_stable_rule_hash(tmp_path):
    store = _store(tmp_path)
    exp = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    rule = store.create_rule(
        title="t",
        description="d",
        action_type="status_refresh",
        allowed_surfaces=["exciton"],
        max_risk_class="read_only",
        created_by_operator_ref="local-operator",
        expires_at=exp,
    )
    h1 = rule.to_payload()["rule_hash"]
    h2 = rule.to_payload()["rule_hash"]
    assert h1 == h2
