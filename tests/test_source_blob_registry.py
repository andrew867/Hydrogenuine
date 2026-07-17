from __future__ import annotations

from pathlib import Path

from hg_gateway.db import get_connection
from hg_gateway.source_blob_registry import (
    archive_source_blob_document,
    compare_source_blob_versions,
    create_source_blob_document,
    get_source_blob_document,
    get_source_blob_inventory_summary,
    inventory_source_blobs,
    list_source_blob_inventory,
    list_source_blob_versions,
    save_source_blob_document,
    sync_source_blob_inventory,
    restore_source_blob_document,
)
from hg_core.source_blob_execution import run_source_blob_module


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def test_source_blob_inventory_and_versioning(tmp_path: Path) -> None:
    workspace = tmp_path / 'workspace'
    file_path = workspace / 'hg_platforms' / 'demo_platform.py'
    _write(file_path, 'def alpha():\n    return 1\n')

    items = inventory_source_blobs(workspace)
    assert len(items) == 1
    item = items[0]
    assert item.class_key == 'python_source'
    assert item.file_path == 'hg_platforms/demo_platform.py'
    assert item.module_path == 'hg_platforms.demo_platform'
    assert item.line_count == 3
    assert item.word_count >= 3

    db_path = tmp_path / 'gateway.sqlite3'
    with get_connection(str(db_path)) as conn:
        summary = sync_source_blob_inventory(conn, root=workspace)
        assert summary['documents'] == 1
        assert summary['versions'] == 1

        overview = get_source_blob_inventory_summary(conn)
        assert overview['total_documents'] == 1
        assert overview['total_versions'] == 1
        assert overview['classes'][0]['class_key'] == 'python_source'

        entries = list_source_blob_inventory(conn)
        assert len(entries) == 1
        source_blob_id = entries[0]['source_blob_id']

        detail = get_source_blob_document(conn, source_blob_id)
        assert detail is not None
        assert detail['title'] == 'demo platform'
        assert detail['versions'][0]['version_number'] == 1
        assert 'def alpha' in detail['versions'][0]['source_text']

        created = create_source_blob_document(
            conn,
            'python_source',
            'hg_platforms/new_blob.py',
            'def created():\n    return 2\n',
            title='new blob',
            actor_id='operator_console',
            change_summary='create source blob',
            root=workspace,
        )
        assert created['title'] == 'new blob'
        assert (workspace / 'hg_platforms/new_blob.py').read_text(encoding='utf-8') == 'def created():\n    return 2\n'

        saved = save_source_blob_document(
            conn,
            created['source_blob_id'],
            'def created():\n    return 3\n',
            actor_id='operator_console',
            change_summary='update source blob',
            root=workspace,
        )
        assert saved['versions'][0]['version_number'] == 2
        assert (workspace / 'hg_platforms/new_blob.py').read_text(encoding='utf-8') == 'def created():\n    return 3\n'
        diff = compare_source_blob_versions(
            conn,
            created['source_blob_id'],
            saved['versions'][1]['version_id'],
            saved['versions'][0]['version_id'],
        )
        assert diff is not None
        assert 'return 3' in diff['diff_text']

        archived = archive_source_blob_document(
            conn,
            created['source_blob_id'],
            actor_id='operator_console',
            change_summary='archive source blob',
        )
        assert archived['latest_status'] == 'archived'
        assert archived['active'] == 0

        restored = restore_source_blob_document(
            conn,
            created['source_blob_id'],
            actor_id='operator_console',
            change_summary='restore source blob',
        )
        assert restored['latest_status'] == 'current'
        assert restored['active'] == 1

        versions = list_source_blob_versions(conn, created['source_blob_id'])
        assert len(versions) == 4


def test_source_blob_run_exports_db_source_and_records_run(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / 'workspace'
    monkeypatch.setenv('HG_WORKSPACE', str(workspace))
    db_path = tmp_path / 'gateway.sqlite3'
    monkeypatch.setenv('HG_GATEWAY_STORE', 'sqlite')
    monkeypatch.setenv('HG_GATEWAY_DB_PATH', str(db_path))
    with get_connection(str(db_path)) as conn:
        create_source_blob_document(
            conn,
            'python_source',
            'hg_platforms/run_demo.py',
            'def main():\n    print("sandbox-ok")\n\nif __name__ == "__main__":\n    main()\n',
            title='run demo',
            actor_id='operator_console',
            change_summary='create run demo',
            root=workspace,
        )
    result = run_source_blob_module(
        'python_source:hg_platforms/run_demo.py',
        actor_id='operator_console',
        change_summary='sandboxed source run test',
        timeout_s=30,
    )
    assert result['ok'] is True
    assert 'sandbox-ok' in (result['run'].get('stdout') or '')
    assert result['run']['status'] == 'completed'
    with get_connection(str(db_path)) as conn:
        detail = get_source_blob_document(conn, 'python_source:hg_platforms/run_demo.py')
        assert detail is not None
        assert detail['vscode_uri'].startswith('vscode://file/')
        assert detail['runs'][0]['run_id'] == result['run']['run_id']
