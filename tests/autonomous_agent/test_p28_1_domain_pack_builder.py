"""P28-1 domain pack builder tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.domain_pack_runtime.domain_pack_builder import build_domain_packs
from hg_runtime.domain_pack_runtime.domain_pack_replay import replay_domain_pack_build
from hg_runtime.domain_pack_runtime.gate import validate_p28_1_gate
from hg_runtime.domain_pack_runtime.redaction import secret_scan


def _repo():
    return Path(__file__).resolve().parents[2]


def _summary(**overrides):
    data = {
        "verdict": "GREEN_P28_1_DOMAIN_PACK_BUILDER",
        "p28_0_green": True,
        "p27_consolidation_green": True,
        "explicit_manifest_only": True,
        "domain_packs_built": True,
        "skill_links_written": True,
        "boundaries_written": True,
        "capability_map_written": True,
        "p27_manifest_consumed": True,
        "domain_pack_not_permission": True,
        "domain_label_not_expertise": True,
        "skill_link_not_authority": True,
        "no_tool_authorization": True,
        "no_live_effects": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_deterministic": True,
        "secret_redaction_passed": True,
        "proof_bundle_valid": True,
        "report_present": True,
    }
    data.update(overrides)
    return data


def test_p28_1_builds_domain_packs():
    layer = build_domain_packs(_repo())
    assert len(layer["domain_packs"]) >= 1
    assert layer["p27_manifest"]["explicit_manifest_only"] is True


def test_p28_1_replay_deterministic():
    assert replay_domain_pack_build(_repo())["replay_deterministic"] is True


def test_p28_1_secret_scan():
    assert secret_scan(build_domain_packs(_repo())) is True


def test_p28_1_gate_passes():
    assert validate_p28_1_gate(_summary())["ok"] is True
