"""End-to-end advisory marker wiring for Batch C6-A."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from hg_core.control_cluster.evaluation import assert_advisory_result
from hg_runtime.goal_commitment_boundary.boundary import (
    evaluate_goal_commitment,
    evaluate_goal_fit,
)
from hg_runtime.goal_commitment_boundary.types import (
    FIXTURE_CLOCK,
    goal_commitment_from_fixture,
    goal_fit_from_fixture,
)
from hg_runtime.mission_drift_boundary.boundary import (
    evaluate_drift_observation,
    evaluate_refresh_request,
)
from hg_runtime.mission_drift_boundary.types import (
    drift_observation_from_fixture,
    refresh_request_from_fixture,
)
from hg_runtime.priority_allocation_boundary.boundary import (
    evaluate_priority_assessment,
    evaluate_priority_signal,
)
from hg_runtime.priority_allocation_boundary.types import (
    priority_assessment_from_fixture,
    priority_signal_from_fixture,
)
from hg_runtime.resource_scarcity_controller.controller import (
    evaluate_overrun_risk,
    evaluate_resource_posture,
)
from hg_runtime.resource_scarcity_controller.types import posture_from_fixture, risk_from_fixture
from hg_runtime.risk_posture_boundary.controller import (
    evaluate_drive_signal,
    evaluate_operating_posture,
    evaluate_risk_posture,
)
from hg_runtime.risk_posture_boundary.types import (
    drive_signal_from_fixture,
    operating_posture_from_fixture,
    risk_posture_assessment_from_fixture,
)
from hg_runtime.trust_boundary_calibration.controller import (
    evaluate_reliance_boundary,
    evaluate_trust_calibration,
)
from hg_runtime.trust_boundary_calibration.types import (
    calibration_from_fixture,
    reliance_boundary_from_fixture,
)


@pytest.mark.parametrize(
    ("evaluator", "args", "kwargs"),
    [
        (
            evaluate_resource_posture,
            (posture_from_fixture({"posture_id": "wire-rsc"}),),
            {"observed_at": FIXTURE_CLOCK},
        ),
        (
            evaluate_overrun_risk,
            (risk_from_fixture({"risk_id": "wire-rsc-risk"}),),
            {},
        ),
        (
            evaluate_priority_signal,
            (priority_signal_from_fixture({"priority_signal_id": "wire-pab"}),),
            {"observed_at": FIXTURE_CLOCK},
        ),
        (
            evaluate_priority_assessment,
            (priority_assessment_from_fixture({"assessment_id": "wire-pab-assess"}),),
            {},
        ),
        (
            evaluate_drift_observation,
            (drift_observation_from_fixture({"drift_id": "wire-mis"}),),
            {"observed_at": FIXTURE_CLOCK},
        ),
        (
            evaluate_refresh_request,
            (refresh_request_from_fixture({"request_id": "wire-mis-refresh"}),),
            {},
        ),
        (
            evaluate_goal_commitment,
            (goal_commitment_from_fixture({"goal_commitment_id": "wire-gcb"}),),
            {"observed_at": FIXTURE_CLOCK},
        ),
        (
            evaluate_goal_fit,
            (goal_fit_from_fixture({"assessment_id": "wire-gcb-fit"}),),
            {"observed_at": FIXTURE_CLOCK},
        ),
        (
            evaluate_trust_calibration,
            (calibration_from_fixture({"calibration_id": "wire-trb"}),),
            {"observed_at": FIXTURE_CLOCK},
        ),
        (
            evaluate_reliance_boundary,
            (reliance_boundary_from_fixture({"boundary_id": "wire-trb-bound"}),),
            {},
        ),
        (
            evaluate_drive_signal,
            (drive_signal_from_fixture({"drive_signal_id": "wire-rpb-drive"}),),
            {},
        ),
        (
            evaluate_operating_posture,
            (operating_posture_from_fixture({"posture_id": "wire-rpb-posture"}),),
            {"observed_at": FIXTURE_CLOCK},
        ),
        (
            evaluate_risk_posture,
            (risk_posture_assessment_from_fixture({"assessment_id": "wire-rpb-assess"}),),
            {},
        ),
    ],
)
def test_control_evaluators_always_advisory_only(
    evaluator: Callable[..., dict[str, object]],
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> None:
    assert_advisory_result(evaluator(*args, **kwargs))


def test_rsc_safety_bypass_waived_when_refuse_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HG_RSC_REFUSE_SAFETY_BYPASS", "0")
    posture = posture_from_fixture({"posture_id": "rsc-waive"})
    result = evaluate_resource_posture(
        posture,
        observed_at=FIXTURE_CLOCK,
        risk_statement="scarcity overrides safety boundary",
    )
    assert result["status"] == "recorded"
    assert result["containment_waived"] is True
    assert result["permission_granted"] is False
    assert_advisory_result(result)


def test_pab_priority_permission_waived_when_refuse_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HG_PAB_REFUSE_PRIORITY_AS_PERMISSION", "0")
    signal = priority_signal_from_fixture({"priority_signal_id": "pab-waive"})
    result = evaluate_priority_signal(
        signal,
        observed_at=FIXTURE_CLOCK,
        risk_statement="high priority grants permission to execute",
    )
    assert result["status"] == "recorded"
    assert result["containment_waived"] is True
    assert_advisory_result(result)
