"""Live E2E (mission case 20) — scripted-OIDC Workbench spine. keycloak_live only."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]


def _keycloak_up() -> bool:
    try:
        import httpx
        return httpx.get(
            "http://localhost:8180/realms/hg/.well-known/openid-configuration",
            timeout=3.0).status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.keycloak_live


@pytest.mark.skipif(not _keycloak_up(), reason="local Keycloak (:8180) not running")
def test_live_workbench_e2e_full_spine(tmp_path):
    out = tmp_path / "e2e.json"
    r = subprocess.run(
        [sys.executable, "scripts/workbench_live_e2e.py", "--out", str(out)],
        cwd=WORKSPACE, capture_output=True, text=True, timeout=180)
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["verdict"] == "GREEN_WORKBENCH_LIVE_E2E", report["steps"]
    assert report["raw_tokens_in_this_report"] is False
    assert "eyJ" not in out.read_text(encoding="utf-8")
    # the full governed spine landed in one chained run
    assert report["timeline_kinds"] == [
        "run_created", "artifact_registered", "progress_event", "progress_event",
        "steering_message", "setting_change"]
