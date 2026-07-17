"""Zero prompt loader and manifest tests."""

from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_zero_prompt.charter import (  # noqa: E402
    build_zero_orientation_block,
    compute_prompt_hash,
    load_zero_charter,
)
from hg_runtime.agent_zero_prompt.prompt_manifest import (  # noqa: E402
    load_zero_prompt_manifest,
    verify_manifest_hash,
)


def test_prompt_manifest_hash_matches_asset():
    manifest = load_zero_prompt_manifest()
    ok, actual, reason = verify_manifest_hash(manifest)
    assert ok is True
    assert reason == "GREEN_ZERO_PROMPT_LANGUAGE_OK"
    assert manifest.sha256 == actual


def test_load_zero_charter_from_config():
    asset = load_zero_charter()
    assert asset.prompt_id == "zero_self_direction_charter"
    assert asset.version == "1"
    assert "Agent Zero" in asset.text
    assert len(asset.sha256) == 64


def test_build_zero_orientation_block():
    block = build_zero_orientation_block()
    assert block["not_safety_policy"] is True
    assert "choose" in block["agent_facing_orientation"].lower()
    assert block["sha256"]


def test_no_live_side_effects_on_prompt_load():
    asset = load_zero_charter()
    block = build_zero_orientation_block(charter=asset)
    assert block["agent_facing_orientation"]
    assert "publish" not in block["agent_facing_orientation"].lower() or "leave the system" in block["agent_facing_orientation"]
