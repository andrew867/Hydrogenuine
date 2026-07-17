"""SIMULATED west-kitchen-window capability lease demo (D02).

Policy under demonstration:

    For the next week, you may open the west kitchen window up to 100 mm
    between 09:00 and 18:00 when the outdoor temperature is above 21 C, it
    is not raining, the alarm is off, and someone is home. Close it before
    evening or when the home becomes unoccupied.

Every beat required by the programme is exercised and recorded in a
deterministic transcript: draft, confirmation, reuse without re-asking,
rain denial, alarm denial, different-window denial, wider-opening denial,
occupancy closure, expiry, conversational renewal with a changed condition,
explicit revocation, and receipts for actions and refusals.

Run:  python -m hg_lease.demos.window_demo
"""

from __future__ import annotations

import json
from typing import Any, Optional

from hg_gpp.engine import PermitAuthority

from hg_lease.adapters import AdapterRegistry, SimulatedWindowAdapter
from hg_lease.compiler import compile_draft
from hg_lease.evaluator import ActionRequest
from hg_lease.gpp_bridge import LeaseAuthority, OperatorConfirmation
from hg_lease.invalidation import ObligationDue, SituationInvalidator
from hg_lease.oea_crossing import LeaseCrossing
from hg_lease.operator import LeaseDashboard
from hg_lease.stores import LeaseStore, ReceiptStore, SituationFact, SituationStore


class DemoClock:
    """Deterministic, script-controlled wall + monotonic clock."""

    def __init__(self, wall: str = "2026-07-17T09:30:00.000000Z", mono: float = 1000.0):
        self.wall_time = wall
        self.mono_time = mono

    def advance_to(self, wall: str, mono_step: float = 60.0) -> None:
        self.wall_time = wall
        self.mono_time += mono_step

    def __call__(self):
        self.mono_time += 0.001
        return self.wall_time, self.mono_time

    def wall(self):
        return self.wall_time


WINDOW = "window:kitchen_west"
POLICY_TEXT = (
    "For the next week, you may open the west kitchen window up to 100 mm "
    "between 09:00 and 18:00 when the outdoor temperature is above 21 C, it "
    "is not raining, the alarm is off, and someone is home. Close it before "
    "evening or when the home becomes unoccupied."
)


def structured_draft() -> dict[str, Any]:
    """The structured draft a conversation layer would produce from
    POLICY_TEXT. Static here so the demo has no model dependency."""
    return {
        "subjects": ["agent:zero"],
        "actions": ["open_window"],
        "objects": [WINDOW],
        "purpose": "ventilation",
        "risk_class": "LOW",
        "renewal_mode": "PROMPT_BEFORE_EXPIRY",
        "unknown_fact_policy": "DENY",
        "valid_from": "2026-07-17T00:00:00.000000Z",
        "valid_until": "2026-07-24T00:00:00.000000Z",
        "condition": {
            "type": "all_of",
            "children": [
                {"type": "time_window", "start": "09:00", "end": "18:00"},
                {"type": "fact", "fact_name": "outdoor_temp_c", "op": "gt", "value": 21.0, "unit": "C"},
                {"type": "fact", "fact_name": "raining", "op": "eq", "value": False, "unit": None},
                {"type": "fact", "fact_name": "alarm_armed", "op": "eq", "value": False, "unit": None},
                {"type": "fact", "fact_name": "someone_home", "op": "eq", "value": True, "unit": None},
            ],
        },
        "numeric_limits": [{"parameter": "opening", "max_value": 100.0, "unit": "mm"}],
        "close_obligations": [
            {"action": "close_window", "trigger_fact": "someone_home", "trigger_value": False},
            {"action": "close_window", "trigger_fact": "evening", "trigger_value": True},
        ],
        "source_conversation_refs": ["conv:demo_window_1"],
    }


