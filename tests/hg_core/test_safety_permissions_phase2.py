"""Tests for autonomy Phase 2: capability model (S1), safety gate (S2), approval tiers (S3), policy tests (S5)."""

import json
import pytest
from pathlib import Path

from hg_core.task_graph.capability_enforcement import (
    load_workflow_capabilities,
    check_allowed,
)
from hg_core.task_graph.approval_tiers import (
    get_approval_tier,
    format_approval_request,
)
from hg_core.safety_gate import is_outbound_allowed
from hg_core.autonomy_config import get_outbound_safety_gate_enabled, save_autonomy_config


# --- S1: Capability deny ---


def test_capability_deny_when_no_declaration(tmp_path):
    """When no workflow declaration exists, check_allowed denies (least-privilege)."""
    allowed, reason = check_allowed("nonexistent-workflow", "destination", "twitter", workspace_root=tmp_path)
    assert allowed is False
    assert "no_workflow_declaration" in reason or "undeclared" in reason


def test_capability_deny_undeclared_scope(tmp_path):
    """When workflow declaration exists but scope/destination not in list, check_allowed denies."""
    decl_dir = tmp_path / "memory" / "automation" / "workflows"
    decl_dir.mkdir(parents=True)
    (decl_dir / "task-a.json").write_text(json.dumps({
        "read_scopes": ["memory/automation/task-a"],
        "write_scopes": ["memory/automation/task-a"],
        "allowed_destinations": ["mastodon"],
        "allowed_tools": ["post"],
    }))
    allowed, reason = check_allowed("task-a", "destination", "twitter", workspace_root=tmp_path)
    assert allowed is False
    assert "twitter" in reason or "undeclared" in reason

    allowed2, _ = check_allowed("task-a", "destination", "mastodon", workspace_root=tmp_path)
    assert allowed2 is True


def test_capability_allow_declared_scope(tmp_path):
    """When scope/destination is in declaration, check_allowed allows."""
    decl_dir = tmp_path / "memory" / "automation" / "workflows"
    decl_dir.mkdir(parents=True)
    (decl_dir / "task-b.json").write_text(json.dumps({
        "allowed_destinations": ["twitter", "mastodon"],
    }))
    allowed, reason = check_allowed("task-b", "destination", "twitter", workspace_root=tmp_path)
    assert allowed is True
    assert reason == ""


# --- S2: Safety gate ---


def test_safety_gate_blocks_empty_content_when_on(tmp_path):
    """When outbound safety gate is ON, empty content is blocked."""
    save_autonomy_config(outbound_safety_gate_enabled=True, workspace_root=tmp_path)
    try:
        allowed, reason = is_outbound_allowed("", workspace_root=tmp_path)
        assert allowed is False
        assert "empty" in reason.lower() or reason
    finally:
        save_autonomy_config(outbound_safety_gate_enabled=False, workspace_root=tmp_path)


def test_safety_gate_allows_content_when_off(tmp_path):
    """When outbound safety gate is OFF, content is allowed (no check)."""
    save_autonomy_config(outbound_safety_gate_enabled=False, workspace_root=tmp_path)
    allowed, reason = is_outbound_allowed("any content", workspace_root=tmp_path)
    assert allowed is True
    assert reason == ""


def test_safety_gate_blocks_disallowed_topic_when_on(tmp_path):
    """When gate is ON, content containing disallowed topic keyword is blocked."""
    (tmp_path / "memory" / "automation").mkdir(parents=True)
    (tmp_path / "memory" / "automation" / "safety_gate_config.json").write_text(
        json.dumps({"disallowed_topics": ["forbidden_topic"]})
    )
    save_autonomy_config(outbound_safety_gate_enabled=True, workspace_root=tmp_path)
    try:
        allowed, reason = is_outbound_allowed("This post is about forbidden_topic.", workspace_root=tmp_path)
        assert allowed is False
        assert reason == "disallowed_topic"
    finally:
        save_autonomy_config(outbound_safety_gate_enabled=False, workspace_root=tmp_path)


