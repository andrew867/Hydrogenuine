"""SYNTHETIC scientific-apparatus capability lease demo (D03).

A fully synthetic spectrometer with one low-risk calibration action. The
lease is tied to instrument identity, calibration state, protocol hash,
operator, time window, maximum actuation, and safety interlock state.
Changing the protocol (or specimen) changes the protocol hash fact and
invalidates reuse.

Run:  python -m hg_lease.demos.instrument_demo
"""

from __future__ import annotations

import json
from typing import Any

from hg_core.governance.canonical_hash import canonical_hash
from hg_gpp.engine import PermitAuthority

from hg_lease.adapters import AdapterRegistry, SimulatedInstrumentAdapter
from hg_lease.compiler import compile_draft
from hg_lease.demos.window_demo import DemoClock
from hg_lease.evaluator import ActionRequest
from hg_lease.gpp_bridge import LeaseAuthority, OperatorConfirmation
from hg_lease.invalidation import SituationInvalidator
from hg_lease.oea_crossing import LeaseCrossing
from hg_lease.stores import LeaseStore, ReceiptStore, SituationFact, SituationStore

INSTRUMENT = "instrument:synth_spectrometer_1"
PROTOCOL_A = {"protocol": "baseline_calibration", "specimen": "reference_cell_A", "version": 3}
PROTOCOL_B = {"protocol": "baseline_calibration", "specimen": "sample_cell_B", "version": 3}


def protocol_hash(protocol: dict[str, Any]) -> str:
    return canonical_hash(protocol)


def calibration_draft() -> dict[str, Any]:
    return {
        "subjects": ["op:local"],
        "actions": ["calibrate_offset"],
        "objects": [INSTRUMENT],
        "purpose": "drift compensation during synthetic soak",
        "risk_class": "LOW",
        "renewal_mode": "MANUAL",
        "unknown_fact_policy": "DENY",
        "valid_from": "2026-07-17T09:00:00.000000Z",
        "valid_until": "2026-07-17T17:00:00.000000Z",
        "condition": {
            "type": "all_of",
            "children": [
                {"type": "time_window", "start": "09:00", "end": "17:00"},
                {"type": "fact", "fact_name": "instrument_id", "op": "eq",
                 "value": INSTRUMENT, "unit": None},
                {"type": "fact", "fact_name": "calibration_state", "op": "eq",
                 "value": "warmed_up", "unit": None},
                {"type": "fact", "fact_name": "protocol_hash", "op": "eq",
                 "value": protocol_hash(PROTOCOL_A), "unit": None},
                {"type": "fact", "fact_name": "interlock_closed", "op": "eq",
                 "value": True, "unit": None},
            ],
        },
        "numeric_limits": [{"parameter": "actuation", "max_value": 25.0,
                            "min_value": -25.0, "unit": "um"}],
        "use_limit": 10,
        "source_conversation_refs": ["conv:demo_instrument_1"],
    }


