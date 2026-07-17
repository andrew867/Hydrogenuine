"""Agent #0 dev boot prep tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.agent0_dev_boot.boot import run_agent0_dev_boot
from hg_runtime.agent0_dev_boot.liveness import wrap_liveness_response
from hg_runtime.agent0_dev_boot.profiles import PROFILES_DIR

def test_dry_run_boot_plan() -> None:
    result = run_agent0_dev_boot(
        profile_path=PROFILES_DIR / "agent0-dev-boot-local-openvino.json",
        dry_run=True,
        storage_required=False,
    )
    assert not result.verdict.startswith("RED")
    assert result.dry_run is True
    assert result.chrono_context is not None
    assert result.audio_context is not None
    assert any(e.get("event_type") == "Agent0WakeRequested" for e in result.events)


def test_fallback_stub_dry_run() -> None:
    result = run_agent0_dev_boot(
        profile_path=PROFILES_DIR / "agent0-dev-boot-fallback-stub.json",
        dry_run=True,
        allow_fallback_stub=True,
        storage_required=False,
    )
    assert result.verdict in {
        "GREEN_AGENT0_PREP_READY",
        "YELLOW_AGENT0_PREP_READY_STORAGE_PENDING",
        "YELLOW_FALLBACK_STUB_ONLY",
    }


def test_liveness_wrapper_safe() -> None:
    out = wrap_liveness_response(
        raw_model_response="I am an AI and cannot experience life.",
        provider_id="windows-openvino-gpu",
        model_id="test",
        fallback_stub=False,
    )
    assert "awake in dev mode" in out["wrapper_response"]
    assert out["raw_model_response_hash"].startswith("sha256:")
    assert out["permission_granted"] is False
    assert out["consciousness_claim"] is False
