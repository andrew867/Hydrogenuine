from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from operator_console.server.app.core.auth import require_api_key
from operator_console.server.app.main import app


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def test_source_blob_registry_api_inventory_and_versions(monkeypatch, tmp_path: Path) -> None:
    workspace = tmp_path / 'workspace'
    _write(workspace / 'hg_platforms' / 'demo_platform.py', 'def alpha():\n    return 1\n')
    gateway_db = tmp_path / 'gateway.sqlite3'
    monkeypatch.setenv('HG_GATEWAY_STORE', 'sqlite')
    monkeypatch.setenv('HG_GATEWAY_DB_PATH', str(gateway_db))
    monkeypatch.setenv('HG_WORKSPACE', str(workspace))

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        sync_resp = client.post('/api/v1/source-registry/registry/sync', json={'root': str(workspace)})
        assert sync_resp.status_code == 200
        payload = sync_resp.json()
        assert payload['sync']['documents'] == 1
        assert payload['summary']['total_documents'] == 1

        create_resp = client.post(
            '/api/v1/source-registry/registry',
            json={
                'class_key': 'python_source',
                'file_path': 'hg_platforms/api_blob.py',
                'source_text': 'def api_blob():\n    return 2\n',
                'title': 'API Blob',
                'actor_id': 'operator_console',
                'change_summary': 'create source blob',
            },
        )
        assert create_resp.status_code == 200
        created = create_resp.json()['source_blob']
        assert created['title'] == 'API Blob'
        assert (workspace / 'hg_platforms/api_blob.py').read_text(encoding='utf-8') == 'def api_blob():\n    return 2\n'

        save_resp = client.put(
            f"/api/v1/source-registry/registry/{created['source_blob_id']}",
            json={
                'source_text': 'def api_blob():\n    return 3\n',
                'title': 'API Blob',
                'actor_id': 'operator_console',
                'change_summary': 'edit source blob',
            },
        )
        assert save_resp.status_code == 200
        saved = save_resp.json()['source_blob']
        assert saved['versions'][0]['version_number'] == 2

        overview = client.get('/api/v1/source-registry/registry')
        assert overview.status_code == 200
        records = overview.json()['source_blobs']
        assert len(records) == 2
        source_blob_id = created['source_blob_id']

        detail = client.get(f'/api/v1/source-registry/registry/{source_blob_id}')
        assert detail.status_code == 200
        detail_payload = detail.json()['source_blob']
        assert detail_payload['module_path'] == 'hg_platforms.api_blob'
        assert detail_payload['vscode_uri'].startswith('vscode://file/')

        diff = client.get(f'/api/v1/source-registry/registry/{source_blob_id}/diff')
        assert diff.status_code == 200
        assert 'return 3' in diff.json()['diff']['diff_text']

        run_resp = client.post(
            f'/api/v1/source-registry/registry/{source_blob_id}/run',
            json={
                'entrypoint': 'hg_platforms.api_blob',
                'args': [],
                'timeout_s': 20,
                'actor_id': 'operator_console',
                'change_summary': 'sandboxed source run',
            },
        )
        assert run_resp.status_code == 200
        run_payload = run_resp.json()
        assert run_payload['run']['status'] in {'completed', 'failed'}
        assert run_payload['run']['run_id']
        assert run_payload['run']['module_path'] == 'hg_platforms.api_blob'

        detail_after_run = client.get(f'/api/v1/source-registry/registry/{source_blob_id}')
        assert detail_after_run.status_code == 200
        assert detail_after_run.json()['source_blob']['runs']

        archive = client.post(
            f'/api/v1/source-registry/registry/{source_blob_id}/archive',
            json={'actor_id': 'operator_console', 'change_summary': 'archive source blob'},
        )
        assert archive.status_code == 200
        assert archive.json()['source_blob']['latest_status'] == 'archived'

        restore = client.post(
            f'/api/v1/source-registry/registry/{source_blob_id}/restore',
            json={'actor_id': 'operator_console', 'change_summary': 'restore source blob'},
        )
        assert restore.status_code == 200
        assert restore.json()['source_blob']['latest_status'] == 'current'

        versions = client.get(f'/api/v1/source-registry/registry/{source_blob_id}/versions')
        assert versions.status_code == 200
        assert len(versions.json()['versions']) == 4
    finally:
        app.dependency_overrides.pop(require_api_key, None)
