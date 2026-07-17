from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from hg_core.ledger import emit
from hg_core.sandbox import create_sandbox_context, destroy_sandbox_context
from hg_gateway.db import get_connection
from hg_gateway.source_blob_registry import (
    get_source_blob_document,
    list_source_blob_inventory,
    record_source_blob_run,
    workspace_root,
    _source_blob_workspace_path,
)


def _run_workspace_root() -> Path:
    root = workspace_root() / "artifacts" / "source-blob-runs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_scope_id(value: str) -> str:
    return value.replace(":", "_").replace("/", "_").replace("\\", "_")


def _sandbox_env(export_root: Path) -> dict[str, str]:
    allowlist = [
        "SystemRoot",
        "WINDIR",
        "COMSPEC",
        "PATH",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "LOCALAPPDATA",
        "APPDATA",
    ]
    env = {key: os.environ[key] for key in allowlist if key in os.environ}
    env["PYTHONPATH"] = str(export_root)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["HG_SOURCE_BLOB_SANDBOX"] = "1"
    env["HG_WORKSPACE"] = str(export_root)
    return env


def materialize_source_blob_workspace(conn: Any, target_root: Path | None = None) -> dict[str, Any]:
    export_root = Path(target_root or tempfile.mkdtemp(prefix="source_blob_workspace_")).resolve()
    export_root.mkdir(parents=True, exist_ok=True)
    inventory = list_source_blob_inventory(conn)
    exported: list[dict[str, Any]] = []
    for row in inventory:
        if not row.get("active", 1):
            continue
        doc = get_source_blob_document(conn, row["source_blob_id"])
        if not doc:
            continue
        versions = doc.get("versions") or []
        source_text = ""
        if versions:
            source_text = str(versions[0].get("source_text") or "")
        if not source_text:
            continue
        target = _source_blob_workspace_path(doc["file_path"], root=export_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        _ensure_package_inits(target.parent, export_root)
        target.write_text(source_text, encoding="utf-8")
        exported.append(
            {
                "source_blob_id": doc["source_blob_id"],
                "file_path": doc["file_path"],
                "module_path": doc["module_path"],
                "workspace_path": str(target),
                "source_sha256": doc.get("source_sha256"),
            }
        )
    return {"workspace_root": str(export_root), "exported": exported, "exported_count": len(exported)}


def _ensure_package_inits(path: Path, workspace_root: Path) -> None:
    current = path.resolve()
    workspace_root = workspace_root.resolve()
    while current != workspace_root and workspace_root in current.parents:
        init_path = current / "__init__.py"
        if not init_path.exists():
            init_path.write_text("", encoding="utf-8")
        current = current.parent


def run_source_blob_module(
    source_blob_id: str,
    *,
    entrypoint: str | None = None,
    args: Iterable[str] | None = None,
    timeout_s: int = 120,
    actor_id: str | None = None,
    change_summary: str | None = None,
) -> dict[str, Any]:
    args_list = [str(arg) for arg in (args or [])]
    with get_connection() as conn:
        doc = get_source_blob_document(conn, source_blob_id)
        if doc is None:
            raise ValueError(f"Unknown source_blob_id: {source_blob_id}")
        if doc.get("class_key") != "python_source":
            raise ValueError(f"Unsupported source blob class for execution: {doc.get('class_key')}")

        safe_prefix = source_blob_id.replace(":", "_").replace("/", "_").replace("\\", "_")
        run_dir = Path(tempfile.mkdtemp(prefix=f"{safe_prefix}_", dir=str(_run_workspace_root())))
        materialized = materialize_source_blob_workspace(conn, run_dir / "workspace")
        sandbox_scope_id = _safe_scope_id(source_blob_id)
        sandbox_id = create_sandbox_context(
            scope={"type": "source_blob", "id": sandbox_scope_id},
            actor={"agent_id": actor_id or "source_blob_registry", "pubkey": "", "key_id": ""},
            workspace_root=Path(materialized["workspace_root"]),
        )
        module_path = entrypoint or str(doc.get("module_path") or "")
        if not module_path:
            raise ValueError(f"Source blob has no module path: {source_blob_id}")
        command = [sys.executable, "-m", module_path, *args_list]
        emit(
            "SOURCE_BLOB_RUN_STARTED",
            "source_blob_run",
            source_blob_id,
            {
                "source_blob_id": source_blob_id,
                "module_path": module_path,
                "entrypoint": entrypoint,
                "args": args_list,
                "command": command,
                "workspace_root": materialized["workspace_root"],
                "sandbox_id": sandbox_id,
            },
            scope={"type": "source_blob", "id": sandbox_scope_id},
            workspace_root=Path(materialized["workspace_root"]),
        )
        try:
            result = subprocess.run(
                command,
                cwd=materialized["workspace_root"],
                env=_sandbox_env(Path(materialized["workspace_root"])),
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            status = "completed" if result.returncode == 0 else "failed"
            run_record = record_source_blob_run(
                conn,
                run_id=str(uuid4()),
                source_blob_id=source_blob_id,
                module_path=module_path,
                entrypoint=entrypoint,
                args=args_list,
                command=command,
                workspace_root=materialized["workspace_root"],
                sandbox_id=sandbox_id,
                status=status,
                returncode=int(result.returncode),
                stdout=result.stdout,
                stderr=result.stderr,
                actor_id=actor_id,
                change_summary=change_summary or "sandboxed source blob run",
                payload={"materialized": materialized},
            )
            emit(
                "SOURCE_BLOB_RUN_COMPLETED",
                "source_blob_run",
                source_blob_id,
                {
                    "source_blob_id": source_blob_id,
                    "module_path": module_path,
                    "sandbox_id": sandbox_id,
                    "status": status,
                    "returncode": int(result.returncode),
                    "stdout": result.stdout[-2000:],
                    "stderr": result.stderr[-2000:],
                    "run_id": run_record["run_id"],
                },
                scope={"type": "source_blob", "id": sandbox_scope_id},
                workspace_root=Path(materialized["workspace_root"]),
            )
            return {
                "ok": result.returncode == 0,
                "run": run_record,
                "materialized": materialized,
            }
        except subprocess.TimeoutExpired as exc:
            run_record = record_source_blob_run(
                conn,
                run_id=str(uuid4()),
                source_blob_id=source_blob_id,
                module_path=module_path,
                entrypoint=entrypoint,
                args=args_list,
                command=command,
                workspace_root=materialized["workspace_root"],
                sandbox_id=sandbox_id,
                status="timeout",
                returncode=-1,
                stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
                stderr=(exc.stderr or "") if isinstance(exc.stderr, str) else "",
                actor_id=actor_id,
                change_summary=change_summary or "sandboxed source blob run timeout",
                payload={"materialized": materialized, "timeout_s": timeout_s},
            )
            emit(
                "SOURCE_BLOB_RUN_TIMED_OUT",
                "source_blob_run",
                source_blob_id,
                {
                    "source_blob_id": source_blob_id,
                    "module_path": module_path,
                    "sandbox_id": sandbox_id,
                    "timeout_s": timeout_s,
                    "run_id": run_record["run_id"],
                },
                scope={"type": "source_blob", "id": sandbox_scope_id},
                workspace_root=Path(materialized["workspace_root"]),
            )
            return {"ok": False, "error": "timeout", "run": run_record, "materialized": materialized}
        except Exception as exc:
            run_record = record_source_blob_run(
                conn,
                run_id=str(uuid4()),
                source_blob_id=source_blob_id,
                module_path=module_path,
                entrypoint=entrypoint,
                args=args_list,
                command=command,
                workspace_root=materialized["workspace_root"],
                sandbox_id=sandbox_id,
                status="failed",
                returncode=-1,
                stdout="",
                stderr=str(exc),
                actor_id=actor_id,
                change_summary=change_summary or "sandboxed source blob run failed",
                payload={"materialized": materialized, "error": str(exc)},
            )
            emit(
                "SOURCE_BLOB_RUN_FAILED",
                "source_blob_run",
                source_blob_id,
                {
                    "source_blob_id": source_blob_id,
                    "module_path": module_path,
                    "sandbox_id": sandbox_id,
                    "error": str(exc),
                    "run_id": run_record["run_id"],
                },
                scope={"type": "source_blob", "id": sandbox_scope_id},
                workspace_root=Path(materialized["workspace_root"]),
            )
            return {"ok": False, "error": str(exc), "run": run_record, "materialized": materialized}
        finally:
            try:
                destroy_sandbox_context(
                    sandbox_id=sandbox_id,
                    scope={"type": "source_blob", "id": sandbox_scope_id},
                    actor={"agent_id": actor_id or "source_blob_registry", "pubkey": "", "key_id": ""},
                    workspace_root=Path(materialized["workspace_root"]),
                )
            finally:
                shutil.rmtree(run_dir, ignore_errors=True)
