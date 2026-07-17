"""Operator social env loader tests."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from hg_runtime.social_capability.credentials import (
    apply_social_env_aliases,
    load_operator_social_env,
    live_read_credentials_present,
    social_env_candidate_paths,
)
from hg_runtime.social_capability.live_bridge import live_read_enabled


@pytest.fixture(autouse=True)
def _clear_social_env(monkeypatch):
    for key in list(os.environ):
        if key.startswith(("HG_SOCIAL_", "HG_MOLTBOOK_", "HG_FOURCLAW_", "HG_ENABLE_LIVE_SOCIAL")):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("HG_SOCIAL_LIVE_PUBLISH", "false")
    monkeypatch.setenv("HG_ENABLE_LIVE_SOCIAL_WRITES", "false")


def test_loads_only_operator_local_social_env(tmp_path, monkeypatch):
    secrets = tmp_path / ".hg-local" / "secrets"
    secrets.mkdir(parents=True)
    social = secrets / "social.env"
    social.write_text(
        "\n".join(
            [
                "HG_SOCIAL_LIVE_READ=true",
                "HG_SOCIAL_MOLTBOOK_TOKEN=mb-test-token",
                "HG_SOCIAL_FOURCLAW_TOKEN=fc-test-token",
                "HG_SOCIAL_LIVE_PUBLISH=false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    # Root .env must not be consulted even if present.
    (tmp_path / ".env").write_text("MOLTBOOK_API_KEY=root-env-should-not-load\n", encoding="utf-8")

    loaded = load_operator_social_env(workspace=tmp_path, override=True)
    assert str(social) in loaded
    assert live_read_enabled() is True
    assert os.environ.get("HG_MOLTBOOK_TOKEN") == "mb-test-token"
    assert os.environ.get("HG_FOURCLAW_TOKEN") == "fc-test-token"
    assert os.environ.get("MOLTBOOK_API_KEY") != "root-env-should-not-load"
    assert live_read_credentials_present(surface="moltbook") is True


def test_env_social_local_candidate(tmp_path):
    paths = social_env_candidate_paths(workspace=tmp_path)
    assert any(p.name == "social.env" for p in paths)
    assert any(p.name == ".env.social.local" for p in paths)


def test_apply_aliases_without_overwriting_existing(monkeypatch):
    monkeypatch.setenv("HG_SOCIAL_MOLTBOOK_TOKEN", "from-social")
    monkeypatch.setenv("HG_MOLTBOOK_TOKEN", "already-set")
    apply_social_env_aliases()
    assert os.environ["HG_MOLTBOOK_TOKEN"] == "already-set"
