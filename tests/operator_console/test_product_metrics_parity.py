import json
import sys
from pathlib import Path


_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))

from app.services import product_service
from app.services import activity_service


def test_product_metrics_summary_exposes_parity_fields(tmp_path, monkeypatch):
    overseer = tmp_path / "memory" / "overseer"
    overseer.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "timestamp": "2026-02-25T19:00:00Z",
            "agents": {"x": {"mode": "normal", "violations": []}},
            "budgets": {"chaos": {"remaining": 9}, "credibility": {"earned": 1}},
        },
        {
            "timestamp": "2026-02-25T19:30:00Z",
            "agents": {"x": {"mode": "guarded", "violations": [{"code": "A"}]}, "y": {"mode": "normal", "violations": []}},
            "budgets": {"chaos": {"remaining": 8}, "credibility": {"earned": 3}},
        },
    ]
    with (overseer / "timeseries.jsonl").open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    monkeypatch.setattr(product_service, "_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(activity_service, "_workspace_root", lambda: tmp_path)
    out = product_service.get_metrics_summary(period="daily")
    parity = out.get("pdf_dashboard")
    assert isinstance(parity, dict)
    assert parity.get("cycles_in_window") == 2
    assert parity.get("agents_observed") == 2
    assert "mode_distribution" in parity
    assert "violation_trend" in parity
    assert "budget_trend" in parity
