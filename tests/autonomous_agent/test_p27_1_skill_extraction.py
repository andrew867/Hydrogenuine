"""P27-1 skill extraction tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.skill_graph.batch_gate import validate_p27_1_gate
from hg_runtime.skill_graph.skill_extractor import extract_skills_from_p26
from hg_runtime.skill_graph.skill_replay import replay_skill_extraction


def _layer():
    return extract_skills_from_p26(Path(__file__).resolve().parents[2])


def test_p27_1_extracts_skills_from_p26():
    assert len(_layer()["skill_records"]) >= 1


def test_p27_1_all_skills_have_provenance():
    assert all(row["provenance_refs"] for row in _layer()["skill_records"])


def test_p27_1_skill_not_authority():
    assert all(not row["skill_treated_as_authority"] for row in _layer()["skill_records"])


def test_p27_1_replay_deterministic():
    assert replay_skill_extraction(Path(__file__).resolve().parents[2])["replay_deterministic"] is True


def test_p27_1_gate_passes():
    assert validate_p27_1_gate(
        {
            "verdict": "GREEN_P27_1_SKILL_EXTRACTION",
            "p27_0_green": True,
            "p26_consolidation_green": True,
            "explicit_manifest_only": True,
            "skills_extracted": True,
            "source_links_written": True,
            "provenance_pointers_recorded": True,
            "skill_not_authority": True,
            "memory_not_truth": True,
            "recall_not_authority": True,
            "skill_without_provenance_rejected": True,
            "confidence_descriptive_only": True,
            "no_tool_authorization": True,
            "no_live_effects": True,
            "phase19_yellow_preserved": True,
            "phase24_infrastructure_only_preserved": True,
            "replay_deterministic": True,
            "secret_redaction_passed": True,
            "proof_bundle_valid": True,
            "report_present": True,
        }
    )["ok"]
