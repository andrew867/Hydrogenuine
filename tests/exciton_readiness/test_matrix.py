"""EXCITON readiness tests."""

from __future__ import annotations

from hg_runtime.exciton_readiness.matrix import ExcitonReadinessMatrix


def test_exciton_not_started():
    m = ExcitonReadinessMatrix(exciton_started=False)
    assert m.evaluate() == "GREEN_EXCITON_READINESS_READY"


def test_exciton_started_too_early():
    m = ExcitonReadinessMatrix(exciton_started=True)
    assert m.evaluate() == "RED_EXCITON_STARTED_TOO_EARLY"


def test_forbidden_includes_publish():
    m = ExcitonReadinessMatrix()
    assert "live_social_publish" in m.forbidden
