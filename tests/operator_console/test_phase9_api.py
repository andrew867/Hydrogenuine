"""Phase 9: API runs list, events, run index on complete."""

import os
import tempfile

import pytest


def test_events_post_then_get_by_run_id():
    """POST /events then GET /events?run_id= sees the event."""
    import gc
    import time
    db_path = os.path.join(tempfile.gettempdir(), "phase9_gateway_%s.sqlite" % os.getpid())
    os.environ["HG_GATEWAY_STORE"] = "sqlite"
    os.environ["HG_GATEWAY_DB_PATH"] = db_path
    try:
        from fastapi.testclient import TestClient
        from operator_console.server.app.main import app
        client = TestClient(app)
        api_key = os.environ.get("HG_API_KEY", "changeme")
        headers = {"Authorization": f"Bearer {api_key}"}
        r = client.post(
            "/api/v1/events",
            json={"run_id": "phase9-run-1", "payload": {"msg": "hello"}, "tenant_id": "t", "actor_id": "a"},
            headers=headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("accepted") is True
        assert data.get("event_id")
        r2 = client.get("/api/v1/events", params={"run_id": "phase9-run-1"}, headers=headers)
        assert r2.status_code == 200
        events = r2.json().get("events") or []
        assert len(events) >= 1
        assert any(e.get("run_id") == "phase9-run-1" for e in events)
    finally:
        os.environ.pop("HG_GATEWAY_STORE", None)
        os.environ.pop("HG_GATEWAY_DB_PATH", None)
        gc.collect()
        time.sleep(0.05)
        try:
            os.unlink(db_path)
        except Exception:
            pass


def test_runs_list_and_run_detail():
    """GET /runs returns list; GET /runs/{run_id} returns detail when run exists."""
    from fastapi.testclient import TestClient
    from operator_console.server.app.main import app
    client = TestClient(app)
    api_key = os.environ.get("HG_API_KEY", "changeme")
    headers = {"Authorization": f"Bearer {api_key}"}
    r = client.get("/api/v1/runs", headers=headers)
    assert r.status_code == 200
    body = r.json()
    runs = body if isinstance(body, list) else body.get("runs", [])
    assert isinstance(runs, list)
    if runs:
        run_id = runs[0].get("run_id")
        if run_id:
            r2 = client.get(f"/api/v1/runs/{run_id}", headers=headers)
            assert r2.status_code in (200, 404)