def run_instrument_demo() -> dict[str, Any]:
    clock = DemoClock(wall="2026-07-17T09:15:00.000000Z")
    situation = SituationStore()
    lease_store = LeaseStore()
    receipts = ReceiptStore()
    gpp = PermitAuthority(clock=clock.wall, permit_ttl_s=3600.0)
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
        agent_id="agent:lab_assistant",
        clock=clock,
    )
    instrument = SimulatedInstrumentAdapter(
        instrument_id=INSTRUMENT, max_actuation_um=50.0
    )
    registry = AdapterRegistry()
    registry.register(instrument)
    crossing = LeaseCrossing(
        authority=authority, permit_authority=gpp, registry=registry,
        receipt_store=receipts, capability_ref="cap.oea_stub_log",
        effect_class="audit_log", clock=clock,
    )

    SituationInvalidator(
        authority=authority, lease_store=lease_store,
        situation_store=situation, clock=clock,
    )

    transcript: list[dict[str, Any]] = []
    counter = [0]

    def note(beat: str, **payload: Any) -> None:
        transcript.append({"beat": beat, "provenance": "SYNTHETIC", **payload})

    def put_fact(name: str, value: Any) -> None:
        situation.put(SituationFact(
            name=name, typed_value=value, observed_at=clock.wall_time,
            source_id="sim:lab_state",
        ))

    def ask(actuation_um: float = 5.0, subject: str = "op:local"):
        counter[0] += 1
        return crossing.request_action(ActionRequest(
            request_id=f"cal_req_{counter[0]}",
            subject=subject,
            action_type="calibrate_offset",
            object_id=INSTRUMENT,
            purpose="drift compensation during synthetic soak",
            requested_at=clock.wall_time,
            parameters={"actuation": {"value": actuation_um, "unit": "um"}},
        ))

    put_fact("instrument_id", INSTRUMENT)
    put_fact("calibration_state", "warmed_up")
    put_fact("protocol_hash", protocol_hash(PROTOCOL_A))
    put_fact("interlock_closed", True)

    policy = compile_draft(calibration_draft(), issuer_operator_id="op:local")
    lease = authority.mint_lease(policy, OperatorConfirmation(
        operator_id="op:local",
        policy_hash=policy.canonical_policy_hash,
        confirmed_at=clock.wall_time,
        display_summary_shown=policy.display_summary,
    ))
    note("lease_bindings",
         lease_id=lease.lease_id,
         bound_instrument=INSTRUMENT,
         bound_calibration_state="warmed_up",
         bound_protocol_hash=protocol_hash(PROTOCOL_A),
         bound_operator="op:local",
         time_window="09:00-17:00",
         max_actuation_um=25.0,
         interlock_required=True,
         use_limit=10)

    allowed = ask(actuation_um=5.0)
    note("calibration_allowed", outcome=allowed.outcome,
         offset_um=instrument.offset_um, receipt_id=allowed.receipt_id)

    over = ask(actuation_um=40.0)
    note("actuation_over_lease_limit_denied", outcome=over.outcome,
         reason_codes=list(over.reason_codes))

    wrong_operator = ask(subject="op:intern_2")
    note("different_operator_denied", outcome=wrong_operator.outcome,
         reason_codes=list(wrong_operator.reason_codes))

    put_fact("interlock_closed", False)
    interlock_open = ask()
    note("interlock_open_denied", outcome=interlock_open.outcome,
         reason_codes=list(interlock_open.reason_codes))
    put_fact("interlock_closed", True)

    put_fact("calibration_state", "cooling_down")
    wrong_state = ask()
    note("calibration_state_changed_denied", outcome=wrong_state.outcome,
         reason_codes=list(wrong_state.reason_codes))
    put_fact("calibration_state", "warmed_up")

    # Protocol/specimen change invalidates reuse.
    put_fact("protocol_hash", protocol_hash(PROTOCOL_B))
    changed_protocol = ask()
    note("protocol_change_invalidates_reuse",
         outcome=changed_protocol.outcome,
         old_protocol_hash=protocol_hash(PROTOCOL_A),
         new_protocol_hash=protocol_hash(PROTOCOL_B),
         reason_codes=list(changed_protocol.reason_codes),
         lease_state=lease_store.get(lease.lease_id).state)

    put_fact("protocol_hash", protocol_hash(PROTOCOL_A))
    recovered = ask(actuation_um=-3.0)
    note("original_protocol_recovers", outcome=recovered.outcome,
         offset_um=instrument.offset_um)

    note("receipts", chain_valid=receipts.verify_chain(),
         receipt_count=len(receipts.all()),
         outcomes=sorted({r["outcome"] for r in receipts.all()}))

    return {
        "demo": "synthetic_instrument_calibration_lease",
        "provenance": "SYNTHETIC — no real laboratory instrument exists or was controlled",
        "transcript": transcript,
    }


def main() -> int:
    print(json.dumps(run_instrument_demo(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
