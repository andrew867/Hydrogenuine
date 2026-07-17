"""Mission cases 10-16: role mapping + risk/step-up policy."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hg_operator_auth.identity import OperatorIdentity
from hg_operator_auth.roles import can_approve_as_human, map_roles
from hg_operator_auth.stepup_policy import evaluate_step_up

NOW = datetime(2026, 7, 3, 21, 0, 0, tzinfo=timezone.utc)


def _identity(roles, *, step_up=False, evidence=(), auth_age_s=60):
    auth_time = (NOW - timedelta(seconds=auth_age_s)).isoformat().replace("+00:00", "Z")
    return OperatorIdentity(
        provider="keycloak", issuer="http://localhost:8180/realms/hg",
        subject="3f2b8c1e-1111-4222-8333-444455556666",
        display_name="Demo", email="", roles=tuple(roles),
        session_id_hash="sha256:" + "a" * 64, auth_time=auth_time,
        assurance_level="otp" if step_up else "password",
        step_up_required=step_up, step_up_satisfied=step_up and bool(evidence),
        production_operator_auth=True, step_up_evidence=tuple(evidence))


def test_legacy_roles_map_to_hg_roles():
    assert map_roles(["superadmin"]) == ("hg.admin", "hg.config_admin", "hg.breakglass")
    assert map_roles(["tenant_admin"]) == ("hg.admin", "hg.approver")
    assert map_roles(["operator"]) == ("hg.operator", "hg.approver")
    assert map_roles(["viewer"]) == ("hg.viewer",)
    assert map_roles(["service"]) == ()
    assert "hg.operator" in map_roles(["hg.operator"])


def test_high_risk_requires_fresh_step_up():
    ident = _identity(["hg.memory_admin", "hg.high_risk_approver", "hg.approver"])
    v = evaluate_step_up(action_class="memory_mutation", decision="approve",
                         identity=ident, now=NOW)
    assert not v.allowed and v.reason == "step_up_missing"
    ident2 = _identity(["hg.memory_admin", "hg.high_risk_approver", "hg.approver"],
                       step_up=True, evidence=("amr:otp",))
    v2 = evaluate_step_up(action_class="memory_mutation", decision="approve",
                          identity=ident2, now=NOW,
                          last_step_up_at=NOW - timedelta(seconds=100))
    assert v2.allowed and v2.step_up_satisfied
    v3 = evaluate_step_up(action_class="memory_mutation", decision="approve",
                          identity=ident2, now=NOW,
                          last_step_up_at=NOW - timedelta(seconds=1200))
    assert not v3.allowed and v3.reason == "step_up_stale"


def test_restricted_requires_step_up_every_approval():
    ident = _identity(["hg.restricted_approver", "hg.approver"])
    v = evaluate_step_up(action_class="external_effect", decision="approve",
                         identity=ident, now=NOW)
    assert not v.allowed and v.reason == "step_up_missing"
    ident2 = _identity(["hg.restricted_approver", "hg.approver"],
                       step_up=True, evidence=("amr:webauthn",))
    v2 = evaluate_step_up(action_class="external_effect", decision="approve",
                          identity=ident2, now=NOW)
    assert v2.allowed and v2.reason == "step_up_per_approval"


def test_breakglass_requires_reason():
    ident = _identity(["hg.breakglass", "hg.approver"],
                      step_up=True, evidence=("amr:webauthn",))
    v = evaluate_step_up(action_class="breakglass", decision="approve",
                         identity=ident, now=NOW, breakglass_reason="")
    assert not v.allowed and v.reason == "breakglass_reason_required"
    v2 = evaluate_step_up(action_class="breakglass", decision="approve",
                          identity=ident, now=NOW,
                          breakglass_reason="incident-42 containment")
    assert v2.allowed


def test_denial_requires_no_step_up_by_default():
    ident = _identity(["hg.restricted_approver", "hg.approver"])
    v = evaluate_step_up(action_class="external_effect", decision="deny",
                         identity=ident, now=NOW)
    assert v.allowed and not v.step_up_required
    assert v.reason == "deny_no_step_up_required"


def test_config_action_requires_config_admin_role():
    ident = _identity(["hg.approver", "hg.operator"])
    v = evaluate_step_up(action_class="configuration", decision="approve",
                         identity=ident, now=NOW)
    assert not v.allowed and v.reason.startswith("missing_role:hg.config_admin")


def test_embodied_control_requires_embodied_role():
    ident = _identity(["hg.approver"])
    v = evaluate_step_up(action_class="embodied_control", decision="approve",
                         identity=ident, now=NOW)
    assert not v.allowed and "missing_role" in v.reason
    ident2 = _identity(["hg.embodied_operator", "hg.approver"],
                       step_up=True, evidence=("amr:webauthn",))
    v2 = evaluate_step_up(action_class="embodied_control", decision="approve",
                          identity=ident2, now=NOW)
    assert v2.allowed


def test_service_cannot_approve_and_unknown_class_fails_closed():
    ident = _identity([])  # no roles at all
    assert not can_approve_as_human(ident.roles)
    v = evaluate_step_up(action_class="promotion", decision="approve",
                         identity=ident, now=NOW)
    assert not v.allowed and v.reason == "not_a_human_approver"
    v2 = evaluate_step_up(action_class="not_a_class", decision="approve",
                          identity=_identity(["hg.approver"]), now=NOW)
    assert not v2.allowed and v2.reason == "unknown_action_class"
