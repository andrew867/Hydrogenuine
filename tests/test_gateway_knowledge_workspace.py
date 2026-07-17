import os

import pytest
from fastapi.testclient import TestClient

from hg_core.docs import store as docs_store_module
from hg_gateway.auth import get_tenant_context, verify_api_key
from hg_gateway.main import app
from hg_gateway.store import get_store
from hg_gateway import store as gateway_store_module


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


def _seed_document(chat_id: str, title: str = "chapters.pdf", chapter_count: int = 4) -> str:
    doc_store = docs_store_module.get_document_store()
    document_id = doc_store.document_create(
        "default",
        filename=title,
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
            text=f"Chapter {chapter} discusses topic {chapter}.",
            tokens_est=64,
            page_start=chapter,
            page_end=chapter,
            provenance={"section": f"Chapter {chapter}"},
        )
    doc_store.chat_attach_documents("default", chat_id, [document_id])
    return document_id


def test_knowledge_workspace_returns_documents_and_runs(client):
    store = get_store()
    chat_id = store.chat_create("default", title="Workspace chat")
    document_id = _seed_document(chat_id, chapter_count=3)
    store.message_add(
        "default",
        chat_id,
        "tool",
        "Planned research workflow for VOCM",
        tool_name="planner.plan",
        tool_payload={
            "mode": "research_summary",
            "original_request": "Find VOCM stories this week",
            "query": "VOCM stories this week",
            "kind": "news",
        },
        tool_result={
            "template": "planned_research_summary_v1",
            "confidence": 0.91,
            "dag": {"graph_id": "planned_research_summary_v1", "inputs": {"query_variants": ["VOCM stories this week", "VOCM latest"]}, "nodes": [{"id": "a"}, {"id": "b"}]},
        },
    )
    store.message_add(
        "default",
        chat_id,
        "assistant",
        "Here are the top stories.",
    )
    store.message_add(
        "default",
        chat_id,
        "tool",
        "Planned document decomposition",
        tool_name="planner.plan",
        tool_payload={
            "mode": "document_decomposition",
            "document_id": document_id,
            "segments": [{"segment_id": "segment_1"}, {"segment_id": "segment_2"}, {"segment_id": "segment_3"}],
        },
        tool_result={
            "template": "planned_document_review_fanout_v1",
            "confidence": 0.88,
            "dag": {"graph_id": "planned_document_review_fanout_v1", "inputs": {"segment_labels": ["Chapter 1", "Chapter 2", "Chapter 3"]}, "nodes": [{"id": "a"}]},
        },
    )
    store.message_add(
        "default",
        chat_id,
        "tool",
        "Spawned 3 document agents.",
        tool_name="swarm.run",
        tool_result={"swarm_run_id": "swarm-123", "segment_count": 3, "document_id": document_id},
    )
    store.message_add(
        "default",
        chat_id,
        "assistant",
        "Multiple agents reviewed different document segments and the combined summary is ready.",
    )

    response = client.get(f"/v1/chats/{chat_id}/knowledge-workspace")

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["chat"]["chat_id"] == chat_id
    assert len(data["documents"]) == 1
    assert data["documents"][0]["document_id"] == document_id
    assert len(data["documents"][0]["segments"]) == 3
    assert len(data["research_runs"]) == 1
    assert data["research_runs"][0]["plan_template"] == "planned_research_summary_v1"
    assert data["research_runs"][0]["query"] == "VOCM stories this week"
    assert len(data["document_runs"]) == 1
    assert data["document_runs"][0]["plan_template"] == "planned_document_review_fanout_v1"
    assert data["document_runs"][0]["swarm_run_id"] == "swarm-123"


def test_research_plan_preview_returns_template(client):
    store = get_store()
    chat_id = store.chat_create("default", title="Research preview")

    response = client.post(
        f"/v1/chats/{chat_id}/knowledge-workspace/research-plan-preview",
        json={"content": "Search online and summarize the latest VOCM headlines this week."},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["detected"] is True
    assert data["plan"]["template"] == "planned_research_summary_v1"


def test_document_plan_preview_returns_segments(client):
    store = get_store()
    chat_id = store.chat_create("default", title="Document preview")
    document_id = _seed_document(chat_id, chapter_count=5)

    response = client.post(
        f"/v1/chats/{chat_id}/knowledge-workspace/document-plan-preview",
        json={
            "content": "Read the attached document in parallel and summarize each chapter before the big picture.",
            "document_id": document_id,
            "requested_count": 5,
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["detected"] is True
    assert data["document"]["document_id"] == document_id
    assert len(data["document_request"]["segments"]) == 5
    assert data["plan"]["template"] == "planned_document_review_fanout_v1"


def test_recent_knowledge_workspaces_returns_tenant_feed(client):
    store = get_store()
    chat_id = store.chat_create("default", title="Recent workspace")
    store.message_add(
        "default",
        chat_id,
        "tool",
        "Planned research workflow",
        tool_name="planner.plan",
        tool_payload={"mode": "research_summary", "original_request": "Find me VOCM headlines", "query": "VOCM headlines", "kind": "news"},
        tool_result={"template": "planned_research_summary_v1", "confidence": 0.9, "dag": {"graph_id": "planned_research_summary_v1", "inputs": {}, "nodes": []}},
    )
    store.message_add("default", chat_id, "assistant", "Here are the headlines.")

    response = client.get("/v1/knowledge-workspaces/recent?limit=5")

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert len(items) >= 1
    assert items[0]["chat_id"] == chat_id
    assert items[0]["kind"] == "research_summary"
