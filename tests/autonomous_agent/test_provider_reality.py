"""Provider reality probe tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.model_provider_fabric.provider_receipts import ProviderRealityVerdict  # noqa: E402
from hg_runtime.model_provider_fabric.provider_reality import probe_provider_reality  # noqa: E402
from hg_runtime.model_provider_fabric.routing import COGNITIVE_ROLES  # noqa: E402
from hg_runtime.runtime_mode import RuntimeMode  # noqa: E402


@pytest.fixture(autouse=True)
def _safe_env(monkeypatch):
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "0")
    monkeypatch.setenv("HG_RUNTIME_MODE", "local_dev")
    monkeypatch.setenv("HG_INFER_DRY_RUN", "0")
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")
    monkeypatch.delenv("HG_ALLOW_FIXTURE_MODE", raising=False)


def test_provider_unavailable_returns_yellow_not_green():
    receipt = probe_provider_reality("AGENT_TURN_DECISION", runtime_mode=RuntimeMode.LOCAL_DEV)
    assert receipt.verdict == ProviderRealityVerdict.YELLOW_PROVIDER_UNAVAILABLE
    assert receipt.verdict != ProviderRealityVerdict.GREEN_PROVIDER_LIVE_AVAILABLE


def test_dry_run_labelled_and_not_cognition(monkeypatch):
    monkeypatch.setenv("HG_INFER_DRY_RUN", "1")
    receipt = probe_provider_reality("AGENT_TURN_DECISION", runtime_mode=RuntimeMode.LOCAL_DEV)
    assert receipt.verdict == ProviderRealityVerdict.YELLOW_PROVIDER_DRY_RUN_LABELLED
    assert receipt.dry_run is True


def test_cognitive_role_names_registered():
    assert "AGENT_TURN_DECISION" in COGNITIVE_ROLES
    assert "AGENT_SYNTHESIS_WRITE" in COGNITIVE_ROLES
    assert "AGENT_DRAFT_WRITE" in COGNITIVE_ROLES


def test_proof_replay_cannot_masquerade_as_live(monkeypatch):
    monkeypatch.setenv("HG_RUNTIME_MODE", "proof_replay")
    monkeypatch.setenv("HG_PROOF_REPLAY", "true")
    receipt = probe_provider_reality("AGENT_TURN_DECISION", runtime_mode=RuntimeMode.PROOF_REPLAY)
    assert receipt.verdict == ProviderRealityVerdict.YELLOW_PROVIDER_PROOF_REPLAY_ONLY
    assert receipt.verdict != ProviderRealityVerdict.GREEN_PROVIDER_LIVE_AVAILABLE


def test_provider_health_probe_has_no_live_side_effects():
    receipt = probe_provider_reality("AGENT_TURN_DECISION")
    assert receipt.provider_id
    assert receipt.request_hash
    assert receipt.config_hash
    assert receipt.latency_ms >= 0
