"""Control cluster evaluation helper tests."""

from __future__ import annotations

from hg_core.control_cluster.evaluation import assert_advisory_result, resolve_risk_containment
from hg_core.control_cluster.errors import ADVISORY_CONTAINMENT_WAIVED_RSC, REFUSED_SAFETY_BYPASS


def test_resolve_risk_containment_active() -> None:
    result = resolve_risk_containment(
        risk="safety_bypass",
        risk_reason_map={"safety_bypass": REFUSED_SAFETY_BYPASS},
        waived_reason_code=ADVISORY_CONTAINMENT_WAIVED_RSC,
        payload={"posture_id": "rsc-1"},
        refuse_for_risk=lambda _: True,
    )
    assert result is not None
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_SAFETY_BYPASS
    assert_advisory_result(result)


def test_resolve_risk_containment_waived() -> None:
    result = resolve_risk_containment(
        risk="safety_bypass",
        risk_reason_map={"safety_bypass": REFUSED_SAFETY_BYPASS},
        waived_reason_code=ADVISORY_CONTAINMENT_WAIVED_RSC,
        payload={"posture_id": "rsc-waive"},
        refuse_for_risk=lambda _: False,
    )
    assert result is not None
    assert result["status"] == "recorded"
    assert result["reason_code"] == ADVISORY_CONTAINMENT_WAIVED_RSC
    assert result["containment_waived"] is True
    assert result["would_contain_reason_code"] == REFUSED_SAFETY_BYPASS
    assert_advisory_result(result)


def test_resolve_risk_containment_no_risk() -> None:
    assert (
        resolve_risk_containment(
            risk=None,
            risk_reason_map={"safety_bypass": REFUSED_SAFETY_BYPASS},
            waived_reason_code=ADVISORY_CONTAINMENT_WAIVED_RSC,
            payload={},
        )
        is None
    )
