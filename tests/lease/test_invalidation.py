"""Event-driven invalidation: suspend-first, resume, obligations, races."""

import itertools

import pytest

from hg_gpp.engine import PermitAuthority
from hg_lease.compiler import compile_draft
from hg_lease.evaluator import ActionRequest, OUTCOME_ALLOW, OUTCOME_DENY
from hg_lease.gpp_bridge import LeaseAuthority, OperatorConfirmation
from hg_lease.invalidation import ObligationDue, SituationInvalidator
from hg_lease.stores import LeaseStore, ReceiptStore, SituationFact, SituationStore

NOW = "2026-07-17T12:00:00.000000Z"
_req_counter = itertools.count()


class FakeClock:
    def __init__(self):
        self.tick = 0

    def __call__(self):
        self.tick += 1
        return f"2026-07-17T12:00:{min(self.tick, 59):02d}.000000Z", 100.0 + self.tick


def draft():
    return dict(
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
        close_obligations=[
            {"action": "close_window", "trigger_fact": "someone_home", "trigger_value": False},
        ],
    )


def request():
    return ActionRequest(
        request_id=f"req_inv_{next(_req_counter)}",
        subject="agent:zero",
        action_type="open_window",
        object_id="window:kitchen_west",
        purpose="ventilation",
        requested_at=NOW,
        parameters={},
    )


@pytest.fixture
def rig():
    clock = FakeClock()
    situation = SituationStore()
    lease_store = LeaseStore()
    obligations: list[ObligationDue] = []
    authority = LeaseAuthority(
        permit_authority=PermitAuthority(clock=lambda: "2026-06-12T12:00:00.000000Z"),
        lease_store=lease_store,
        receipt_store=ReceiptStore(),
        situation_store=situation,
        capability_ref="cap.oea_stub_log",
        effect_class="audit_log",
        authority_chain_ref="dec_allow_stub",
        admission_ref="adm:token_fixture_valid",
        retention_ref="ret:bundle_fixture_1",
        agent_id="agent:fixture",
        clock=clock,
    )
    SituationInvalidator(
        authority=authority,
        lease_store=lease_store,
        situation_store=situation,
        clock=clock,
        obligation_sink=obligations.append,
    )
    situation.put(SituationFact(name="raining", typed_value=False, observed_at=NOW, source_id="sim"))
    situation.put(SituationFact(name="someone_home", typed_value=True, observed_at=NOW, source_id="sim"))
    policy = compile_draft(draft(), issuer_operator_id="op:local")
    lease = authority.mint_lease(
        policy,
        OperatorConfirmation(
            operator_id="op:local",
            policy_hash=policy.canonical_policy_hash,
            confirmed_at=NOW,
            display_summary_shown=policy.display_summary,
        ),
    )
    return authority, lease_store, situation, lease, obligations


def test_condition_violating_fact_change_suspends(rig):
    authority, lease_store, situation, lease, _ = rig
    situation.put(SituationFact(name="raining", typed_value=True, observed_at=NOW, source_id="sim"))
    assert lease_store.get(lease.lease_id).state == "SUSPENDED"
    assert authority.authorize(request()).decision.outcome == OUTCOME_DENY


def test_fact_recovery_resumes(rig):
    authority, lease_store, situation, lease, _ = rig
    situation.put(SituationFact(name="raining", typed_value=True, observed_at=NOW, source_id="sim"))
    assert lease_store.get(lease.lease_id).state == "SUSPENDED"
    situation.put(SituationFact(name="raining", typed_value=False, observed_at=NOW, source_id="sim"))
    assert lease_store.get(lease.lease_id).state == "ACTIVE"
    assert authority.authorize(request()).decision.outcome == OUTCOME_ALLOW


def test_irrelevant_fact_change_does_not_suspend(rig):
    _, lease_store, situation, lease, _ = rig
    situation.put(SituationFact(name="hallway_light", typed_value=True, observed_at=NOW, source_id="sim"))
    assert lease_store.get(lease.lease_id).state == "ACTIVE"


def test_occupancy_change_emits_close_obligation(rig):
    _, lease_store, situation, lease, obligations = rig
    situation.put(SituationFact(name="someone_home", typed_value=False, observed_at=NOW, source_id="sim"))
    assert lease_store.get(lease.lease_id).state == "SUSPENDED"
    assert len(obligations) == 1
    due = obligations[0]
    assert due.lease_id == lease.lease_id
    assert due.obligation["action"] == "close_window"
    assert due.triggered_by_fact == "someone_home"


def test_fact_removal_by_expiry_fails_closed(rig):
    """A required fact going stale must not leave the lease usable."""
    authority, _, situation, _, _ = rig
    situation.put(SituationFact(
        name="raining", typed_value=False, observed_at=NOW,
        source_id="sim", expires_at="2026-07-17T12:00:01.000000Z",
    ))
    # Snapshot at any later wall clock excludes the stale fact -> deny.
    result = authority.authorize(request())
    assert result.decision.outcome == OUTCOME_DENY


def test_revocation_during_suspension_wins(rig):
    authority, lease_store, situation, lease, _ = rig
    situation.put(SituationFact(name="raining", typed_value=True, observed_at=NOW, source_id="sim"))
    authority.revoke_lease(lease.lease_id, revoker_ref="op:local")
    assert lease_store.get(lease.lease_id).state == "REVOKED"
    # Recovery of the fact must NOT resurrect a revoked lease.
    situation.put(SituationFact(name="raining", typed_value=False, observed_at=NOW, source_id="sim"))
    assert lease_store.get(lease.lease_id).state == "REVOKED"
    assert authority.authorize(request()).decision.outcome == OUTCOME_DENY
