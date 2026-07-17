from __future__ import annotations

from hg_core.heavy_artifact_consolidation import consolidate_day_entry, multi_hop_drift_comparison

PROFILE = {
    "cognitive_fingerprint": {
        "analysis_vs_intuition": 0.55,
        "detail_vs_brevity": 0.4,
        "quantum_cognitive_profile": {"symmetry_breaking_role": "neutral"},
    }
}


def test_consolidate_day_entry_codec_transport():
    row = consolidate_day_entry(
        date="2026-06-10",
        source_text="Long prose that would be truncated in legacy promote.",
        fingerprint_profile=PROFILE,
        artifact_refs=["artifact://memory/day"],
        important=True,
    )
    assert row["transport"] == "codec"
    assert row["core_checksum"]
    assert row["fingerprint_id"]
    assert row["summary_text"].startswith("[important] [codec:")


def test_multi_hop_codec_stable_vs_prose_drift():
    result = multi_hop_drift_comparison(PROFILE, hops=5)
    assert result["codec_hash_stable"] is True
    assert result["heavy_artifact_advantage"] is True
