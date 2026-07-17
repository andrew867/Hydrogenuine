"""Harness + browser-E2E evidence tests (WFC).

Fast checks assert the local stack health and the harness safety invariants;
the browser proof is validated from the latest sealed bundle's evidence (written
by the gate) so we do not re-drive chromium here. A directly-runnable live browser
test is provided under the `browser_e2e` marker, gated on WFC_RUN_BROWSER_TEST=1 so
it does not double-run inside the gate.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
OUTER = WORKSPACE.parent
KC = os.environ.get("KEYCLOAK_URL", "http://localhost:8180")
GW = os.environ.get("WFC_GATEWAY_ORIGIN", "http://localhost:8080")
CONSOLE = os.environ.get("WFC_CONSOLE_ORIGIN", "http://localhost:5173")


def _get(url, timeout=3.0):
    try:
        import httpx
        return httpx.get(url, timeout=timeout)
    except Exception:
        return None


def _keycloak_up():
    r = _get(f"{KC}/realms/hg/.well-known/openid-configuration")
    return bool(r and r.status_code == 200)


def _gateway_up():
    r = _get(f"{GW}/v1/auth/config")
    return bool(r and r.status_code == 200)


def _console_up():
    r = _get(f"{CONSOLE}/")
    return bool(r and r.status_code == 200)


# ---- harness health (cases 1-3) ----

@pytest.mark.keycloak_live
def test_keycloak_discovery():
    if not _keycloak_up():
        pytest.skip("local Keycloak not up")
    r = _get(f"{KC}/realms/hg/.well-known/openid-configuration")
    assert r.status_code == 200
    assert "authorization_endpoint" in r.json()


@pytest.mark.keycloak_live
def test_gateway_health_serves_workbench_auth():
    if not _gateway_up():
        pytest.skip("gateway not up on :8080")
    cfg = _get(f"{GW}/v1/auth/config").json()
    assert cfg.get("oidc_client_id")  # OIDC configured


@pytest.mark.keycloak_live
def test_console_panel_route_served():
    if not _console_up():
        pytest.skip("operator console not up on :5173")
    r = _get(f"{CONSOLE}/")
    assert r.status_code == 200


# ---- harness safety (case 4) ----

def test_harness_script_has_no_push_or_deploy():
    src = (WORKSPACE / "scripts/dev/run_workbench_e2e_harness.py").read_text(encoding="utf-8")
    # No push/deploy COMMANDS (the word "deployment" appears only in the negated
    # doctrine note "not a production deployment").
    lowered = src.lower()
    assert "git push" not in lowered
    assert "docker push" not in lowered
    assert "kubectl" not in lowered
    assert "helm " not in lowered
    # only starts loopback services
    assert "127.0.0.1" in src or "localhost" in src


# ---- browser evidence (cases 5-11,19-23), validated from the latest bundle ----

def _latest_evidence():
    root = OUTER / "docs/proofs/agent_zero_workbench_feature_complete"
    if not root.exists():
        return None
    dirs = sorted(d for d in root.iterdir() if d.is_dir())
    for d in reversed(dirs):
        ev = d / "playwright_result.json"
        if ev.exists():
            return json.loads(ev.read_text(encoding="utf-8"))
    return None


def test_latest_browser_evidence_is_green_or_honest_yellow():
    ev = _latest_evidence()
    if ev is None:
        pytest.skip("no feature-complete bundle yet (run the gate first)")
    assert ev["verdict"].startswith(("GREEN", "YELLOW")), ev.get("verdict")


def test_browser_evidence_when_live_proves_all_steps():
    ev = _latest_evidence()
    if ev is None or ev.get("browser_login_status") != "live":
        pytest.skip("no live browser evidence")
    ok = {s["step"] for s in ev.get("steps", []) if s["ok"]}
    for required in ("browser_oidc_login", "no_raw_token_in_browser_state",
                     "browser_run_created", "server_side_sha256_matches_bytes",
                     "raw_file_bytes_absent_from_receipts", "browser_progress_visible",
                     "browser_subagent_and_persona_visible", "browser_steering_receipted",
                     "browser_high_risk_setting_held", "receipt_timeline_visible",
                     "receipt_chain_valid", "unauthenticated_create_rejected"):
        assert required in ok, f"missing/failed step: {required}"
    # server hash, not browser-reported, is the upload proof
    assert ev.get("server_content_hash", "").startswith("sha256:")
    # transport observed a real SSE network response
    assert ev.get("sse_network_observed") is True
    assert ev.get("browser_storage_scan", {}).get("jwt_present") is False
    assert ev.get("browser_storage_scan", {}).get("session_cookie_js_readable") is False


# ---- optional live browser run (case 5, direct) ----

@pytest.mark.browser_e2e
def test_run_browser_e2e_live_optional(tmp_path):
    if os.environ.get("WFC_RUN_BROWSER_TEST") != "1":
        pytest.skip("set WFC_RUN_BROWSER_TEST=1 to drive chromium in-test")
    if not (_keycloak_up() and _gateway_up() and _console_up()):
        pytest.skip("local Workbench stack not up")
    import subprocess
    import sys
    out = tmp_path / "ev.json"
    env = dict(os.environ)
    env["HG_WORKBENCH_DIR"] = str(WORKSPACE / ".tmp" / "wfc_workbench_runs")
    env["KEYCLOAK_CLIENT_ID"] = "agent-zero-panel"
    r = subprocess.run([sys.executable, "scripts/workbench_feature_complete_browser_e2e.py",
                        "--out", str(out), "--screenshots", str(tmp_path / "shots")],
                       cwd=WORKSPACE, env=env, capture_output=True, text=True, timeout=300)
    ev = json.loads(out.read_text(encoding="utf-8"))
    assert ev["verdict"].startswith(("GREEN", "YELLOW")), ev
