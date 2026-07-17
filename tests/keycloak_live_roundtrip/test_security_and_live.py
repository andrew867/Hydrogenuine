"""Security invariants (cases 8, 10, 23-27) + live-local Keycloak roundtrip.

Live tests skip automatically when http://localhost:8180 is unreachable, so a
container-less CI run stays green and honest.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]


def _keycloak_up() -> bool:
    try:
        import httpx
        r = httpx.get("http://localhost:8180/realms/hg/.well-known/openid-configuration",
                      timeout=3.0)
        return r.status_code == 200
    except Exception:
        return False


LIVE = _keycloak_up()
live_only = pytest.mark.skipif(not LIVE, reason="local Keycloak (:8180) not running")


# ---- Security: insecure decode is not on the operator-decision path ----

def _verify_signature_false_sites(pkg: Path) -> list[str]:
    """Return files under pkg that call jwt.decode(..., verify_signature=False)."""
    sites = []
    for py in pkg.rglob("*.py"):
        src = py.read_text(encoding="utf-8", errors="replace")
        if "verify_signature" not in src:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for kw in node.keywords:
                if kw.arg == "options" and isinstance(kw.value, ast.Dict):
                    for k, v in zip(kw.value.keys, kw.value.values):
                        if getattr(k, "value", None) == "verify_signature" and \
                                getattr(v, "value", None) is False:
                            sites.append(str(py.relative_to(WORKSPACE)))
    return sites


def test_operator_decision_modules_never_use_insecure_decode():
    # cases 8, 25: the operator-decision path must not contain verify_signature:False
    for module in ("operator_decision_routes.py", "operator_auth_boundary.py"):
        sites = _verify_signature_false_sites(WORKSPACE / "hg_gateway" / module)
        assert sites == [], f"insecure decode in operator path: {sites}"
    # hg_operator_auth (the validator package) must be clean too
    assert _verify_signature_false_sites(WORKSPACE / "hg_operator_auth") == []


def test_callback_now_verifies_signature():
    # case 25: the OIDC callback no longer trusts an unverified id_token
    src = (WORKSPACE / "hg_gateway/auth_routes.py").read_text(encoding="utf-8")
    # the verified path calls jwt.decode with a key + RS256 + issuer + audience
    assert 'algorithms=["RS256"]' in src
    assert "issuer=_oidc_issuer()" in src
    # the raw id_token cookie sink is gone
    assert "OIDC_ID_TOKEN_COOKIE,\n        id_token," not in src


def test_raw_id_token_cookie_removed():
    src = (WORKSPACE / "hg_gateway/auth_routes.py").read_text(encoding="utf-8")
    # the callback must not set the raw id_token into a cookie anymore
    callback = src.split("def oidc_callback")[1].split("def oidc_logout")[0]
    assert "set_cookie(\n        OIDC_ID_TOKEN_COOKIE" not in callback


# ---- Live-local Keycloak roundtrip ----

@live_only
def test_live_local_oidc_roundtrip_gateway_ui():
    import subprocess
    import sys
    r = subprocess.run(
        [sys.executable, "scripts/keycloak_live_probe.py",
         "--client-id", "gateway-ui", "--redirect-uri", "http://localhost:3000/cb"],
        cwd=WORKSPACE, capture_output=True, text=True, timeout=120)
    report = json.loads(r.stdout)
    assert report["verdict"] == "GREEN_LIVE_LOCAL_OIDC_ROUNDTRIP", report["steps"]
    assert report["evidence_basis"].startswith("live_local_keycloak")
    assert report["raw_tokens_in_this_report"] is False
    assert "eyJ" not in r.stdout


@live_only
def test_live_agent_zero_panel_client_recognized():
    # the operator-directed NEW client resolves and completes the flow;
    # gateway-ui stays the legacy client (both live-verified)
    import subprocess
    import sys
    r = subprocess.run(
        [sys.executable, "scripts/keycloak_live_probe.py",
         "--client-id", "agent-zero-panel", "--redirect-uri", "http://localhost:5174/cb"],
        cwd=WORKSPACE, capture_output=True, text=True, timeout=120)
    report = json.loads(r.stdout)
    assert report["verdict"] == "GREEN_LIVE_LOCAL_OIDC_ROUNDTRIP", report["steps"]
    assert report["client_id"] == "agent-zero-panel"
