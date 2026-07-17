"""Pack 15: Unit tests for signals_json schema and signal groups."""

import pytest

from hg_core.signals.schema import (
    SIGNALS_JSON_SCHEMA_VERSION,
    build_signals_json,
    signal_groups_doc,
)


def test_schema_version_defined():
    assert SIGNALS_JSON_SCHEMA_VERSION == "1.0"


def test_signal_groups_doc_contains_groups():
    assert "drift_erosion" in signal_groups_doc
    assert "persona_coherence" in signal_groups_doc
    assert "verification_behavior" in signal_groups_doc
    assert "emotion_affect" in signal_groups_doc
    assert "legal_privacy" in signal_groups_doc
    assert "vector_divergence" in signal_groups_doc


def test_build_signals_json_minimal():
    out = build_signals_json()
    assert out["schema_version"] == "1.0"
    assert list(out.keys()) == ["schema_version"]


def test_build_signals_json_with_groups():
    out = build_signals_json(
        drift_erosion={"capability_creep_score": 0.5},
        emotion_affect={"valence": 0.2, "arousal": 0.1},
    )
    assert out["schema_version"] == "1.0"
    assert out["drift_erosion"] == {"capability_creep_score": 0.5}
    assert out["emotion_affect"] == {"valence": 0.2, "arousal": 0.1}
