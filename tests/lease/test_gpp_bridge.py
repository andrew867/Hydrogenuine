"""LeaseAuthority over GPP: minting, authorization, revocation, supersession.

Uses the real hg_gpp.PermitAuthority with registry-registered fixture refs —
no mocks. Proves that an ALLOW mints a real GovernedPermit and that lease
revocation revokes outstanding permits.
"""

import itertools

import pytest

from hg_gpp.engine import PermitAuthority
from hg_lease.compiler import compile_draft
from hg_lease.evaluator import ActionRequest, OUTCOME_ALLOW, OUTCOME_DENY
from hg_lease.gpp_bridge import (
    LeaseAuthority,
    LeaseAuthorityError,
    OperatorConfirmation,
)
from hg_lease.stores import LeaseStore, ReceiptStore, SituationFact, SituationStore

NOW_BASE = "2026-07-17T12:00:{s:02d}.000000Z"


class FakeClock:
    def __init__(self):
        self.tick = 0

    def __call__(self):
        self.tick += 1
        return NOW_BASE.format(s=min(self.tick, 59)), 100.0 + self.tick


def draft(**overrides):
    base = dict(
        subjects=["agent:zero"],
        actions=["open_window"],
        objects=["window:kitchen_west"],
        purpose="ventilation",
        risk_class="LOW",
        valid_from="2026-07-17T00:00:00.000000Z",
        valid_until="2026-07-24T00:00:00.000000Z",
        condition={
            "type": "all_of",
            "children": [
                {"type": "fact", "fact_name": "raining", "op": "eq", "value": False, "unit": None},
                {"type": "fact", "fact_name": "someone_home", "op": "eq", "value": True, "unit": None},
            ],
        },
        numeric_limits=[{"parameter": "opening", "max_value": 100.0, "unit": "mm"}],
    )
    base.update(overrides)
    return base


_req_counter = itertools.count()


def request(**overrides):
    base = dict(
        request_id=f"req_{next(_req_counter)}",
        subject="agent:zero",
        action_type="open_window",
        object_id="window:kitchen_west",
        purpose="ventilation",
        requested_at="2026-07-17T12:00:00.000000Z",
        parameters={"opening": {"value": 80, "unit": "mm"}},
    )
    base.update(overrides)
    return ActionRequest(**base)


@pytest.fixture
def rig():
    clock = FakeClock()
    situation = SituationStore()
    lease_store = LeaseStore()
    receipts = ReceiptStore()
    gpp = PermitAuthority(clock=lambda: "2026-06-12T12:00:00.000000Z")
    authority = LeaseAuthority(
        permit_authority=gpp,
        lease_store=lease_store,
        receipt_store=receipts,
        situation_store=situation,
        capability_ref="cap.oea_stub_log",
        effect_class="audit_log",
        authority_chain_ref="dec_allow_stub",
        admission_ref="adm:token_fixture_valid",
        retention_ref="ret:bundle_fixture_1",
        agent_id="agent:fixture",
        clock=clock,
    )
    now = "2026-07-17T12:00:00.000000Z"
    for name, value in (("raining", False), ("someone_home", True)):
        situation.put(SituationFact(name=name, typed_value=value,
                                    observed_at=now, source_id="sim:demo"))
    return authority, gpp, lease_store, receipts, situation


def mint(authority, policy):
    return authority.mint_lease(
        policy,
        OperatorConfirmation(
            operator_id=policy.issuer_operator_id,
            policy_hash=policy.canonical_policy_hash,
            confirmed_at="2026-07-17T12:00:00.000000Z",
            display_summary_shown=policy.display_summary,
        ),
    )


def test_mint_requires_exact_hash_confirmation(rig):
    authority, *_ = rig
    policy = compile_draft(draft(), issuer_operator_id="op:local")
    with pytest.raises(LeaseAuthorityError):
        authority.mint_lease(
            policy,
            OperatorConfirmation(
                operator_id="op:local",
                policy_hash="sha256:different",
                confirmed_at="now",
                display_summary_shown=policy.display_summary,
            ),
        )


def test_mint_requires_matching_summary_shown(rig):
    """The operator must confirm the summary they were actually shown."""
    authority, *_ = rig
    policy = compile_draft(draft(), issuer_operator_id="op:local")
    with pytest.raises(LeaseAuthorityError):
        authority.mint_lease(
            policy,
            OperatorConfirmation(
                operator_id="op:local",
                policy_hash=policy.canonical_policy_hash,
                confirmed_at="now",
                display_summary_shown="something friendlier",
            ),
        )


def test_context_alone_cannot_authorize(rig):
    """No lease minted -> deny, even though conversation 'remembered' consent."""
    authority, _, _, receipts, _ = rig
    result = authority.authorize(request())
    assert result.decision.outcome == OUTCOME_DENY
    assert result.permit_id is None
    assert receipts.verify_chain()


def test_allow_mints_real_gpp_permit_and_receipt(rig):
    authority, gpp, _, receipts, _ = rig
    policy = compile_draft(draft(), issuer_operator_id="op:local")
    mint(authority, policy)
    result = authority.authorize(request())
    assert result.decision.outcome == OUTCOME_ALLOW
    assert result.permit_id is not None
    permit = gpp.store.get(result.permit_id)
    assert permit is not None and permit.status == "granted"
    assert receipts.get(result.receipt_id) is not None
    assert receipts.verify_chain()


