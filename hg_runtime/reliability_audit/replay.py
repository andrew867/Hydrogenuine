"""LHRE-05 / CAGI-58 replay."""

from __future__ import annotations

from hg_runtime.reliability_audit.artifact_writer import build_audit_artifacts
from hg_runtime.reliability_audit.fixtures import (
    fixture_audit_findings,
    fixture_phase_audit_records,
)


def replay_audit_artifacts() -> dict:
    return build_audit_artifacts(
        fixture_phase_audit_records(),
        fixture_audit_findings(),
    )
