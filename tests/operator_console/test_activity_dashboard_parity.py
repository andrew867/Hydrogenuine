import json
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

from hg_gateway.shared_storage import append_overseer_timeseries, upsert_latest_overseer_state

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))

from app.services import activity_service


def test_get_dashboard_data_includes_pdf_parity_aggregates(tmp_path, monkeypatch):
    overseer = tmp_path / "memory" / "overseer"
    overseer.mkdir(parents=True, exist_ok=True)
    start = datetime.now(timezone.utc) - timedelta(minutes=15)
    second = start + timedelta(minutes=15)
    latest_state = {
        "timestamp": second.isoformat().replace("+00:00", "Z"),
        "analysis_capabilities": {
            "agents_total": 2,
            "degraded_agents": ["alpha"],
            "degraded_count": 1,
            "reasons": ["humanization modules unavailable: optional modules missing"],
            "summary": "optional analysis degraded for 1/2 agents",
        },
    }
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "memory" / "gateway.sqlite3"))
    monkeypatch.setattr("hg_lib.config.get_workspace_root", lambda: tmp_path)
    upsert_latest_overseer_state(latest_state)
    series = [
        {
            "timestamp": start.isoformat().replace("+00:00", "Z"),
            "agents": {
                "alpha": {"mode": "normal", "violations": [{"code": "X"}]},
                "beta": {"mode": "guarded", "violations": []},
            },
            "budgets": {"chaos": {"remaining": 12}, "credibility": {"earned": 4}},
        },
        {
            "timestamp": second.isoformat().replace("+00:00", "Z"),
            "agents": {
                "alpha": {"mode": "normal", "violations": []},
            },
            "budgets": {"chaos": {"remaining": 11}, "credibility": {"earned": 5}},
        },
    ]
    for row in series:
        append_overseer_timeseries(row)

    monkeypatch.setattr(activity_service, "_workspace_root", lambda: tmp_path)
    out = activity_service.get_dashboard_data(hours=24)
    parity = out.get("pdf_dashboard")
    assert isinstance(parity, dict)
    assert parity.get("cycles_in_window") == 2
    assert parity.get("agents_observed") == 2
    assert parity.get("latest_timestamp") == second.isoformat().replace("+00:00", "Z")
    assert parity.get("mode_distribution", {}).get("normal") == 2
    assert parity.get("mode_distribution", {}).get("guarded") == 1
    assert isinstance(parity.get("violation_trend"), list)
    assert isinstance(parity.get("budget_trend"), list)
    assert out.get("analysis_capabilities", {}).get("degraded_count") == 1
    assert out.get("summary", {}).get("analysis_capabilities", {}).get("degraded_agents") == ["alpha"]
