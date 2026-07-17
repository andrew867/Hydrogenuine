"""Organ manifest tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_runtime.agent0_dev_boot.manifest import load_organ_manifest, manifest_digest, validate_organ_manifest

MANIFEST = Path(__file__).resolve().parents[2] / "configs" / "organs" / "agent0_dev_organ_manifest.json"


def test_manifest_loads() -> None:
    data = load_organ_manifest()
    assert data["manifest_id"]
    assert len(data["organs"]) >= 15


def test_required_organs_present() -> None:
    data = load_organ_manifest()
    ids = {o["organ_id"] for o in data["organs"]}
    assert "organ:Agent0" in ids
    assert "organ:AIS" in ids
    assert "organ:AIO" in ids


def test_no_permission_on_organs() -> None:
    data = load_organ_manifest()
    for organ in data["organs"]:
        assert organ["permission_granted"] is False


def test_required_organ_missing_fails() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    data["organs"] = [o for o in data["organs"] if o["organ_id"] != "organ:Agent0"]
    with pytest.raises(ValueError):
        validate_organ_manifest(data)


def test_manifest_digest_stable() -> None:
    data = load_organ_manifest()
    assert manifest_digest(data) == manifest_digest(data)
