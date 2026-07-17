import json
import sys
from pathlib import Path

import pytest

# bose_integration depends on the (optional) scipy stack.
pytest.importorskip("scipy")

_workspace = Path(__file__).resolve().parents[2]
_overseer_core = _workspace / "hg_overseer" / "overseer_core"
if str(_overseer_core) not in sys.path:
    sys.path.insert(0, str(_overseer_core))

import bose_integration as bi


def test_normalize_metric_history_flattens_dicts_and_scalars():
    normalized, meta = bi._normalize_metric_history(
        {
            "support_ratio": [(1, 0.2), {"timestamp": 2, "value": 0.4}],
            "competence": {
                "overall": 0.8,
                "quality": [(3, 0.9)],
            },
            "bad_metric": {"oops": "not-a-number"},
        }
    )

    assert sorted(normalized.keys()) == ["competence.overall", "competence.quality", "support_ratio"]
    assert normalized["competence.overall"][-1][1] == 0.8
    assert normalized["competence.quality"][0] == (3.0, 0.9)
    assert meta["normalized_metric_count"] == 3
    assert meta["flattened_metric_count"] >= 1
    assert "bad_metric" in meta["dropped_metric_keys"]


def test_analyze_agent_with_bose_skips_fallback_humanization_metrics(monkeypatch):
    monkeypatch.setattr(bi, "extract_all_metrics", lambda _agent_id, hours=24: {"support_ratio": [(1, 0.5)]})
    monkeypatch.setattr(bi, "extract_competence_metrics", lambda _agent_id, hours=24: {"competence": {"overall": 0.7}})
    monkeypatch.setattr(bi, "HUMANIZATION_METRICS_AVAILABLE", True)
    monkeypatch.setattr(
        bi,
        "get_humanization_capability_status",
        lambda: {
            "modules_available": False,
            "fallback_active": True,
            "import_error": "optional modules missing",
            "semantic_duplicate_embeddings_available": False,
            "reasons": ["humanization modules unavailable: optional modules missing"],
        },
    )
    monkeypatch.setattr(
        bi.BoseAnalysis,
        "analyze_agent",
        lambda self, metric_history, hours=24: {
            "metrics_analyzed": list(metric_history.keys()),
            "capabilities": {"input_normalization": {"normalized_metric_count": len(metric_history)}},
        },
    )

    result = bi.analyze_agent_with_bose("demo-agent", hours=24)

    assert "support_ratio" in result["_metric_history"]
    assert "competence.overall" in result["_metric_history"]
    assert "agent_detection_accuracy" not in result["_metric_history"]
    assert result["capabilities"]["degraded_optional_analysis"] is True
    assert result["capabilities"]["humanization_metrics"]["fallback_active"] is True
