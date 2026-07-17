import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from hg_core.docs import store as docs_store_module
from hg_gateway.auth import get_tenant_context, verify_api_key
from hg_gateway.main import app
from hg_gateway.store import get_store
from hg_gateway import store as gateway_store_module
from hg_core.task_graph import DagPlanner, validate_dag_with_diagnostics
from hg_gateway.routes import _extract_requested_parallel_count


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


def _seed_document(chat_id: str, chapter_count: int = 5) -> str:
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


def test_document_segments_endpoint_groups_by_section(client):
    store = get_store()
    chat_id = store.chat_create("default", title="Doc chat")
    document_id = _seed_document(chat_id, chapter_count=4)

    response = client.get(f"/v1/documents/{document_id}/segments")

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["document_id"] == document_id
    assert [segment["label"] for segment in data["segments"]] == [
        "Chapter 1",
        "Chapter 2",
        "Chapter 3",
        "Chapter 4",
    ]


def test_documents_list_returns_attached_documents_for_chat(client):
    store = get_store()
    chat_id = store.chat_create("default", title="Attached docs")
    document_id = _seed_document(chat_id, chapter_count=2)

    response = client.get(f"/v1/documents?chat_id={chat_id}")

    assert response.status_code == 200, response.text
    documents = response.json()["documents"]
    assert len(documents) == 1
    assert documents[0]["document_id"] == document_id


def test_planner_selects_document_review_fanout_template():
    planner = DagPlanner()

    result = planner.plan(
        "Get five agents to read the five chapters of the attached PDF and summarize it.",
        context={
            "attached_documents": True,
            "segment_count": 5,
            "inputs": {
                "document_id": "doc-1",
                "filename": "chapters.pdf",
                "segment_ids": [f"segment_{idx}" for idx in range(1, 6)],
                "segment_labels": [f"Chapter {idx}" for idx in range(1, 6)],
            },
        },
    )

    assert result.dag is not None
    assert result.dag["graph_id"] == "planned_document_review_fanout_v1"
    assert len(result.diagnostics) == 0
    assert validate_dag_with_diagnostics(result.dag, strict=False)["ok"] is True


def test_extract_requested_parallel_count_prefers_highest_requested_agent_count():
    content = "Get five agents to read the five chapters of the attached PDF and summarize it in one answer."
    assert _extract_requested_parallel_count(content) == 5


@patch("hg_gateway.routes.run_turn", new_callable=AsyncMock)
@patch("hg_gateway.routes._requires_approval", return_value=False)
def test_chat_message_document_decomposition_reduces_into_parent(
    _mock_requires_approval,
    mock_run_turn,
    client,
):
    store = get_store()
    chat_id = store.chat_create("default", title="Doc swarm", fingerprint_id="tesla")
    document_id = _seed_document(chat_id, chapter_count=5)
    mock_run_turn.side_effect = [
        type("Row", (), {"message_id": "m1", "chat_id": "child-1", "role": "assistant", "created_at": "t", "content": "Chapter 1 says topic one is urgent.", "agent_id": "primary"})(),
        type("Row", (), {"message_id": "m2", "chat_id": "child-2", "role": "assistant", "created_at": "t", "content": "Chapter 2 says topic two is constrained.", "agent_id": "primary"})(),
        type("Row", (), {"message_id": "m3", "chat_id": "child-3", "role": "assistant", "created_at": "t", "content": "Chapter 3 says topic three needs review.", "agent_id": "primary"})(),
        type("Row", (), {"message_id": "m4", "chat_id": "child-4", "role": "assistant", "created_at": "t", "content": "Chapter 4 says topic four is approved.", "agent_id": "primary"})(),
        type("Row", (), {"message_id": "m5", "chat_id": "child-5", "role": "assistant", "created_at": "t", "content": "Chapter 5 says topic five is next.", "agent_id": "primary"})(),
        type("Row", (), {"message_id": "m6", "chat_id": chat_id, "role": "assistant", "created_at": "t", "content": "Multiple agents reviewed different document segments and the combined summary is ready.", "agent_id": "primary"})(),
    ]

    response = client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"content": "Tesla, get five agents to read the five chapters of the attached PDF and summarize it here."},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["document_decomposition"] == {"document_id": document_id, "segment_count": 5}
    assert data["message"]["chat_id"] == chat_id
    assert "different document segments" in data["message"]["content"]

    parent_messages = client.get(f"/v1/chats/{chat_id}/messages").json()["messages"]
    assert any(msg.get("tool_name") == "planner.plan" for msg in parent_messages)
    assert any(msg.get("tool_name") == "swarm.run" for msg in parent_messages)

    all_chats = client.get("/v1/chats").json()["chats"]
    children = [chat for chat in all_chats if chat.get("swarm_run_id") and chat.get("swarm_role") == "entity"]
    assert len(children) == 5
    for child in children:
        child_messages = client.get(f"/v1/chats/{child['chat_id']}/messages").json()["messages"]
        assert any(msg.get("tool_name") == "document.segment_assign" for msg in child_messages)


@patch("hg_gateway.routes.run_turn", new_callable=AsyncMock)
@patch("hg_gateway.routes._requires_approval", return_value=True)
def test_document_decomposition_approval_resume(
    _mock_requires_approval,
    mock_run_turn,
    client,
):
    store = get_store()
    chat_id = store.chat_create("default", title="Doc approval", fingerprint_id="tesla")
    document_id = _seed_document(chat_id, chapter_count=3)
    mock_run_turn.side_effect = [
        type("Row", (), {"message_id": "m1", "chat_id": "child-1", "role": "assistant", "created_at": "t", "content": "Chapter 1 summary.", "agent_id": "primary"})(),
        type("Row", (), {"message_id": "m2", "chat_id": "child-2", "role": "assistant", "created_at": "t", "content": "Chapter 2 summary.", "agent_id": "primary"})(),
        type("Row", (), {"message_id": "m3", "chat_id": "child-3", "role": "assistant", "created_at": "t", "content": "Chapter 3 summary.", "agent_id": "primary"})(),
        type("Row", (), {"message_id": "m4", "chat_id": chat_id, "role": "assistant", "created_at": "t", "content": "Multiple agents reviewed different document segments.", "agent_id": "primary"})(),
    ]

    initial = client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"content": "Please have three agents review the attached PDF chapters and summarize them."},
    )

    assert initial.status_code == 202, initial.text
    approval_id = initial.json()["pending_approval_id"]
    approval = store.approval_get("default", approval_id)
    assert approval is not None
    assert approval["payload"]["type"] == "document_decomposition_chat_turn"
    assert approval["payload"]["document_request"]["document_id"] == document_id

    approved = client.post(f"/v1/approvals/{approval_id}/approve", json={"note": "go"})

    assert approved.status_code == 200, approved.text
    data = approved.json()
    assert data["continued"] is True
    assert data["document_decomposition"] == {"document_id": document_id, "segment_count": 3}
    assert "different document segments" in data["message"]["content"]
