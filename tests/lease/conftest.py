"""Shared rig for lease tests: real GPP, real stores, deterministic clock."""

import itertools
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from hg_gpp.engine import PermitAuthority
from hg_lease.compiler import compile_draft
from hg_lease.evaluator import ActionRequest
from hg_lease.gpp_bridge import LeaseAuthority, OperatorConfirmation
from hg_lease.stores import LeaseStore, ReceiptStore, SituationFact, SituationStore

NOW = "2026-07-17T12:00:00.000000Z"
_counter = itertools.count()


class SharedClock:
    """Deterministic wall+monotonic clock shared by every component."""

    def __init__(self):
        self.tick = 0

    def __call__(self):
        self.tick += 1
        minute, second = divmod(min(self.tick, 3500), 60)
        return (
            f"2026-07-17T12:{minute:02d}:{second:02d}.000000Z",
            100.0 + self.tick,
        )

    def wall(self):
        return self()[0]


@pytest.fixture
def clock():
    return SharedClock()


@pytest.fixture
def situation():
    store = SituationStore()
    for name, value, unit in (
        ("raining", False, None),
        ("someone_home", True, None),
        ("alarm_armed", False, None),
        ("outdoor_temp_c", 24.0, "C"),
    ):
        store.put(SituationFact(name=name, typed_value=value, unit=unit,
                                observed_at=NOW, source_id="sim:demo"))
    return store


@pytest.fixture
def gpp(clock):
    return PermitAuthority(clock=clock.wall, permit_ttl_s=3600.0)


@pytest.fixture
def lease_store():
    return LeaseStore()


@pytest.fixture
def receipts():
    return ReceiptStore()


@pytest.fixture
def authority(clock, situation, gpp, lease_store, receipts):
    return LeaseAuthority(
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


def window_draft(**overrides):
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
                {"type": "time_window", "start": "09:00", "end": "18:00"},
                {"type": "fact", "fact_name": "outdoor_temp_c", "op": "gt", "value": 21.0, "unit": "C"},
                {"type": "fact", "fact_name": "raining", "op": "eq", "value": False, "unit": None},
                {"type": "fact", "fact_name": "alarm_armed", "op": "eq", "value": False, "unit": None},
                {"type": "fact", "fact_name": "someone_home", "op": "eq", "value": True, "unit": None},
            ],
        },
        numeric_limits=[{"parameter": "opening", "max_value": 100.0, "unit": "mm"}],
        close_obligations=[
            {"action": "close_window", "trigger_fact": "someone_home", "trigger_value": False},
        ],
    )
    base.update(overrides)
    return base


def mint(authority, policy, supersedes=None):
    return authority.mint_lease(
        policy,
        OperatorConfirmation(
            operator_id=policy.issuer_operator_id,
            policy_hash=policy.canonical_policy_hash,
            confirmed_at=NOW,
            display_summary_shown=policy.display_summary,
        ),
        supersedes_lease_id=supersedes,
    )


def mint_window_lease(authority, **draft_overrides):
    policy = compile_draft(window_draft(**draft_overrides), issuer_operator_id="op:local")
    return mint(authority, policy), policy


def make_request(**overrides):
    base = dict(
        request_id=f"req_shared_{next(_counter)}",
        subject="agent:zero",
        action_type="open_window",
        object_id="window:kitchen_west",
        purpose="ventilation",
        requested_at=NOW,
        parameters={"opening": {"value": 80, "unit": "mm"}},
    )
    base.update(overrides)
    return ActionRequest(**base)
