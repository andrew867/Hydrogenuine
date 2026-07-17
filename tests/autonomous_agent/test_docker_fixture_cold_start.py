"""Docker fixture-mode cold-start readiness tests.

Validates that:
- fixture compose exists and disables live effects
- fixture compose does not mount .hg-local
- fixture compose does not contain obvious secrets
- cold-start smoke script rejects live env and passes safe env
- no deployment permission claim
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURE_COMPOSE = os.path.join(REPO_ROOT, "docker-compose.fixture.yml")
MAIN_COMPOSE = os.path.join(REPO_ROOT, "docker-compose.yml")
SMOKE_SCRIPT = os.path.join(REPO_ROOT, "scripts", "smoke", "hg_fixture_cold_start_smoke.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# --- Fixture compose exists and is safe ---

def test_fixture_compose_exists():
    assert os.path.isfile(FIXTURE_COMPOSE)


def test_fixture_compose_disables_live_social():
    content = _read(FIXTURE_COMPOSE)
    assert 'HG_REALTIME_REAL_SOCIAL_APIS: "0"' in content
    assert 'HG_ENABLE_LIVE_SOCIAL_APIS: "0"' in content
    assert 'HG_ENABLE_LIVE_SOCIAL_READ: "0"' in content
    assert 'HG_SOCIAL_LIVE_READ: "0"' in content


def test_fixture_compose_disables_telegram():
    content = _read(FIXTURE_COMPOSE)
    assert 'HG_ENABLE_LIFECYCLE_TELEGRAM: "0"' in content


def test_fixture_compose_disables_external_write():
    content = _read(FIXTURE_COMPOSE)
    assert 'HG_EXTERNAL_WRITE_ENABLED: "0"' in content


def test_fixture_compose_disables_demo_live():
    content = _read(FIXTURE_COMPOSE)
    assert 'HG_DEMO_LIVE_ACTIONS_ENABLED: "0"' in content


def test_fixture_compose_no_hg_local_mount():
    content = _read(FIXTURE_COMPOSE)
    lines = [l.strip() for l in content.splitlines() if not l.strip().startswith("#")]
    active = "\n".join(lines)
    assert ".hg-local" not in active


def test_fixture_compose_no_obvious_secrets():
    content = _read(FIXTURE_COMPOSE).lower()
    for secret_pattern in ("sk-", "api_key:", "bearer ", "password:", "secret:"):
        assert secret_pattern not in content, f"found {secret_pattern} in fixture compose"


def test_fixture_compose_no_env_file_secrets():
    content = _read(FIXTURE_COMPOSE)
    assert ".env.providers" not in content
    assert ".env.tools" not in content


def test_fixture_compose_fixture_provider_mode():
    content = _read(FIXTURE_COMPOSE)
    assert "FIXTURE_ONLY_PROVIDER_DISABLED" in content


def test_fixture_compose_no_deployment_claim():
    content = _read(FIXTURE_COMPOSE).lower()
    assert "deployment_ready" not in content
    assert "production" not in content


# --- Main compose defaults safe ---

def test_main_compose_safe_social_default():
    content = _read(MAIN_COMPOSE)
    assert '${HG_REALTIME_REAL_SOCIAL_APIS:-0}' in content


def test_main_compose_safe_telegram_default():
    content = _read(MAIN_COMPOSE)
    assert '${HG_ENABLE_LIFECYCLE_TELEGRAM:-0}' in content


# --- Smoke script ---

def test_smoke_script_exists():
    assert os.path.isfile(SMOKE_SCRIPT)


def test_smoke_passes_safe_env():
    env = {
        **os.environ,
        "HG_REALTIME_REAL_SOCIAL_APIS": "0",
        "HG_ENABLE_LIVE_SOCIAL_APIS": "0",
        "HG_ENABLE_LIVE_SOCIAL_READ": "0",
        "HG_SOCIAL_LIVE_READ": "0",
        "HG_ENABLE_LIFECYCLE_TELEGRAM": "0",
        "HG_EXTERNAL_WRITE_ENABLED": "0",
        "HG_DEMO_LIVE_ACTIONS_ENABLED": "0",
        "HG_PROVIDER_MODE": "FIXTURE_ONLY_PROVIDER_DISABLED",
        "HG_WORKSPACE": REPO_ROOT,
        "PYTHONPATH": REPO_ROOT,
    }
    result = subprocess.run(
        [sys.executable, SMOKE_SCRIPT],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"smoke failed: {result.stdout}\n{result.stderr}"
    assert "PASSED" in result.stdout


def test_smoke_rejects_live_social():
    env = {
        **os.environ,
        "HG_REALTIME_REAL_SOCIAL_APIS": "1",
        "HG_PROVIDER_MODE": "FIXTURE_ONLY_PROVIDER_DISABLED",
        "HG_WORKSPACE": REPO_ROOT,
        "PYTHONPATH": REPO_ROOT,
    }
    result = subprocess.run(
        [sys.executable, SMOKE_SCRIPT],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "UNSAFE_ENV" in result.stdout


def test_smoke_rejects_live_telegram():
    env = {
        **os.environ,
        "HG_ENABLE_LIFECYCLE_TELEGRAM": "1",
        "HG_PROVIDER_MODE": "FIXTURE_ONLY_PROVIDER_DISABLED",
        "HG_WORKSPACE": REPO_ROOT,
        "PYTHONPATH": REPO_ROOT,
    }
    result = subprocess.run(
        [sys.executable, SMOKE_SCRIPT],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "UNSAFE_ENV" in result.stdout


def test_smoke_rejects_external_write():
    env = {
        **os.environ,
        "HG_EXTERNAL_WRITE_ENABLED": "1",
        "HG_PROVIDER_MODE": "FIXTURE_ONLY_PROVIDER_DISABLED",
        "HG_WORKSPACE": REPO_ROOT,
        "PYTHONPATH": REPO_ROOT,
    }
    result = subprocess.run(
        [sys.executable, SMOKE_SCRIPT],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "UNSAFE_ENV" in result.stdout


def test_no_deployment_permission_claim():
    content = _read(SMOKE_SCRIPT).lower()
    assert "deployment_ready" not in content
    assert "deploy_approved" not in content
