"""CT-02 SEC-U6 bundle sealing tests."""

from __future__ import annotations

import pytest

from hg_core.secrets.bundle import refuse_seal_if_leak, seal_proof_bundle
from hg_core.secrets.canary import CANARY_MARKERS
from hg_core.secrets.redact import RedactionFailure


def test_sec_u6_bundle_with_canary_refused(tmp_path) -> None:
    proof = tmp_path / "bundle"
    proof.mkdir()
    (proof / "leak.txt").write_text(CANARY_MARKERS["bundle"], encoding="utf-8")
    ok, hits = seal_proof_bundle(proof)
    assert not ok
    assert hits
    with pytest.raises(RedactionFailure):
        refuse_seal_if_leak(proof)


def test_clean_bundle_seals(tmp_path) -> None:
    proof = tmp_path / "bundle"
    proof.mkdir()
    (proof / "status.md").write_text("ok", encoding="utf-8")
    ok, hits = seal_proof_bundle(proof)
    assert ok
    assert not hits