def test_safety_gate_blocks_pii_ssn_when_on(tmp_path):
    """When gate is ON, content with SSN is blocked."""
    save_autonomy_config(outbound_safety_gate_enabled=True, workspace_root=tmp_path)
    try:
        allowed, reason = is_outbound_allowed("My SSN is 123-45-6789 for verification.", workspace_root=tmp_path)
        assert allowed is False
        assert reason == "pii_ssn"
    finally:
        save_autonomy_config(outbound_safety_gate_enabled=False, workspace_root=tmp_path)


def test_safety_gate_blocks_pii_email_when_on(tmp_path):
    """When gate is ON, content with email is blocked."""
    save_autonomy_config(outbound_safety_gate_enabled=True, workspace_root=tmp_path)
    try:
        allowed, reason = is_outbound_allowed("Contact me at user@example.com", workspace_root=tmp_path)
        assert allowed is False
        assert reason == "pii_email"
    finally:
        save_autonomy_config(outbound_safety_gate_enabled=False, workspace_root=tmp_path)


def test_safety_gate_blocks_harassment_when_on(tmp_path):
    """When gate is ON, content with harassment keywords is blocked."""
    save_autonomy_config(outbound_safety_gate_enabled=True, workspace_root=tmp_path)
    try:
        allowed, reason = is_outbound_allowed("I will find you and hurt you.", workspace_root=tmp_path)
        assert allowed is False
        assert reason == "harassment"
    finally:
        save_autonomy_config(outbound_safety_gate_enabled=False, workspace_root=tmp_path)


def test_safety_gate_blocks_medical_claim_when_on(tmp_path):
    """When gate is ON, content with unsubstantiated medical claims is blocked."""
    save_autonomy_config(outbound_safety_gate_enabled=True, workspace_root=tmp_path)
    try:
        allowed, reason = is_outbound_allowed("This is a miracle cure for everything.", workspace_root=tmp_path)
        assert allowed is False
        assert reason == "medical_claim"
    finally:
        save_autonomy_config(outbound_safety_gate_enabled=False, workspace_root=tmp_path)


def test_safety_gate_allows_clean_content_when_on(tmp_path):
    """When gate is ON, clean content (no PII, harassment, medical, disallowed) is allowed."""
    save_autonomy_config(outbound_safety_gate_enabled=True, workspace_root=tmp_path)
    try:
        allowed, reason = is_outbound_allowed(
            "Hello, here is a normal post about the weather and books.", workspace_root=tmp_path
        )
        assert allowed is True
        assert reason == ""
    finally:
        save_autonomy_config(outbound_safety_gate_enabled=False, workspace_root=tmp_path)


# --- S3: Approval tiers ---


def test_high_risk_destination_has_tier_ge_1():
    """High-risk destinations require approval tier >= 1."""
    assert get_approval_tier("post", "external_api") >= 1
    assert get_approval_tier("post", "payment") == 2


def test_tier_1_destinations_require_approval():
    """Sensitive social destinations are Tier 1."""
    assert get_approval_tier("post", "twitter") == 1
    assert get_approval_tier("post", "mastodon") == 1


def test_format_approval_request():
    """format_approval_request returns dict with action_type, destination, approval_tier, etc."""
    req = format_approval_request("post", "twitter", "Summary of post", evidence_pointer="run_123")
    assert req["action_type"] == "post"
    assert req["destination"] == "twitter"
    assert req["approval_tier"] in (0, 1, 2)
    assert "content_summary" in req
    assert "on_approve" in req


# --- S5: Policy regression ---


def test_policy_regression_undeclared_denied(tmp_path):
    """Policy regression: undeclared scope/destination is always denied when declaration exists."""
    decl_dir = tmp_path / "memory" / "automation" / "workflows"
    decl_dir.mkdir(parents=True)
    (decl_dir / "regression.json").write_text(json.dumps({
        "allowed_destinations": ["allowed_only"],
    }))
    allowed, _ = check_allowed("regression", "destination", "not_in_list", workspace_root=tmp_path)
    assert allowed is False


def test_policy_regression_least_privilege_no_declaration(tmp_path):
    """Policy regression: when no declaration, least-privilege default is deny."""
    for action in ("read", "write", "destination", "tool"):
        allowed, _ = check_allowed("no_decl", action, "anything", workspace_root=tmp_path)
        assert allowed is False
