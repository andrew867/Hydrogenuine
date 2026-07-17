"""Provider health tests."""
from __future__ import annotations

from hg_runtime.live_provider.provider_health import probe_provider_health


def test_health_unavailable_returns_yellow(monkeypatch):
    monkeypatch.setenv("HG_LIVE_PROVIDER_KIND", "dry_unavailable")
    monkeypatch.delenv("HG_OPENVINO_ENDPOINT", raising=False)
    receipt = probe_provider_health()
    assert receipt.provider_ref
    assert not receipt.available
    assert receipt.verdict.value.startswith("YELLOW_")


def test_health_available_when_openvino_running():
    receipt = probe_provider_health()
    if receipt.available:
        assert receipt.verdict.value.startswith("GREEN_")
    else:
        assert receipt.verdict.value.startswith("YELLOW_")
    assert receipt.hash
