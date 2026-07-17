"""Runtime profile tests."""

from __future__ import annotations

import pytest

from hg_runtime.agent0_dev_boot.profiles import PROFILES_DIR, load_runtime_profile, list_runtime_profiles


def test_all_profiles_load() -> None:
    for path in list_runtime_profiles():
        data = load_runtime_profile(path)
        assert data["permission_granted"] is False
        assert data["live_oea"] is False


def test_openvino_profile_requires_fabric() -> None:
    data = load_runtime_profile(PROFILES_DIR / "dev-local-openvino.json")
    assert data["provider_fabric_required"] is True
    assert data["cloud_providers_enabled"] is False


def test_unsafe_profile_rejected() -> None:
    bad = {
        "profile_id": "bad",
        "purpose": "x",
        "duration_budget_minutes": 1,
        "token_budget": 1,
        "heartbeat_interval_seconds": 1,
        "external_network_allowed": False,
        "cloud_providers_enabled": False,
        "live_oea": True,
        "live_ter": False,
        "srp_apply": False,
        "publish": False,
        "child_spawn": False,
        "permission_granted": False,
        "authority_created": False,
    }
    from hg_runtime.agent0_dev_boot.profiles import validate_runtime_profile

    with pytest.raises(ValueError):
        validate_runtime_profile(bad)