def run_window_demo() -> dict[str, Any]:
    clock = DemoClock()
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
        agent_id="agent:zero",
        clock=clock,
    )
    window = SimulatedWindowAdapter(device_ids=(WINDOW,))
    registry = AdapterRegistry()
    registry.register(window)
    crossing = LeaseCrossing(
        authority=authority, permit_authority=gpp, registry=registry,
        receipt_store=receipts, capability_ref="cap.oea_stub_log",
        effect_class="audit_log", clock=clock,
    )
    dashboard = LeaseDashboard(
        authority=authority, lease_store=lease_store, receipt_store=receipts
    )
    obligations: list[ObligationDue] = []
    SituationInvalidator(
        authority=authority, lease_store=lease_store,
        situation_store=situation, clock=clock,
        obligation_sink=obligations.append,
    )

    transcript: list[dict[str, Any]] = []
    request_counter = [0]

    def note(beat: str, **payload: Any) -> None:
        transcript.append({"beat": beat, "provenance": "SIMULATED", **payload})

    def put_fact(name: str, value: Any, unit: Optional[str] = None) -> None:
        situation.put(SituationFact(
            name=name, typed_value=value, unit=unit,
            observed_at=clock.wall_time, source_id="sim:home_sensors",
        ))

    def ask(action: str = "open_window", obj: str = WINDOW, opening_mm: float = 60.0):
        request_counter[0] += 1
        return crossing.request_action(ActionRequest(
            request_id=f"demo_req_{request_counter[0]}",
            subject="agent:zero",
            action_type=action,
            object_id=obj,
            purpose="ventilation",
            requested_at=clock.wall_time,
            parameters={"opening": {"value": opening_mm, "unit": "mm"}}
            if action == "open_window" else {},
        ))

    # World starts sunny, warm, disarmed, occupied.
    for name, value, unit in (
        ("outdoor_temp_c", 24.5, "C"),
        ("raining", False, None),
        ("alarm_armed", False, None),
        ("someone_home", True, None),
        ("evening", False, None),
    ):
        put_fact(name, value, unit)

    # 1. Initial policy draft.
    draft = structured_draft()
    policy = compile_draft(draft, issuer_operator_id="op:local")
    note("policy_draft",
         operator_utterance=POLICY_TEXT,
         canonical_hash=policy.canonical_policy_hash,
         display_summary=policy.display_summary)

    # 2. Operator confirmation (exact hash + summary echo).
    lease = authority.mint_lease(policy, OperatorConfirmation(
        operator_id="op:local",
        policy_hash=policy.canonical_policy_hash,
        confirmed_at=clock.wall_time,
        display_summary_shown=policy.display_summary,
    ))
    note("operator_confirmation", lease_id=lease.lease_id, state="ACTIVE")

    # 3. Permitted reuse without repetitive confirmation (three actions).
    for step in range(3):
        clock.advance_to(f"2026-07-17T{10 + step}:00:00.000000Z")
        result = ask(opening_mm=60.0 + 10 * step)
        note("permitted_reuse", attempt=step + 1, outcome=result.outcome,
             receipt_id=result.receipt_id, permit_id=result.permit_id,
             window_position_mm=window.positions_mm[WINDOW])

    # 4. Denial when rain begins.
    put_fact("raining", True)
    result = ask()
    note("denied_rain", outcome=result.outcome,
         reason_codes=list(result.reason_codes), receipt_id=result.receipt_id)
    put_fact("raining", False)  # rain passes; lease resumes

    # 5. Denial when the alarm arms.
    put_fact("alarm_armed", True)
    result = ask()
    note("denied_alarm", outcome=result.outcome,
         reason_codes=list(result.reason_codes), receipt_id=result.receipt_id)
    put_fact("alarm_armed", False)

    # 6. Denial for a different window.
    result = ask(obj="window:bedroom")
    note("denied_other_window", outcome=result.outcome,
         reason_codes=list(result.reason_codes), receipt_id=result.receipt_id)

    # 7. Denial for a wider opening.
    result = ask(opening_mm=150.0)
    note("denied_wider_opening", outcome=result.outcome,
         reason_codes=list(result.reason_codes), receipt_id=result.receipt_id)

    # 8. Closure when occupancy changes (close obligation honoured).
    put_fact("someone_home", False)
    due = [o for o in obligations if o.obligation.get("trigger_fact") == "someone_home"]
    closed = window.perform(device_id=WINDOW, action_type="close_window", parameters={})
    note("closure_on_unoccupied",
         obligation_emitted=bool(due),
         lease_state=lease_store.get(lease.lease_id).state,
         window_position_mm=window.positions_mm[WINDOW],
         adapter=closed.to_payload())
    put_fact("someone_home", True)

    # 9. Expiry after the week.
    clock.advance_to("2026-07-25T10:00:00.000000Z")
    result = ask()
    authority.expire_lease(lease.lease_id)
    note("expiry", outcome=result.outcome,
         reason_codes=list(result.reason_codes),
         lease_state=lease_store.get(lease.lease_id).state)

    # 10. Conversational renewal with a changed condition (warmer threshold).
    renewal_draft = dashboard.renewal_draft(lease.lease_id, changes={
        "valid_from": "2026-07-25T00:00:00.000000Z",
        "valid_until": "2026-08-01T00:00:00.000000Z",
        "condition": {
            "type": "all_of",
            "children": [
                {"type": "time_window", "start": "09:00", "end": "18:00"},
                {"type": "fact", "fact_name": "outdoor_temp_c", "op": "gt", "value": 23.0, "unit": "C"},
                {"type": "fact", "fact_name": "raining", "op": "eq", "value": False, "unit": None},
                {"type": "fact", "fact_name": "alarm_armed", "op": "eq", "value": False, "unit": None},
                {"type": "fact", "fact_name": "someone_home", "op": "eq", "value": True, "unit": None},
            ],
        },
    })
    renewed_policy = compile_draft(renewal_draft, issuer_operator_id="op:local")
    renewed = authority.mint_lease(
        renewed_policy,
        OperatorConfirmation(
            operator_id="op:local",
            policy_hash=renewed_policy.canonical_policy_hash,
            confirmed_at=clock.wall_time,
            display_summary_shown=renewed_policy.display_summary,
        ),
        supersedes_lease_id=lease.lease_id,
    )
    put_fact("outdoor_temp_c", 22.0, "C")  # warm by old policy, cool by new
    denied_cool = ask()
    put_fact("outdoor_temp_c", 24.5, "C")
    allowed_warm = ask()
    note("renewal_with_changed_condition",
         renewed_lease_id=renewed.lease_id,
         old_threshold_c=21.0, new_threshold_c=23.0,
         denied_at_22c=denied_cool.outcome,
         allowed_at_24_5c=allowed_warm.outcome)

    # 11. Explicit revocation.
    dashboard.revoke(renewed.lease_id, operator_id="op:local")
    result = ask()
    note("explicit_revocation",
         lease_state=lease_store.get(renewed.lease_id).state,
         outcome_after_revocation=result.outcome,
         receipt_id=result.receipt_id)

    # 12. Receipts for actions and refusals.
    all_receipts = receipts.all()
    note("receipts",
         chain_valid=receipts.verify_chain(),
         receipt_count=len(all_receipts),
         outcomes=sorted({r["outcome"] for r in all_receipts}),
         saturation=dashboard.saturation_report().__dict__)

    return {
        "demo": "west_kitchen_window_capability_lease",
        "provenance": "SIMULATED — no real window, sensor, or alarm was involved",
        "policy_text": POLICY_TEXT,
        "transcript": transcript,
    }


def main() -> int:
    print(json.dumps(run_window_demo(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
