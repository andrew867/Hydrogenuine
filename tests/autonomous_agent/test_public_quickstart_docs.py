"""Tests for public quickstart documentation validation."""

from __future__ import annotations

import pytest
from pathlib import Path


DOCS_DIR = Path(__file__).resolve().parents[2] / "docs" / "public"


def test_docker_quickstart_mentions_fixture_default():
    path = DOCS_DIR / "QUICKSTART_DOCKER_FIXTURE.md"
    assert path.exists()
    content = path.read_text(encoding="utf-8").lower()
    assert "fixture" in content
    assert "default" in content


def test_lmstudio_doc_mentions_host_container_localhost():
    path = DOCS_DIR / "QUICKSTART_LMSTUDIO_OPTIONAL.md"
    assert path.exists()
    content = path.read_text(encoding="utf-8").lower()
    assert "host.docker.internal" in content
    assert "localhost" in content
    assert "container" in content


def test_lmstudio_doc_mentions_tailscale_endpoint():
    path = DOCS_DIR / "QUICKSTART_LMSTUDIO_OPTIONAL.md"
    content = path.read_text(encoding="utf-8").lower()
    assert "tailscale" in content


def test_lmstudio_doc_mentions_model_whitelist():
    path = DOCS_DIR / "QUICKSTART_LMSTUDIO_OPTIONAL.md"
    content = path.read_text(encoding="utf-8").lower()
    assert "whitelist" in content or "allowed" in content


def test_lmstudio_doc_mentions_available_model_not_permission():
    path = DOCS_DIR / "QUICKSTART_LMSTUDIO_OPTIONAL.md"
    content = path.read_text(encoding="utf-8").lower()
    assert "available model is not permission" in content


def test_openvino_doc_mentions_downloads_disabled_by_default():
    path = DOCS_DIR / "QUICKSTART_DOCKER_FIXTURE.md"
    content = path.read_text(encoding="utf-8").lower()
    assert "download" in content
    assert "false" in content


def test_not_agi_doc_present():
    path = DOCS_DIR / "NOT_AGI.md"
    assert path.exists()
    content = path.read_text(encoding="utf-8").lower()
    assert "not agi" in content


def test_claims_boundaries_doc_present():
    path = DOCS_DIR / "CLAIMS_AND_BOUNDARIES.md"
    assert path.exists()
    content = path.read_text(encoding="utf-8").lower()
    assert "cannot say" in content or "you cannot" in content


def test_docker_quickstart_mentions_no_secrets():
    path = DOCS_DIR / "QUICKSTART_DOCKER_FIXTURE.md"
    content = path.read_text(encoding="utf-8").lower()
    assert "secret" in content


def test_docker_quickstart_mentions_hg_local_excluded():
    path = DOCS_DIR / "QUICKSTART_DOCKER_FIXTURE.md"
    content = path.read_text(encoding="utf-8").lower()
    assert ".hg-local" in content


def test_docker_quickstart_mentions_not_production():
    path = DOCS_DIR / "QUICKSTART_DOCKER_FIXTURE.md"
    content = path.read_text(encoding="utf-8").lower()
    assert "not production" in content or "not deploy" in content
