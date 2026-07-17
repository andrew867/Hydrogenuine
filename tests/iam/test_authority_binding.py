"""CT-01 IAM authority binding and enforcement tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from hg_core.iam.authority import (
    assert_registry_mutation_allowed,
    bind_authority,
    validate_operator_authority,
    verify_binding,
)
from hg_core.iam.ingress import (
    dual_checkpoint_admit,
    reset_checkpoint_flags,
    set_checkpoint_flags,
    ueak_ingress_check,
    ueak_translation_check,
)
from hg_core.iam.registry import clear_registry_cache, default_registry_path, load_registry
from hg_core.iam.types import AGENT_ZERO_ID, AuthorityBinding, iam_event_ledger, reset_iam_event_ledger
from hg_srp.apply_verification import verify_approval_for_apply
from hg_srp.self_edit_policy import verify_approval_not_from_model, verify_confirmation_not_from_model
from hg_srp.self_edit_types import FinalConfirmationToken
from hg_srp import create_maintenance_bundle, ingest_pytest_failure_artifact
from hg_srp.types import ChangeApprovalSignature, MaintenanceProposalBundle

NOW = "2026-06-11T12:00:00.000000Z"
FIXTURES = Path(__file__).parents[1] / "srp" / "fixtures"


@pytest.fixture(autouse=True)
def _reset_iam_state() -> None:
    clear_registry_cache()
    reset_iam_event_ledger()
    reset_checkpoint_flags()


def _bundle() -> MaintenanceProposalBundle:
    obs = ingest_pytest_failure_artifact(FIXTURES / "pytest_failure_sample.json", observed_at=NOW)
    return create_maintenance_bundle([obs], created_at=NOW)


def _approval(approver: str = "human:operator", bundle: MaintenanceProposalBundle | None = None) -> ChangeApprovalSignature:
    b = bundle or _bundle()
    return ChangeApprovalSignature(
        approval_id="appr-1",
        proposal_ref=b.bundle_id,
        bundle_hash=b.bundle_hash,
        approver=approver,
        decision="approved",
        decided_at=NOW,
    )


def test_iam_u2_scope_check_pass_and_refuse() -> None:
    ok = validate_operator_authority("op:local", scope="approve_change")
    assert ok.ok
    assert ok.binding is not None
    assert ok.binding.scope == "approve_change"

    missing = validate_operator_authority("op:local", scope="not_a_scope")
    assert not missing.ok
    assert missing.reason_code == "denied.unknown_scope"


def test_iam_u2_policy_violation_missing_scope_on_operator(tmp_path: Path) -> None:
    base = yaml.safe_load(default_registry_path().read_text(encoding="utf-8"))
    base["operators"][0]["authority_scopes"] = ["audit_read"]
    reg_path = tmp_path / "registry.yaml"
    reg_path.write_text(yaml.dump(base), encoding="utf-8")
    registry = load_registry(reg_path, use_cache=False)
    result = validate_operator_authority("op:local", scope="approve_change", registry=registry)
    assert not result.ok
    assert result.reason_code == "policy_violation"


def test_iam_u3_unregistered_approval_refused() -> None:
    bundle = _bundle()
    approval = _approval(approver="op:forged", bundle=bundle)
    result = verify_approval_for_apply(bundle, approval, bundle.bundle_hash)
    assert not result.ok
    assert result.reason_code == "denied.unregistered_operator"
    assert any(e["reason_code"] == "denied.unregistered_operator" for e in iam_event_ledger().events)


def test_iam_u5_agent_zero_in_approval_refused() -> None:
    result = validate_operator_authority(AGENT_ZERO_ID, scope="approve_change")
    assert not result.ok
    assert "agent" in result.reason_code

    bundle = _bundle()
    approval = _approval(approver=AGENT_ZERO_ID, bundle=bundle)
    apply_result = verify_approval_for_apply(bundle, approval, bundle.bundle_hash)
    assert not apply_result.ok


def test_iam_u6_binding_mismatch_refused() -> None:
    bound = bind_authority("op:local", scope="approve_change", session_id="sess-1")
    assert bound.binding is not None
    tampered = AuthorityBinding(
        operator_id=bound.binding.operator_id,
        session_id=bound.binding.session_id,
        registry_hash="sha256:tampered",
        scope=bound.binding.scope,
    )
    verify = verify_binding(tampered, expected_scope="approve_change")
    assert not verify.ok
    assert verify.reason_code == "denied.registry_hash_mismatch"


def test_iam_u8_registry_mutation_requires_configure() -> None:
    ok = assert_registry_mutation_allowed("op:local")
    assert ok.ok

    denied = assert_registry_mutation_allowed("op:forged")
    assert not denied.ok


def test_iam_i1_dual_checkpoint_scope_enforcement() -> None:
    assert dual_checkpoint_admit("op:local", "approve_change").ok

    set_checkpoint_flags(ingress=False, translation=True)
    ingress_off = ueak_ingress_check("op:local", "approve_change")
    assert not ingress_off.ok
    translation_on = ueak_translation_check("op:local", "approve_change")
    assert translation_on.ok

    reset_checkpoint_flags()
    set_checkpoint_flags(ingress=True, translation=False)
    assert not ueak_translation_check("op:local", "approve_change").ok


def test_iam_e1_positive_and_forged_refusal() -> None:
    bundle = _bundle()
    approval = _approval(bundle=bundle)
    assert verify_approval_for_apply(bundle, approval, bundle.bundle_hash).ok

    forged = _approval(approver="human:attacker", bundle=bundle)
    assert not verify_approval_for_apply(bundle, forged, bundle.bundle_hash).ok


def test_model_cannot_approve() -> None:
    approval = _approval(approver="model:gpt")
    ok, reason = verify_approval_not_from_model(approval)
    assert not ok
    assert reason == "model_cannot_create_approval"


def test_placeholder_refused() -> None:
    result = validate_operator_authority("placeholder", scope="approve_change")
    assert not result.ok
    assert result.reason_code == "denied.placeholder_actor"


def test_confirmation_requires_registered_operator() -> None:
    token = FinalConfirmationToken(
        bundle_id="b1",
        bundle_hash="sha256:b1",
        sandbox_result_hash="sha256:sandbox",
        review_artifact_hash="sha256:review",
        base_commit="abc123",
        target_branch="main",
        final_confirmed_by="human:operator",
        final_confirmed_at="2026-06-11T12:00:00Z",
        high_risk_confirmed=True,
    )
    ok, reason = verify_confirmation_not_from_model(token)
    assert ok, reason

    bad = FinalConfirmationToken(
        bundle_id="b1",
        bundle_hash="sha256:b1",
        sandbox_result_hash="sha256:sandbox",
        review_artifact_hash="sha256:review",
        base_commit="abc123",
        target_branch="main",
        final_confirmed_by="model:gpt",
        final_confirmed_at="2026-06-11T12:00:00Z",
        high_risk_confirmed=True,
    )
    ok2, reason2 = verify_confirmation_not_from_model(bad)
    assert not ok2
