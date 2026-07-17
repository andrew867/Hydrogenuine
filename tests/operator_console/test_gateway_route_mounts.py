import io

from fastapi.testclient import TestClient

from hg_gateway.auth import get_tenant_context, verify_api_key
from operator_console.server.app.main import app


def test_operator_api_mounts_gateway_file_and_document_routes():
    app.dependency_overrides[verify_api_key] = lambda: None
    app.dependency_overrides[get_tenant_context] = lambda: type("TC", (), {"tenant_id": "default"})()
    client = TestClient(app)
    try:
        list_response = client.get("/v1/documents")
        assert list_response.status_code == 200, list_response.text
        assert "documents" in list_response.json()

        upload_response = client.post(
            "/v1/files/upload",
            files={"file": ("chapters.docx", io.BytesIO(b"fake"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert upload_response.status_code == 200, upload_response.text
        payload = upload_response.json()
        assert payload["document_id"]
        assert payload["filename"] == "chapters.docx"
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
        app.dependency_overrides.pop(get_tenant_context, None)


def test_operator_api_upload_accepts_docx_when_client_sends_octet_stream():
    app.dependency_overrides[verify_api_key] = lambda: None
    app.dependency_overrides[get_tenant_context] = lambda: type("TC", (), {"tenant_id": "default"})()
    client = TestClient(app)
    try:
        upload_response = client.post(
            "/v1/files/upload",
            files={"file": ("chapters.docx", io.BytesIO(b"fake"), "application/octet-stream")},
        )
        assert upload_response.status_code == 200, upload_response.text
        payload = upload_response.json()
        assert payload["document_id"]
        assert payload["mime"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
        app.dependency_overrides.pop(get_tenant_context, None)
