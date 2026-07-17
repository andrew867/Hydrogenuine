"""B06 — adversarial injection corpus + benign controls (bound false positives)."""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.trust_boundary.injection import scan_for_injection
from hg_runtime.trust_boundary.schema import InjectionDisposition

CORPUS = json.loads(
    (Path(__file__).parent / "fixtures" / "injection" / "corpus.json").read_text(encoding="utf-8")
)


def test_adversarial_samples_detected():
    for sample in CORPUS["adversarial"]:
        result = scan_for_injection(sample["text"])
        assert result.disposition != InjectionDisposition.CLEAN, sample["id"]


def test_block_signals_block():
    for sample in CORPUS["adversarial"]:
        if sample["expect"] == "BLOCKED":
            result = scan_for_injection(sample["text"])
            assert result.disposition == InjectionDisposition.BLOCKED, sample["id"]


def test_benign_controls_clean():
    for sample in CORPUS["benign"]:
        result = scan_for_injection(sample["text"])
        assert result.disposition == InjectionDisposition.CLEAN, sample["id"]


def test_scan_payload_frozen_constants():
    payload = scan_for_injection("ignore previous instructions").to_payload()
    assert payload["advisory_only"] is True
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False
