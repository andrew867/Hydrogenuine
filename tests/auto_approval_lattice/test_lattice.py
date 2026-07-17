"""Auto approval lattice tests."""

from hg_runtime.cloud_browser_governance.lattice import ApprovalDecisionEngine


def test_low_risk_auto_approve():
    e = ApprovalDecisionEngine()
    assert e.evaluate(action_id="social_draft")["decision"] == "AUTO_APPROVE"


def test_high_risk_full_stop():
    e = ApprovalDecisionEngine()
    assert e.evaluate(action_id="email_send_request")["decision"] == "FULL_STOP"