def test_denied_reuse_when_rain_starts(rig):
    authority, _, _, _, situation = rig
    policy = compile_draft(draft(), issuer_operator_id="op:local")
    mint(authority, policy)
    situation.put(SituationFact(name="raining", typed_value=True,
                                observed_at="2026-07-17T13:00:00.000000Z", source_id="sim:demo"))
    result = authority.authorize(request())
    assert result.decision.outcome == OUTCOME_DENY
    assert result.permit_id is None


def test_replay_of_same_request_id_denied(rig):
    authority, *_ = rig
    policy = compile_draft(draft(), issuer_operator_id="op:local")
    mint(authority, policy)
    req = request()
    first = authority.authorize(req)
    assert first.decision.outcome == OUTCOME_ALLOW
    second = authority.authorize(req)
    assert second.decision.outcome == OUTCOME_DENY
    assert "replay.duplicate_request" in second.decision.reason_codes


def test_restriction_hook_can_only_veto(rig):
    clock = FakeClock()
    situation = SituationStore()
    now = "2026-07-17T12:00:00.000000Z"
    for name, value in (("raining", False), ("someone_home", True)):
        situation.put(SituationFact(name=name, typed_value=value,
                                    observed_at=now, source_id="sim:demo"))
    vetoing = LeaseAuthority(
        permit_authority=PermitAuthority(clock=lambda: "2026-06-12T12:00:00.000000Z"),
        lease_store=LeaseStore(),
        receipt_store=ReceiptStore(),
        situation_store=situation,
        capability_ref="cap.oea_stub_log",
        effect_class="audit_log",
        authority_chain_ref="dec_allow_stub",
        admission_ref="adm:token_fixture_valid",
        retention_ref="ret:bundle_fixture_1",
        agent_id="agent:fixture",
        clock=clock,
        restriction_hooks=(lambda req, lease, dec: "aep.high_stress_veto",),
    )
    policy = compile_draft(draft(), issuer_operator_id="op:local")
    mint(vetoing, policy)
    result = vetoing.authorize(request())
    assert result.decision.outcome == OUTCOME_DENY
    assert "restriction.aep.high_stress_veto" in result.decision.reason_codes
    assert result.permit_id is None


def test_revoked_lease_stops_future_action_and_revokes_permits(rig):
    authority, gpp, lease_store, _, _ = rig
    policy = compile_draft(draft(), issuer_operator_id="op:local")
    lease = mint(authority, policy)
    allowed = authority.authorize(request())
    assert allowed.permit_id is not None

    authority.revoke_lease(lease.lease_id, revoker_ref="op:local")
    assert lease_store.get(lease.lease_id).state == "REVOKED"
    assert gpp.store.is_revoked(allowed.permit_id)

    denied = authority.authorize(request())
    assert denied.decision.outcome == OUTCOME_DENY


def test_supersession_deactivates_old_lease(rig):
    authority, _, lease_store, _, _ = rig
    old_policy = compile_draft(draft(), issuer_operator_id="op:local")
    old_lease = mint(authority, old_policy)
    new_policy = compile_draft(
        draft(numeric_limits=[{"parameter": "opening", "max_value": 50.0, "unit": "mm"}]),
        issuer_operator_id="op:local",
    )
    authority.mint_lease(
        new_policy,
        OperatorConfirmation(
            operator_id="op:local",
            policy_hash=new_policy.canonical_policy_hash,
            confirmed_at="now",
            display_summary_shown=new_policy.display_summary,
        ),
        supersedes_lease_id=old_lease.lease_id,
    )
    assert lease_store.get(old_lease.lease_id).state == "SUPERSEDED"
    wide = authority.authorize(request(parameters={"opening": {"value": 80, "unit": "mm"}}))
    assert wide.decision.outcome == OUTCOME_DENY  # old 100mm lease can't execute
    narrow = authority.authorize(request(parameters={"opening": {"value": 40, "unit": "mm"}}))
    assert narrow.decision.outcome == OUTCOME_ALLOW


def test_use_limit_exhaustion(rig):
    authority, _, lease_store, _, _ = rig
    policy = compile_draft(draft(use_limit=1), issuer_operator_id="op:local")
    lease = mint(authority, policy)
    first = authority.authorize(request())
    assert first.decision.outcome == OUTCOME_ALLOW
    assert lease_store.get(lease.lease_id).state == "EXHAUSTED"
    second = authority.authorize(request())
    assert second.decision.outcome == OUTCOME_DENY


def test_revoke_all(rig):
    authority, _, lease_store, _, _ = rig
    p1 = compile_draft(draft(), issuer_operator_id="op:local")
    p2 = compile_draft(draft(objects=["window:kitchen_east"]), issuer_operator_id="op:local")
    mint(authority, p1)
    mint(authority, p2)
    assert authority.revoke_all(revoker_ref="op:local") == 2
    assert all(l.state == "REVOKED" for l in lease_store.all())
