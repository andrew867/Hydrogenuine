from __future__ import annotations

import io
import hashlib
import json
import os
import tarfile
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from ops.backup_restore import create_backup, restore_backup, verify_backup, verify_restore


def _make_tenants(root: Path) -> None:
    tenants = root / "memory" / "tenants" / "default"
    tenants.mkdir(parents=True, exist_ok=True)
    (tenants / "note.txt").write_text("tenant data", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_create_backup_sqlite_writes_manifest_and_copies_db(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    db_path = tmp_path / "memory" / "gateway.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_text("sqlite-db", encoding="utf-8")
    _make_tenants(tmp_path)

    out_dir = create_backup(tmp_path)

    assert (out_dir / "gateway.sqlite3").exists()
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["backend"] == "sqlite"
    assert "gateway.sqlite3" in manifest["files"]
    assert "tenants.tar" in manifest["files"]
    summary = verify_backup(out_dir, backend="sqlite")
    assert summary["all_passed"] is True


def test_create_backup_postgres_uses_pg_dump(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HG_GATEWAY_STORE", "postgres")
    monkeypatch.setenv("HG_GATEWAY_POSTGRES_DSN", "postgresql://hg:hg@localhost:5432/hg_demo")
    _make_tenants(tmp_path)

    calls: list[list[str]] = []

    def runner(cmd, check=True, env=None):
        calls.append(list(cmd))
        if "--file" in cmd:
            file_path = Path(cmd[cmd.index("--file") + 1])
            file_path.write_text("dump", encoding="utf-8")
        return CompletedProcess(cmd, 0)

    out_dir = create_backup(tmp_path, backend="postgres", runner=runner)

    assert (out_dir / "gateway.dump").exists()
    assert (out_dir / "gateway.sql").exists()
    assert any(call[0] == "pg_dump" and "--format=custom" in call for call in calls)
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["backend"] == "postgres"
    assert "gateway.dump" in manifest["files"]
    assert "gateway.sql" in manifest["files"]
    summary = verify_backup(out_dir, backend="postgres")
    assert summary["all_passed"] is True


def test_restore_backup_postgres_runs_pg_restore(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HG_GATEWAY_STORE", "postgres")
    monkeypatch.setenv("HG_GATEWAY_POSTGRES_DSN", "postgresql://hg:hg@localhost:5432/hg_demo")
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    (backup_dir / "gateway.dump").write_text("dump", encoding="utf-8")
    (backup_dir / "gateway.sql").write_text("schema", encoding="utf-8")
    tar_path = backup_dir / "tenants.tar"
    with tarfile.open(tar_path, "w") as tar:
        data = b"tenant data"
        info = tarfile.TarInfo("tenants/default/note.txt")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    manifest = {
        "version": 2,
        "backend": "postgres",
        "workspace_root": str(tmp_path),
        "created_at": "2026-03-22T00:00:00Z",
        "files": {
            "gateway.dump": "placeholder",
            "gateway.sql": "placeholder",
            "tenants.tar": "placeholder",
        },
    }
    (backup_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["files"]["gateway.dump"] = _sha256(backup_dir / "gateway.dump")
    manifest["files"]["gateway.sql"] = _sha256(backup_dir / "gateway.sql")
    manifest["files"]["tenants.tar"] = _sha256(tar_path)
    (backup_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    calls: list[list[str]] = []

    def runner(cmd, check=True, env=None):
        calls.append(list(cmd))
        return CompletedProcess(cmd, 0)

    restore_backup(backup_dir, tmp_path, backend="postgres", runner=runner)

    assert any(call[0] == "pg_restore" for call in calls)
    assert (tmp_path / "memory" / "tenants" / "default" / "note.txt").exists()


def test_restore_backup_postgres_uses_sql_fallback_when_dump_missing(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HG_GATEWAY_STORE", "postgres")
    monkeypatch.setenv("HG_GATEWAY_POSTGRES_DSN", "postgresql://hg:hg@localhost:5432/hg_demo")
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    (backup_dir / "gateway.sql").write_text("schema", encoding="utf-8")
    tar_path = backup_dir / "tenants.tar"
    with tarfile.open(tar_path, "w") as tar:
        data = b"tenant data"
        info = tarfile.TarInfo("tenants/default/note.txt")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    manifest = {
        "version": 2,
        "backend": "postgres",
        "workspace_root": str(tmp_path),
        "created_at": "2026-03-22T00:00:00Z",
        "files": {
            "gateway.sql": "placeholder",
            "tenants.tar": "placeholder",
        },
    }
    manifest["files"]["gateway.sql"] = _sha256(backup_dir / "gateway.sql")
    manifest["files"]["tenants.tar"] = _sha256(tar_path)
    (backup_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    calls: list[list[str]] = []

    def runner(cmd, check=True, env=None):
        calls.append(list(cmd))
        return CompletedProcess(cmd, 0)

    restore_backup(backup_dir, tmp_path, backend="postgres", runner=runner)

    assert any(call[0] == "psql" for call in calls)
    assert not any(call[0] == "pg_restore" for call in calls)
    assert (tmp_path / "memory" / "tenants" / "default" / "note.txt").exists()


def test_verify_backup_detects_hash_mismatch(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    db_path = tmp_path / "memory" / "gateway.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_text("sqlite-db", encoding="utf-8")
    out_dir = create_backup(tmp_path)
    (out_dir / "gateway.sqlite3").write_text("tampered", encoding="utf-8")

    summary = verify_backup(out_dir, backend="sqlite")
    assert summary["all_passed"] is False
    assert any(not check["pass"] and check["check"] == "backup_file_hash" for check in summary["checks"])


def test_restore_backup_rejects_invalid_backup(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    db_path = tmp_path / "memory" / "gateway.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_text("sqlite-db", encoding="utf-8")
    backup_dir = create_backup(tmp_path)
    (backup_dir / "manifest.json").write_text("{}", encoding="utf-8")

    with pytest.raises(RuntimeError):
        restore_backup(backup_dir, tmp_path, backend="sqlite", runner=lambda *args, **kwargs: CompletedProcess(args[0], 0))


def test_verify_restore_postgres_checks_schema(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HG_GATEWAY_STORE", "postgres")
    monkeypatch.setenv("HG_GATEWAY_POSTGRES_DSN", "postgresql://hg:hg@localhost:5432/hg_demo")
    _make_tenants(tmp_path)

    class FakeCursor:
        def execute(self, sql):
            self.sql = sql

        def fetchone(self):
            return (12,)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakePsycopg:
        def connect(self, dsn):
            assert dsn.startswith("postgresql://")
            return FakeConn()

    import ops.backup_restore as backup_restore

    monkeypatch.setattr(backup_restore, "psycopg", FakePsycopg())

    summary = verify_restore(tmp_path, backend="postgres")
    assert summary["all_passed"] is True
    assert summary["backend"] == "postgres"
    assert any(check["check"] == "gateway_schema_version" and check["pass"] for check in summary["checks"])
