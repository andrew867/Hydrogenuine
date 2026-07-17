"""
Differentiators Pack 4: Domain value segmentation, risk budget v2, conflict detection.

See .cursor/plans/differentiators/chapter4/differentiators_pack4_domain_values_riskbudget_v2/
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone, timedelta

from hg_core.values import (
    publish_value_profile,
    resolve_profile,
    record_value_profile_applied,
    publish_value_profile_resolution,
)
from hg_core.conflicts import (
    detect_value_conflict,
    emit_conflict_detected,
    create_conflict_work_item,
    publish_conflict_resolution,
)
from hg_core.risk_budget import (
    compute_risk_cost_v2,
    emit_risk_cost_computed,
    INFINITE_COST,
)
from hg_core.exceptions import grant_exception, check_exception_expired


SCOPE = {"type": "run", "id": "test_diff4"}
ACTOR = {"agent_id": "agent_diff4", "pubkey": "0" * 64, "key_id": "k"}


def test_resolve_profile_by_domain_tenant_env(tmp_path: Path) -> None:
    """Resolver picks correct profile by domain, tenant, environment."""
    publish_value_profile(
        domain_id="dom_a",
        weights=[{"dimension": "speed", "weight": 0.8}, {"dimension": "privacy", "weight": 0.2}],
        constraints=[{"dimension": "privacy", "op": ">=", "value": 0.1}],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        tenant_id="t1",
        environment="prod",
    )
    publish_value_profile(
        domain_id="dom_a",
        weights=[{"dimension": "speed", "weight": 0.9}, {"dimension": "privacy", "weight": 0.1}],
        constraints=[],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        tenant_id="t1",
        environment="staging",
    )
    # No tenant/env: latest for domain
    p = resolve_profile(tmp_path, "dom_a")
    assert p is not None
    assert p.get("domain_id") == "dom_a"
    # With tenant and env
    p_prod = resolve_profile(tmp_path, "dom_a", tenant_id="t1", environment="prod")
    assert p_prod is not None
    assert p_prod.get("environment") == "prod"
    p_staging = resolve_profile(tmp_path, "dom_a", tenant_id="t1", environment="staging")
    assert p_staging is not None
    assert p_staging.get("environment") == "staging"
    assert resolve_profile(tmp_path, "dom_b") is None


def test_value_profile_applied_recorded(tmp_path: Path) -> None:
    """Applied profile is recorded for decisions and actions."""
    profile_id = publish_value_profile(
        domain_id="dom_x",
        weights=[{"dimension": "safety", "weight": 1.0}],
        constraints=[],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    ev = record_value_profile_applied(
        profile_id=profile_id,
        decision_id="dec_1",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        reason="pre-commit",
    )
    assert ev
    ev2 = record_value_profile_applied(
        profile_id=profile_id,
        action_id="act_1",
        work_item_id="wi_1",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert ev2


def test_constraint_violation_triggers_conflict(tmp_path: Path) -> None:
    """Decision weights violating profile constraints trigger CONFLICT_DETECTED path."""
    profile = {
        "profile_id": "vp_test",
        "domain_id": "d",
        "constraints": [
            {"dimension": "privacy", "op": ">=", "value": 0.5},
            {"dimension": "speed", "op": "<=", "value": 0.8},
        ],
    }
    # Compliant
    assert detect_value_conflict(
        [{"dimension": "privacy", "weight": 0.6}, {"dimension": "speed", "weight": 0.7}],
        profile,
    ) is None
    # Violation: privacy too low
    conflict = detect_value_conflict(
        [{"dimension": "privacy", "weight": 0.2}, {"dimension": "speed", "weight": 0.7}],
        profile,
    )
    assert conflict is not None
    assert conflict.get("type") == "value"
    assert len(conflict.get("violations", [])) >= 1
    # Emit CONFLICT_DETECTED
    cid = emit_conflict_detected(
        conflict_type="value",
        scope=SCOPE,
        refs=[{"profile_id": "vp_test", "violations": conflict["violations"]}],
        scope_actor=ACTOR,
        workspace_root=tmp_path,
        rationale="privacy weight below constraint",
    )
    assert cid.startswith("conf_")
    assert (tmp_path / "artifacts" / "conflicts" / f"{cid}.json").exists()


def test_conflict_work_item_and_resolution(tmp_path: Path) -> None:
    """Create conflict work item and publish resolution."""
    cid = emit_conflict_detected(
        conflict_type="policy",
        scope=SCOPE,
        refs=[{"policy_ref": "pol_1"}],
        scope_actor=ACTOR,
        workspace_root=tmp_path,
    )
    ev_id, wi_id = create_conflict_work_item(
        conflict_id=cid,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        title="Arbitrate policy conflict",
    )
    assert ev_id
    assert wi_id.startswith("wi_")
    ev_res = publish_conflict_resolution(
        conflict_id=cid,
        resolution={"outcome": "override_granted", "expiry_ts": "2026-12-31T00:00:00Z"},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert ev_res
    assert (tmp_path / "artifacts" / "conflicts" / "resolutions").exists()


def test_exception_grant_and_expiry(tmp_path: Path) -> None:
    """Exceptions can be granted and expire (EXCEPTION_EXPIRED when past expiry)."""
    past_expiry = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
    ex_id = grant_exception(
        scope=SCOPE,
        expiry_ts=past_expiry,
        refs=[{"conflict_id": "conf_1"}],
        actor=ACTOR,
        workspace_root=tmp_path,
        reason="temporary override",
    )
    assert ex_id.startswith("ex_")
    assert (tmp_path / "artifacts" / "exceptions" / f"{ex_id}.json").exists()
    # Check expired: should emit EXCEPTION_EXPIRED and return True
    expired = check_exception_expired(
        exception_id=ex_id,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert expired is True


def test_exception_not_expired_yet(tmp_path: Path) -> None:
    """Exception with future expiry does not emit EXCEPTION_EXPIRED."""
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    ex_id = grant_exception(
        scope=SCOPE,
        expiry_ts=future,
        refs=[],
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    expired = check_exception_expired(
        exception_id=ex_id,
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert expired is False


def test_risk_v2_fan_out_and_diversity(tmp_path: Path) -> None:
    """Fan-out and poor verifier diversity increase cost."""
    cost_low, _ = compute_risk_cost_v2(fan_out=1.0, verifier_diversity_quality=1.0)
    cost_high_fan, _ = compute_risk_cost_v2(fan_out=10.0, verifier_diversity_quality=1.0)
    cost_low_div, _ = compute_risk_cost_v2(fan_out=1.0, verifier_diversity_quality=0.3)
    assert cost_high_fan >= cost_low
    assert cost_low_div >= cost_low


def test_risk_v2_continuity_and_gap(tmp_path: Path) -> None:
    """Continuity invalidations and gap score increase cost."""
    cost_base, ctrl_base = compute_risk_cost_v2(continuity_invalidations=0, gap_score=0.0)
    cost_cont, ctrl_cont = compute_risk_cost_v2(continuity_invalidations=2)
    cost_gap, ctrl_gap = compute_risk_cost_v2(gap_score=0.8)
    assert cost_cont >= cost_base
    assert cost_gap >= cost_base
    assert "min_robustness_threshold" in ctrl_cont or cost_cont > cost_base
    assert "step_size_limits" in ctrl_gap or cost_gap > cost_base


def test_risk_v2_hard_constraint_infinite(tmp_path: Path) -> None:
    """Hard constraint violation makes cost infinite unless exception."""
    cost, required_controls = compute_risk_cost_v2(constraint_violation=True)
    assert cost >= INFINITE_COST - 1
    assert required_controls.get("independent_reviewer_required") is True
    assert "step_size_limits" in required_controls or "min_evidence_count" in required_controls


def test_risk_cost_computed_emitted(tmp_path: Path) -> None:
    """RISK_COST_COMPUTED emitted with rationale artifact."""
    risk_id, ev_id = emit_risk_cost_computed(
        action_id="act_1",
        work_item_id="wi_1",
        cost=2.5,
        components={"fan_out": 2.0, "gap_score": 0.2},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert risk_id.startswith("risk_")
    assert ev_id
    assert (tmp_path / "artifacts" / "risk" / f"{risk_id}.json").exists()
