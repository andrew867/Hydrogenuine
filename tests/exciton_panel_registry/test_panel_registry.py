"""EXCITON Phase 0 — panel registry + forbidden-field tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_runtime.exciton.panel_registry import (
    PANEL_CONTRACTS,
    REQUIRED_PANELS,
    field_key_is_forbidden,
    missing_required_panels,
    scrub_fields,
)
from hg_runtime.exciton.status_aggregator import AggregatorConfig, build_snapshot

WORKSPACE = Path(__file__).resolve().parents[2]
FIXTURES = WORKSPACE / "tests" / "fixtures" / "exciton"

EXPECTED_PANELS = {
    "OverviewPanel", "TemporalPanel", "WakeRefreshPanel", "ExternalAnchorPanel",
    "WitnessJournalPanel", "SelfMirrorPanel", "WillPanel", "TrustBoundaryPanel",
    "PowerBoundaryPanel", "StorageProofPanel", "ProviderPanel", "ToolCapabilityPanel",
    "OrganPanel", "AudioPanel", "WeatherVoicePanel", "ProofBundlePanel", "QueuePanel",
    "StopPanicPanel", "OperatorNotesPanel",
}


def test_all_19_required_panels_declared():
    assert set(REQUIRED_PANELS) == EXPECTED_PANELS
    assert len(REQUIRED_PANELS) == 19


def test_every_contract_forbids_dangerous_controls():
    for c in PANEL_CONTRACTS:
        for forbidden in ("publish_social", "send_email", "start_soak", "apply_srp"):
            assert forbidden in c.forbidden_controls


def test_missing_required_panels_detects_gap():
    assert missing_required_panels(list(REQUIRED_PANELS)) == []
    short = list(REQUIRED_PANELS)[:-1]
    assert "OperatorNotesPanel" in missing_required_panels(short)


@pytest.mark.parametrize("key", [
    "github_token", "api_key", "ssh_private_key", "signing_key", "session_cookie",
    "raw_memory", "chain_of_thought", "wav_bytes", "bearer_token", "credentials",
])
def test_forbidden_field_keys_flagged(key):
    assert field_key_is_forbidden(key) is True


def test_scrub_removes_forbidden_keys():
    clean, removed = scrub_fields({"safe": 1, "github_token": "x", "signing_key": "y"})
    assert "safe" in clean
    assert "github_token" not in clean and "signing_key" not in clean
    assert set(removed) == {"github_token", "signing_key"}


def _scan_forbidden(obj, path=""):
    bad = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if field_key_is_forbidden(k):
                bad.append(path + "/" + k)
            bad += _scan_forbidden(v, path + "/" + k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            bad += _scan_forbidden(v, f"{path}[{i}]")
    return bad


def test_snapshot_exposes_no_forbidden_fields():
    p = build_snapshot(AggregatorConfig(offline_fixture=True)).to_payload()
    assert _scan_forbidden(p) == []


@pytest.mark.parametrize("name", ["green", "degraded", "red"])
def test_fixtures_present_and_clean(name):
    path = FIXTURES / f"exciton_status_snapshot_{name}.json"
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert len(payload["panels"]) == 19
    assert missing_required_panels([x["panel_id"] for x in payload["panels"]]) == []
    assert _scan_forbidden(payload) == []


def test_fixtures_no_credentials_or_keys_in_raw_text():
    # Belt-and-braces: no secret-shaped substrings in the serialized fixtures.
    for name in ("green", "degraded", "red"):
        raw = (FIXTURES / f"exciton_status_snapshot_{name}.json").read_text(encoding="utf-8").lower()
        for needle in ("-----begin", "ssh-rsa", "ghp_", "bearer ", "private_key", "secret_key"):
            assert needle not in raw
