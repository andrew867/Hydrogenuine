from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _quantum_e2e_env(monkeypatch):
    monkeypatch.setenv("HG_QUANTUM_SYMMETRY_BREAKING_ENABLED", "true")
    monkeypatch.setenv("HG_QUANTUM_LDPC_VERIFICATION_ENABLED", "true")
    monkeypatch.setenv("HG_QUANTUM_NOISE_CHARACTERIZATION_ENABLED", "true")
    monkeypatch.setenv("HG_EMBODIED_MOCK_MODE", "1")


@pytest.fixture
def proof_dir(tmp_path) -> Path:
    base = os.environ.get("QR_E2E_PROOF_DIR")
    if base:
        path = Path(base)
        path.mkdir(parents=True, exist_ok=True)
        return path
    return tmp_path / "proofs"
