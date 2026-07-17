from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from hg_knowledge.control_plane import append_research_history, queue_topic, save_source_config
from operator_console.server.app.core.auth import require_api_key
from operator_console.server.app.main import app


def test_knowledge_control_and_queue_endpoints(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "memory" / "gateway.sqlite3"))
    (tmp_path / "memory" / "automation").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "automation" / "realtime_schedule.json").write_text(
        json.dumps([{"job_id": "knowledge-research-auto-v2", "interval_minutes": 15, "inputs": {"trigger": "realtime", "goal": ""}}]),
        encoding="utf-8",
    )
    queue_topic("Entity continuity", requested_by="operator", priority="high")

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        control = client.get("/api/v1/knowledge/control")
        assert control.status_code == 200
        payload = control.json()
        assert payload["queue_count"] == 1
        assert payload["schedule"]["enabled"] is True

        add_response = client.post(
            "/api/v1/knowledge/queue",
            json={"topic": "Bayman keystore migration", "requested_by": "bayman", "priority": "medium", "context": "NB-3 prep"},
        )
        assert add_response.status_code == 200
        queue_payload = client.get("/api/v1/knowledge/queue").json()
        topics = {item["topic"] for item in queue_payload["queued_topics"]}
        assert "Entity continuity" in topics
        assert "Bayman keystore migration" in topics

        disable_response = client.post("/api/v1/knowledge/schedule", json={"enabled": False})
        assert disable_response.status_code == 200
        assert disable_response.json()["enabled"] is False

        enable_response = client.post("/api/v1/knowledge/schedule", json={"enabled": True})
        assert enable_response.status_code == 200
        assert enable_response.json()["enabled"] is True
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_knowledge_delivery_summary_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "memory" / "gateway.sqlite3"))
    (tmp_path / "knowledge" / "current_events").mkdir(parents=True, exist_ok=True)
    append_research_history(
        "knowledge-research-auto-v2",
        topic="current events brief",
        file_path="knowledge/current_events/brief-2026-03-13.md",
        source_count=4,
        source_mix={"brave": 3, "google_news": 1},
    )
    append_research_history(
        "knowledge-research-auto-v2",
        topic="AI infrastructure",
        file_path="knowledge/technology/ai-infrastructure.md",
        source_count=2,
        source_mix={"brave": 2},
    )
    (tmp_path / "knowledge" / "current_events" / "brief-2026-03-13.md").write_text(
        "# Current Events Brief\n\n1. **Headline** - https://example.com\n",
        encoding="utf-8",
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/knowledge/delivery-summary?limit=3&max_chars=1200")
        assert response.status_code == 200
        payload = response.json()
        assert payload["recent_topic_count"] == 2
        assert payload["recent_topics"][0]["topic"] == "AI infrastructure"
        assert payload["recent_topics"][0]["source_mix"]["brave"] == 2
        assert payload["latest_brief_path"].endswith("brief-2026-03-13.md")
        assert payload["latest_brief_source_mix"]["google_news"] == 1
        assert "Current Events Brief" in payload["latest_brief_preview"]
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_knowledge_readiness_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "memory" / "gateway.sqlite3"))
    (tmp_path / "memory" / "automation").mkdir(parents=True, exist_ok=True)
    (tmp_path / "knowledge" / "current_events").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "automation" / "realtime_schedule.json").write_text(
        json.dumps([{"job_id": "knowledge-research-auto-v2", "interval_minutes": 15, "inputs": {"trigger": "realtime", "goal": ""}}]),
        encoding="utf-8",
    )
    save_source_config({"brave": {"enabled": True, "news_count": 4, "web_count": 5}})
    append_research_history(
        "knowledge-research-auto-v2",
        topic="current events brief",
        file_path="knowledge/current_events/brief-2026-03-13.md",
        source_count=1,
    )
    (tmp_path / "knowledge" / "current_events" / "brief-2026-03-13.md").write_text(
        "# Current Events Brief\n\n1. **Headline** - https://example.com\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("operator_console.server.app.services.knowledge_service.get_stats", lambda: {"total_documents": 3, "by_category": []})

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/knowledge/readiness")
        assert response.status_code == 200
        payload = response.json()
        assert payload["ready"] is True
        assert payload["checks"]["schedule_enabled"] is True
        assert payload["checks"]["source_enabled"] is True
        assert payload["summary"]["enabled_sources"] == ["brave"]
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_knowledge_sources_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "memory" / "gateway.sqlite3"))
    save_source_config(
        {
            "brave": {"enabled": True, "news_count": 6, "web_count": 3},
            "google_news": {"enabled": True, "news_count": 2, "hl": "en-CA", "gl": "CA", "ceid": "CA:en"},
            "local_news": {"enabled": True, "urls": ["https://local.test/rss.xml"], "timeout_s": 5},
        }
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/knowledge/sources")
        assert response.status_code == 200
        payload = response.json()
        assert payload["sources"]["brave"]["enabled"] is True
        assert payload["sources"]["brave"]["news_count"] == 6
        assert payload["sources"]["google_news"]["enabled"] is True
        assert payload["sources"]["google_news"]["hl"] == "en-CA"
        assert payload["sources"]["google_news"]["gl"] == "CA"
        assert payload["sources"]["local_news"]["enabled"] is True
        assert payload["sources"]["local_news"]["url_count"] == 1
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_knowledge_sources_save_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "memory" / "gateway.sqlite3"))

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/knowledge/sources",
            json={
                "sources": {
                    "brave": {"enabled": True, "news_count": 7, "web_count": 4},
                    "google_news": {"enabled": True, "news_count": 3, "hl": "en-CA", "gl": "CA", "ceid": "CA:en"},
                    "local_news": {"enabled": True, "urls": ["https://local.test/rss.xml", ""], "timeout_s": 5},
                }
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["sources"]["brave"]["news_count"] == 7
        assert payload["sources"]["google_news"]["enabled"] is True
        assert payload["sources"]["google_news"]["gl"] == "CA"
        assert payload["sources"]["local_news"]["url_count"] == 1

        control = client.get("/api/v1/knowledge/sources")
        saved = control.json()["sources"]
        assert saved["brave"]["web_count"] == 4
        assert saved["google_news"]["ceid"] == "CA:en"
        assert saved["local_news"]["urls"] == ["https://local.test/rss.xml"]
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_knowledge_sources_probe_endpoint(monkeypatch):
    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        monkeypatch.setattr(
            "operator_console.server.app.api.knowledge.probe_source_config",
            lambda query: {
                "query": query or "AI agents infrastructure current events",
                "sources": {
                    "brave": {"enabled": True, "news_count": 2, "web_count": 2, "sample_titles": ["Brave one"]},
                    "google_news": {"enabled": True, "news_count": 1, "sample_titles": ["Google one"]},
                    "local_news": {"enabled": False, "url_count": 0, "news_count": 0, "sample_titles": []},
                },
            },
        )
        response = client.post("/api/v1/knowledge/sources/probe", json={"query": "agent infra"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["query"] == "agent infra"
        assert payload["sources"]["brave"]["web_count"] == 2
        assert payload["sources"]["google_news"]["sample_titles"] == ["Google one"]
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_workflow_manual_run_accepts_goal_override(monkeypatch):
    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        monkeypatch.setattr("operator_console.server.app.api.workflows._workspace_root", lambda: Path("."))
        monkeypatch.setattr("operator_console.server.app.api.workflows.enforce_release_gate", lambda **kwargs: {"ok": True})
        monkeypatch.setattr(
            "operator_console.server.app.api.workflows.read_scheduled_dag",
            lambda root, job_id: {"dag": {"workflow_id": job_id, "inputs": {"goal": "", "trigger": "manual"}, "nodes": []}},
        )

        captured = {}

        def _submit_run(dag):
            captured["dag"] = dag
            return {"ok": True, "run_id": "run-knowledge-1", "status": "queued"}

        monkeypatch.setattr("operator_console.server.app.api.workflows.submit_run", _submit_run)
        response = client.post(
            "/api/v1/workflows/scheduled-jobs/knowledge-research-auto-v2/run",
            json={"goal": "operator-specified deep dive"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["goal"] == "operator-specified deep dive"
        assert captured["dag"]["inputs"]["goal"] == "operator-specified deep dive"
    finally:
        app.dependency_overrides.pop(require_api_key, None)
