"""SOAR sovereign arbitration runtime tests."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from hg_core.governance.canonical_hash import canonical_hash
from hg_soar import (
    DENIED_MISSING_ADMISSION,
    DENIED_MISSING_FRESHNESS,
    DENIED_MISSING_IDENTITY,
    DENIED_REDACTION_FAILURE,
    DENIED_STALE_APPROVAL,
    DENIED_UNKNOWN_DOMAIN,
    SoarEventLogAdapter,
    SoarRuntime,
    fixture_soar_request,
    verify_replay,
)
from hg_soar.collapse import build_collapse
from hg_soar.critique import apply_critique, binding_rank, weakened_binding
from hg_soar.domains import evaluate_all_domains
from hg_soar.d7 import arbitrate_d7
from hg_soar.validation import DENIED_DUPLICATE
from hg_soar.events import (
    SOAR_D7_COLLAPSE_RECORDED,
    SOAR_GPP_ROUTE_FIXTURE,
    SOAR_HAL_ROUTE_REQUESTED,
    SOAR_UEAK_ROUTE_FIXTURE,
)
from hg_soar.models import MonotoneCritiqueGuard, signal_from_evaluation
from hg_soar.types import D7Decision, DOMAIN_IDS


def _clock() -> str:
    return "2026-06-12T16:00:00.000000Z"


def _runtime() -> SoarRuntime:
    return SoarRuntime(log=SoarEventLogAdapter(), clock=_clock)


def _proposal_payload(**content_overrides) -> dict:
    content = {
        "proposal_id": "prop_soar_rt",
        "kind": "candidate_action",
        "capability_id": "cap.oea_stub_log",
        "effect_class": "audit_log",
        "action_type": "oea_stub_log",
    }
    content.update(content_overrides)
    return {
        "proposal_id": "prop_soar_rt",
        "kind": "candidate_action",
        "content": content,
    }


def test_d1_d6_advisory_signal_schema():
    proposal = {
        "event_id": "evt_1",
        "payload": _proposal_payload(),
    }
    evaluations = evaluate_all_domains(proposal=proposal, input_refs=("evt_1",))
    signals = [signal_from_evaluation(e) for e in evaluations]
    d1_d6 = [s for s in signals if s.domain_id != "D7"]
    assert len(d1_d6) == 6
    for signal in d1_d6:
        assert signal.advisory_only is True
        payload = signal.to_payload()
        assert payload["evaluation"]["schema"] == "soar-domain-evaluation"


def test_d7_collapse_positive_fixture():
    runtime = _runtime()
    decision, events = runtime.process(fixture_soar_request())
    assert decision.collapse is not None
    assert decision.binding == "ACCEPT"
    assert decision.collapse.to_payload()["execution_permission"] is False
    assert any(e.event_type == SOAR_D7_COLLAPSE_RECORDED for e in events)


def test_conflicting_domain_signals_preserved():
    runtime = _runtime()
    request = fixture_soar_request(
        proposal_payload=_proposal_payload(memory_stale=True),
        contradictions=("manual:conflict_ref",),
    )
    decision, _ = runtime.process(request)
    assert decision.collapse is not None
    assert len(decision.collapse.contradictions) >= 1


def test_critique_restrict_only():
    proposal = {"event_id": "evt", "payload": _proposal_payload()}
    evaluations = evaluate_all_domains(proposal=proposal, input_refs=())
    signals = tuple(signal_from_evaluation(e) for e in evaluations)
    primary = D7Decision(
        decision_id="d7_test",
        request_id="req",
        binding="ACCEPT",
        domain_evaluation_refs=tuple(s.evaluation.evaluation_id for s in signals),
        reason_code="test",
        hard_veto=True,
    )
    from hg_soar.critique import audit_d7

    critique = audit_d7(primary, evaluations=tuple(s.evaluation for s in signals))
    assert apply_critique(primary, critique) == "DEFER"
    assert binding_rank(weakened_binding(primary, critique)) <= binding_rank(primary.binding)


def test_no_d1_d6_self_authorize():
    proposal = {"event_id": "evt", "payload": _proposal_payload()}
    signals = tuple(signal_from_evaluation(e) for e in evaluate_all_domains(proposal=proposal, input_refs=()))
    for signal in signals:
        if signal.domain_id != "D7":
            assert signal.advisory_only
            assert "permit" not in signal.evaluation.verdict.lower()


def test_no_d7_execution_permission():
    runtime = _runtime()
    decision, _ = runtime.process(fixture_soar_request())
    payload = decision.to_payload()
    assert payload["execution_approved"] is False
    assert payload["permit_minted"] is False
    assert decision.collapse is not None
    assert decision.collapse.to_payload()["execution_permission"] is False


def test_route_to_hal_gpp_ueak_only():
    runtime = _runtime()
    decision, events = runtime.process(fixture_soar_request())
    assert decision.binding == "ACCEPT"
    targets = {r.target for r in decision.routes}
    assert targets == {"HAL", "GPP", "UEAK"}
    assert all(r.fixture_only for r in decision.routes)
    event_types = {e.event_type for e in events}
    assert SOAR_HAL_ROUTE_REQUESTED in event_types
    assert SOAR_GPP_ROUTE_FIXTURE in event_types
    assert SOAR_UEAK_ROUTE_FIXTURE in event_types


def test_deny_stale_approval_fail_closed():
    runtime = _runtime()
    decision, _ = runtime.process(
        fixture_soar_request(approval_expires_at="2020-01-01T00:00:00.000000Z")
    )
    assert decision.decision_state == "fail_closed"
    assert any(r.code == DENIED_STALE_APPROVAL for r in decision.reasons)


def test_deny_redaction_failure():
    runtime = _runtime()
    decision, _ = runtime.process(fixture_soar_request(redaction_ref="sec:redaction_failed"))
    assert decision.decision_state == "fail_closed"
    assert any(r.code == DENIED_REDACTION_FAILURE for r in decision.reasons)


def test_deny_model_identity_cannot_authorize():
    runtime = _runtime()
    decision, _ = runtime.process(fixture_soar_request(identity_ref="model:cognition_proposal"))
    assert decision.decision_state == "fail_closed"
    assert any(r.code == DENIED_MISSING_IDENTITY for r in decision.reasons)


def test_deny_duplicate_idempotency_key():
    runtime = _runtime()
    req = fixture_soar_request(request_id="dup_req", idempotency_key="idem-dup-key")
    first, _ = runtime.process(req)
    assert first.decision_state != "fail_closed"
    second, _ = runtime.process(req)
    assert second.decision_state == "fail_closed"
    assert any(r.code == DENIED_DUPLICATE for r in second.reasons)


def test_deny_missing_identity():
    runtime = _runtime()
    decision, _ = runtime.process(fixture_soar_request(identity_ref="placeholder"))
    assert decision.decision_state == "fail_closed"
    assert any(r.code == DENIED_MISSING_IDENTITY for r in decision.reasons)


def test_deny_missing_admission():
    runtime = _runtime()
    decision, _ = runtime.process(fixture_soar_request(admission_ref="adm:missing"))
    assert decision.decision_state == "fail_closed"
    assert any(r.code == DENIED_MISSING_ADMISSION for r in decision.reasons)


def test_deny_missing_freshness():
    runtime = _runtime()
    decision, _ = runtime.process(fixture_soar_request(freshness_ref="tim:missing"))
    assert decision.decision_state == "fail_closed"
    assert any(r.code == DENIED_MISSING_FRESHNESS for r in decision.reasons)


def test_unknown_domain_fail_closed():
    runtime = _runtime()
    decision, _ = runtime.process(fixture_soar_request(known_domains=("D1", "D2")))
    assert decision.decision_state == "fail_closed"
    assert any(r.code == DENIED_UNKNOWN_DOMAIN for r in decision.reasons)


def test_replay_determinism():
    r1 = _runtime()
    r2 = _runtime()
    req = fixture_soar_request(request_id="soar_det")
    d1, _ = r1.process(req)
    d2, _ = r2.process(req)
    assert d1.decision_hash == d2.decision_hash
    ok, reason = verify_replay(r1.log, expected_state=r1.state)
    assert ok, reason


def test_receipt_hashing():
    runtime = _runtime()
    decision, _ = runtime.process(fixture_soar_request())
    expected = canonical_hash(decision.to_payload(include_hash=False))
    assert decision.decision_hash == expected


def test_no_oea_ter_in_runtime_modules():
    forbidden = ("hg_oea", "hg_ter", "import requests", "import httpx", "subprocess.", "mint_permit")
    runtime_modules = (
        "runtime.py",
        "validation.py",
        "collapse.py",
        "models.py",
        "event_log.py",
        "reducer.py",
        "replay.py",
    )
    for name in runtime_modules:
        text = (Path("hg_soar") / name).read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{name} must not reference {token}"


def test_no_gpp_permit_mint_from_soar():
    runtime = _runtime()
    runtime.process(fixture_soar_request())
    assert runtime.permit_mint_log == []
    payload = runtime.log.events[-3].payload if runtime.log.events else {}
    for event in runtime.log.events:
        if event.event_type == SOAR_GPP_ROUTE_FIXTURE:
            assert event.payload.get("permit_mint") is False


def test_no_ueak_execution_approval_from_soar():
    runtime = _runtime()
    decision, events = runtime.process(fixture_soar_request())
    assert decision.to_payload()["execution_approved"] is False
    ueak_events = [e for e in events if e.event_type == SOAR_UEAK_ROUTE_FIXTURE]
    assert ueak_events and ueak_events[0].payload.get("execution_approved") is False


def test_monotone_critique_guard_blocks_expansion():
    guard = MonotoneCritiqueGuard()
    primary = D7Decision(
        decision_id="d7_guard",
        request_id="req",
        binding="DEFER",
        domain_evaluation_refs=(),
        reason_code="test",
    )
    from hg_soar.types import D7Critique

    critique = D7Critique(
        critique_id="crit",
        primary_decision_id="d7_guard",
        verdict="AFFIRM",
        reason_code=None,
        checks=(),
    )
    assert guard.apply(primary, critique) == "DEFER"


def test_hard_veto_reject_route():
    runtime = _runtime()
    decision, _ = runtime.process(
        fixture_soar_request(proposal_payload=_proposal_payload(hard_veto=True))
    )
    assert decision.binding == "REJECT"
    assert decision.decision_state == "sovereign_refusal"
    assert all(r.target != "HAL" for r in decision.routes)


def test_all_seven_domains_in_registry():
    from hg_soar import domain_registry

    ids = {d.domain_id for d in domain_registry()}
    assert ids == set(DOMAIN_IDS)
