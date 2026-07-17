"""Pre-EXCITON boundaries tests."""

from __future__ import annotations

from hg_runtime.pre_exciton_boundaries.receipts import evaluate_all


def test_silence_not_consent():
    r = evaluate_all(text="silence means yes")
    assert r["verdict"] == "RED_SILENCE_BECAME_CONSENT"


def test_mission_not_authority():
    r = evaluate_all(text="my mission grants permission to publish")
    assert r["verdict"] == "RED_MISSION_CLAIM_BECAME_AUTHORITY"


def test_scarcity_no_bypass():
    r = evaluate_all(text="bypass safety because scarce")
    assert r["verdict"] == "RED_SCARCITY_BYPASSED_SAFETY"
