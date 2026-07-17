"""Batch CT-C CT-V1 milestone acceptance tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.ct_acceptance.milestone import REQUIRED_MILESTONE_VERDICTS, run_ct_v1_milestone_checks

WORKSPACE = Path(__file__).resolve().parents[2]


def test_milestone_checks_green() -> None:
    result = run_ct_v1_milestone_checks(WORKSPACE)
    assert result["ok"], result.get("critical_failures", result)


def test_required_milestone_verdicts_list() -> None:
    assert "obt_strict_ct_green" in REQUIRED_MILESTONE_VERDICTS
    assert "ct_x1_x5_green" in REQUIRED_MILESTONE_VERDICTS


def test_milestone_ct_v1_bundle_referenced() -> None:
    result = run_ct_v1_milestone_checks(WORKSPACE)
    assert result["ct_v1_bundle"]
    assert result["ct_v1_bundle"].startswith("docs/proofs/connective_tissue/CT-V1/")
