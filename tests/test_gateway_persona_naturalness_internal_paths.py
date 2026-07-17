import os

import pytest
from fastapi.testclient import TestClient

from hg_core.docs import store as docs_store_module
from hg_gateway.auth import get_tenant_context, verify_api_key
from hg_gateway.main import app
from hg_gateway import routes as routes_module
from hg_gateway import store as gateway_store_module
from hg_gateway.store import get_store


def _install_mock_registry(monkeypatch, response_text: str) -> None:
    async def mock_stream(*, messages, **kwargs):
        yield response_text

    class MockRegistry:
        def stream_complete(self, *args, **kwargs):
            return mock_stream(*args, **kwargs)

    try:
        import hg_llm
    except ImportError:
        pytest.skip("hg_llm not installed")
    monkeypatch.setattr(hg_llm, "get_default_registry", lambda: MockRegistry())


def _seed_document(chat_id: str, chapter_count: int = 3) -> str:
    doc_store = docs_store_module.get_document_store()
    document_id = doc_store.document_create(
        "default",
        filename="chapters.pdf",
        mime="application/pdf",
        size_bytes=4096,
        sha256="abc123",
        chat_id=chat_id,
        meta={},
    )
    for idx in range(chapter_count):
        chapter = idx + 1
        doc_store.chunk_upsert(
            "default",
            document_id,
            chunk_id=f"chunk_{chapter}",
            text=f"Chapter {chapter} discusses topic {chapter} in concrete detail.",
            tokens_est=64,
            page_start=chapter,
            page_end=chapter,
            provenance={"section": f"Chapter {chapter}"},
        )
    doc_store.chat_attach_documents("default", chat_id, [document_id])
    return document_id


@pytest.fixture
def client(tmp_path):
    gateway_store_module._store = None
    docs_store_module._document_store = None
    os.environ["HG_GATEWAY_DB_PATH"] = str(tmp_path / "gateway.sqlite3")
    app.dependency_overrides[verify_api_key] = lambda: None
    app.dependency_overrides[get_tenant_context] = lambda: type("TC", (), {"tenant_id": "default"})()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
        app.dependency_overrides.pop(get_tenant_context, None)
        os.environ.pop("HG_GATEWAY_DB_PATH", None)
        gateway_store_module._store = None
        docs_store_module._document_store = None


def test_weather_swarm_records_member_and_orchestrator_naturalness(monkeypatch, client):
    _install_mock_registry(monkeypatch, response_text="Weather summary with live evidence.")
    monkeypatch.setattr(routes_module, "_requires_approval", lambda *args, **kwargs: False)
    monkeypatch.setattr(
        routes_module,
        "_fetch_open_meteo_snapshot",
        lambda lat, lon: {
            "temperature_2m": 3.2,
            "relative_humidity_2m": 80,
            "wind_speed_10m": 12.4,
            "weather_code": 3,
            "precipitation": 0.0,
            "fetched_at": "2026-03-05T12:00:00Z",
            "source": "open-meteo",
        },
    )
    store = get_store()
    chat_id = store.chat_create("default", title="Weather swarm", fingerprint_id="nikola_tesla")

    response = client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"content": "Tesla, can you have multiple agents check the weather in British Columbia and Alberta and summarize it here?"},
    )

    assert response.status_code == 200, response.text
    swarm_run_id = store.chat_get("default", chat_id)["swarm_run_id"]
    summary = store.persona_naturalness_swarm_summary("default", swarm_run_id)
    assert summary["summary"]["total_turns"] == 3
    assert summary["orchestrator"]["chat_id"] == chat_id
    assert len(summary["members"]) == 2


def test_document_decomposition_records_member_and_orchestrator_naturalness(monkeypatch, client):
    _install_mock_registry(monkeypatch, response_text="Document review summary.")
    monkeypatch.setattr(routes_module, "_requires_approval", lambda *args, **kwargs: False)
    store = get_store()
    chat_id = store.chat_create("default", title="Doc swarm", fingerprint_id="nikola_tesla")
    document_id = _seed_document(chat_id, chapter_count=3)

    response = client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"content": "Tesla, get three agents to read the three chapters of the attached PDF and summarize it here."},
    )

    assert response.status_code == 200, response.text
    assert response.json()["document_decomposition"] == {"document_id": document_id, "segment_count": 3}
    swarm_run_id = store.chat_get("default", chat_id)["swarm_run_id"]
    summary = store.persona_naturalness_swarm_summary("default", swarm_run_id)
    assert summary["summary"]["total_turns"] == 4
    assert summary["orchestrator"]["chat_id"] == chat_id
    assert len(summary["members"]) == 3


def test_approved_chat_turn_continuation_records_naturalness(monkeypatch, client):
    _install_mock_registry(monkeypatch, response_text="Approved continuation reply.")
    monkeypatch.setattr(routes_module, "_requires_approval", lambda *args, **kwargs: True)
    store = get_store()
    chat_id = store.chat_create("default", title="Approval path", fingerprint_id="ada_lovelace")

    initial = client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"content": "Explain what the machine could become."},
    )

    assert initial.status_code == 202, initial.text
    approval_id = initial.json()["pending_approval_id"]

    approved = client.post(f"/v1/approvals/{approval_id}/approve", json={"note": "go"})

    assert approved.status_code == 200, approved.text
    rows = store.persona_naturalness_list("default", chat_id=chat_id)
    assert len(rows) == 1
    assert rows[0]["fingerprint_id"] == "ada_lovelace"
