"""Part B situational awareness module tests."""

from __future__ import annotations

from hg_runtime.exciton.alerts import build_alert_strip
from hg_runtime.exciton.away_digest import build_away_digest
from hg_runtime.exciton.chrono_expiry import deny_auto_approval_if_clock_uncertain
from hg_runtime.exciton.confirmation_policy import confirmation_for_control
from hg_runtime.exciton.data_freshness import assess_freshness
from hg_runtime.exciton.decision_timeline import build_decision_timeline
from hg_runtime.exciton.ui_state import UIViewState, describe_ui_state
from hg_runtime.exciton.verbatim_preview import build_verbatim_preview, verify_approved_hash
from hg_runtime.exciton.gate_helpers import scan_forbidden
from hg_runtime.bounded_soak.stop_panic_runtime import operator_semantics


def test_freshness_stale():
    f = assess_freshness(generated_at="2020-01-01T00:00:00+00:00")
    assert f["state"] in ("STALE", "CONTACT_LOST")
    assert f["approvals_disabled"]


def test_away_digest_no_pressure():
    d = build_away_digest()
    assert d["pressure_to_approve"] is False
    assert not scan_forbidden(d)


def test_alerts_no_approve():
    a = build_alert_strip(snapshot_generated_at="2020-01-01T00:00:00+00:00")
    assert a["pressure_to_approve"] is False


def test_timeline_human_summary():
    t = build_decision_timeline()
    assert isinstance(t, list)


def test_verbatim_hash_lock():
    p = build_verbatim_preview(action_type="social_post", body="hello world", surface="moltbook")
    assert p["approved_payload_hash"]
    assert verify_approved_hash(p, "hello world")
    assert not verify_approved_hash(p, "changed")


def test_risk_confirmation_forbidden():
    c = confirmation_for_control("APPROVE_ALL")
    assert c["level"] == "denied"


def test_chrono_denies_low_confidence():
    ok, reason = deny_auto_approval_if_clock_uncertain(0.1)
    assert not ok
    assert "UNTRUSTED_CLOCK" in reason


def test_ui_state_model():
    s = describe_ui_state(UIViewState.EMPTY)
    assert s["approvals_disabled"] is False
    s2 = describe_ui_state(UIViewState.STALE)
    assert s2["approvals_disabled"]


def test_stop_panic_semantics():
    sem = operator_semantics()
    assert "STOP" in sem and "PANIC" in sem
