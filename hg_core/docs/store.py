"""Pack 12: Document store backed by the shared gateway SQLite database."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from hg_core.docs.models import (
    Document,
    DocumentChunk,
    DocumentJob,
    DocumentPage,
    JOB_STATUS_PENDING,
    JOB_TYPE_PARSE,
    PARSE_STATUS_PENDING,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_load(value: Optional[str], default: Any) -> Any:
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _get_connection():
    from hg_gateway.db import get_connection as gateway_get_connection

    return gateway_get_connection()


class DocumentStore:
    """SQLite-backed document store. Every method is tenant-scoped."""

    def __init__(self) -> None:
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with _get_connection() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS chat_attachments (
                tenant_id TEXT NOT NULL,
                chat_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, chat_id, document_id)
                )"""
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_attachments_chat ON chat_attachments(tenant_id, chat_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_attachments_document ON chat_attachments(document_id)")

    def _document_from_row(self, row: Any) -> Document:
        return Document(
            document_id=row["document_id"],
            tenant_id=row["tenant_id"],
            filename=row["filename"],
            mime=row["mime"],
            size_bytes=int(row["size_bytes"]),
            sha256=row["sha256"],
            created_at=row["created_at"],
            created_by=row["created_by"],
            chat_id=row["chat_id"],
            parse_status=row["parse_status"],
            meta=_json_load(row["meta_json"], {}),
        )

    def _chunk_from_row(self, row: Any) -> DocumentChunk:
        return DocumentChunk(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            tenant_id=row["tenant_id"],
            text=row["text"],
            tokens_est=int(row["tokens_est"]),
            page_start=int(row["page_start"]),
            page_end=int(row["page_end"]),
            chunk_sha256=row["chunk_sha256"],
            provenance=_json_load(row["provenance_json"], None),
        )

    def _page_from_row(self, row: Any) -> DocumentPage:
        return DocumentPage(
            document_id=row["document_id"],
            page_no=int(row["page_no"]),
            text=row["text"],
            sha256=row["sha256"],
        )

    def _job_from_row(self, row: Any) -> DocumentJob:
        return DocumentJob(
            job_id=row["job_id"],
            tenant_id=row["tenant_id"],
            job_type=row["job_type"],
            status=row["status"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            error=row["error"],
            document_id=row["document_id"],
        )

    def document_create(
        self,
        tenant_id: str,
        filename: str,
        mime: str,
        size_bytes: int,
        sha256: str,
        created_by: Optional[str] = None,
        chat_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        document_id = str(uuid.uuid4())
        with _get_connection() as conn:
            conn.execute(
                """INSERT INTO documents (
                document_id, tenant_id, chat_id, filename, mime, size_bytes, sha256,
                created_at, created_by, parse_status, meta_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    document_id,
                    tenant_id,
                    chat_id,
                    filename,
                    mime,
                    size_bytes,
                    sha256,
                    _now(),
                    created_by,
                    PARSE_STATUS_PENDING,
                    json.dumps(meta or {}),
                ),
            )
        return document_id

    def document_get(self, tenant_id: str, document_id: str) -> Optional[Document]:
        with _get_connection() as conn:
            row = conn.execute(
                """SELECT document_id, tenant_id, chat_id, filename, mime, size_bytes, sha256,
                          created_at, created_by, parse_status, meta_json
                   FROM documents WHERE tenant_id = ? AND document_id = ?""",
                (tenant_id, document_id),
            ).fetchone()
        return self._document_from_row(row) if row else None

    def document_list(
        self,
        tenant_id: str,
        chat_id: Optional[str] = None,
    ) -> List[Document]:
        with _get_connection() as conn:
            if chat_id is None:
                rows = conn.execute(
                    """SELECT document_id, tenant_id, chat_id, filename, mime, size_bytes, sha256,
                              created_at, created_by, parse_status, meta_json
                       FROM documents WHERE tenant_id = ?
                       ORDER BY created_at DESC""",
                    (tenant_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT d.document_id, d.tenant_id, d.chat_id, d.filename, d.mime, d.size_bytes, d.sha256,
                              d.created_at, d.created_by, d.parse_status, d.meta_json
                       FROM documents d
                       JOIN chat_attachments a
                         ON a.document_id = d.document_id AND a.tenant_id = d.tenant_id
                       WHERE d.tenant_id = ? AND a.chat_id = ?
                       ORDER BY d.created_at DESC""",
                    (tenant_id, chat_id),
                ).fetchall()
        return [self._document_from_row(row) for row in rows]

    def document_update_parse_status(
        self,
        tenant_id: str,
        document_id: str,
        parse_status: str,
    ) -> bool:
        with _get_connection() as conn:
            cur = conn.execute(
                "UPDATE documents SET parse_status = ? WHERE tenant_id = ? AND document_id = ?",
                (parse_status, tenant_id, document_id),
            )
        return cur.rowcount > 0

    def document_update_meta(
        self,
        tenant_id: str,
        document_id: str,
        meta: Dict[str, Any],
    ) -> bool:
        current = self.document_get(tenant_id, document_id)
        if not current:
            return False
        merged = {**(current.meta or {}), **(meta or {})}
        with _get_connection() as conn:
            cur = conn.execute(
                "UPDATE documents SET meta_json = ? WHERE tenant_id = ? AND document_id = ?",
                (json.dumps(merged), tenant_id, document_id),
            )
        return cur.rowcount > 0

    def document_set_chat_id(
        self,
        tenant_id: str,
        document_id: str,
        chat_id: Optional[str],
    ) -> bool:
        with _get_connection() as conn:
            cur = conn.execute(
                "UPDATE documents SET chat_id = ? WHERE tenant_id = ? AND document_id = ?",
                (chat_id, tenant_id, document_id),
            )
        return cur.rowcount > 0

    def chunk_upsert(
        self,
        tenant_id: str,
        document_id: str,
        chunk_id: str,
        text: str,
        tokens_est: int,
        page_start: int,
        page_end: int,
        chunk_sha256: Optional[str] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> None:
        with _get_connection() as conn:
            conn.execute(
                """INSERT INTO document_chunks (
                chunk_id, document_id, tenant_id, text, tokens_est, page_start, page_end, chunk_sha256, provenance_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                  document_id = excluded.document_id,
                  tenant_id = excluded.tenant_id,
                  text = excluded.text,
                  tokens_est = excluded.tokens_est,
                  page_start = excluded.page_start,
                  page_end = excluded.page_end,
                  chunk_sha256 = excluded.chunk_sha256,
                  provenance_json = excluded.provenance_json""",
                (
                    chunk_id,
                    document_id,
                    tenant_id,
                    text,
                    tokens_est,
                    page_start,
                    page_end,
                    chunk_sha256,
                    json.dumps(provenance or {}),
                ),
            )

    def chunk_list(
        self,
        tenant_id: str,
        document_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DocumentChunk]:
        with _get_connection() as conn:
            rows = conn.execute(
                """SELECT chunk_id, document_id, tenant_id, text, tokens_est, page_start, page_end, chunk_sha256, provenance_json
                   FROM document_chunks
                   WHERE tenant_id = ? AND document_id = ?
                   ORDER BY page_start, page_end, chunk_id
                   LIMIT ? OFFSET ?""",
                (tenant_id, document_id, limit, offset),
            ).fetchall()
        return [self._chunk_from_row(row) for row in rows]

    def chunk_list_all(
        self,
        tenant_id: str,
        document_ids: Optional[List[str]] = None,
    ) -> List[Tuple[DocumentChunk, str]]:
        params: List[Any] = [tenant_id]
        doc_filter = ""
        if document_ids:
            placeholders = ",".join("?" for _ in document_ids)
            doc_filter = f"AND c.document_id IN ({placeholders})"
            params.extend(document_ids)
        with _get_connection() as conn:
            rows = conn.execute(
                f"""SELECT c.chunk_id, c.document_id, c.tenant_id, c.text, c.tokens_est, c.page_start, c.page_end,
                           c.chunk_sha256, c.provenance_json, d.filename
                    FROM document_chunks c
                    JOIN documents d ON d.document_id = c.document_id AND d.tenant_id = c.tenant_id
                    WHERE c.tenant_id = ? {doc_filter}
                    ORDER BY c.page_start, c.page_end, c.chunk_id""",
                params,
            ).fetchall()
        return [(self._chunk_from_row(row), row["filename"]) for row in rows]

    def page_upsert(
        self,
        document_id: str,
        page_no: int,
        text: str,
        sha256: Optional[str] = None,
    ) -> None:
        tenant_id = self.tenant_for_document(document_id) or "default"
        with _get_connection() as conn:
            conn.execute(
                """INSERT INTO document_pages (document_id, page_no, text, sha256)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(document_id, page_no) DO UPDATE SET
                     text = excluded.text,
                     sha256 = excluded.sha256""",
                (document_id, page_no, text, sha256),
            )
            conn.execute(
                "UPDATE documents SET tenant_id = tenant_id WHERE tenant_id = ? AND document_id = ?",
                (tenant_id, document_id),
            )

    def page_list(
        self,
        tenant_id: str,
        document_id: str,
    ) -> List[DocumentPage]:
        with _get_connection() as conn:
            rows = conn.execute(
                """SELECT p.document_id, p.page_no, p.text, p.sha256
                   FROM document_pages p
                   JOIN documents d ON d.document_id = p.document_id
                   WHERE d.tenant_id = ? AND p.document_id = ?
                   ORDER BY p.page_no""",
                (tenant_id, document_id),
            ).fetchall()
        return [self._page_from_row(row) for row in rows]

    def job_create(
        self,
        tenant_id: str,
        job_type: str,
        document_id: Optional[str] = None,
    ) -> str:
        job_id = str(uuid.uuid4())
        with _get_connection() as conn:
            conn.execute(
                """INSERT INTO document_jobs (
                job_id, tenant_id, job_type, status, started_at, ended_at, error, document_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (job_id, tenant_id, job_type, JOB_STATUS_PENDING, None, None, None, document_id),
            )
        return job_id

    def job_get(self, tenant_id: str, job_id: str) -> Optional[DocumentJob]:
        with _get_connection() as conn:
            row = conn.execute(
                """SELECT job_id, tenant_id, job_type, status, started_at, ended_at, error, document_id
                   FROM document_jobs WHERE tenant_id = ? AND job_id = ?""",
                (tenant_id, job_id),
            ).fetchone()
        return self._job_from_row(row) if row else None

    def job_update(
        self,
        tenant_id: str,
        job_id: str,
        status: str,
        started_at: Optional[str] = None,
        ended_at: Optional[str] = None,
        error: Optional[str] = None,
    ) -> bool:
        current = self.job_get(tenant_id, job_id)
        if not current:
            return False
        with _get_connection() as conn:
            cur = conn.execute(
                """UPDATE document_jobs
                   SET status = ?, started_at = ?, ended_at = ?, error = ?
                   WHERE tenant_id = ? AND job_id = ?""",
                (
                    status,
                    started_at if started_at is not None else current.started_at,
                    ended_at if ended_at is not None else current.ended_at,
                    error if error is not None else current.error,
                    tenant_id,
                    job_id,
                ),
            )
        return cur.rowcount > 0

    def tenant_for_document(self, document_id: str) -> Optional[str]:
        with _get_connection() as conn:
            row = conn.execute(
                "SELECT tenant_id FROM documents WHERE document_id = ?",
                (document_id,),
            ).fetchone()
        return row["tenant_id"] if row else None

    def chat_attach_documents(self, tenant_id: str, chat_id: str, document_ids: List[str]) -> None:
        with _get_connection() as conn:
            conn.execute("DELETE FROM chat_attachments WHERE tenant_id = ? AND chat_id = ?", (tenant_id, chat_id))
            for document_id in document_ids:
                conn.execute(
                    """INSERT INTO chat_attachments (tenant_id, chat_id, document_id, created_at)
                       VALUES (?, ?, ?, ?)""",
                    (tenant_id, chat_id, document_id, _now()),
                )

    def chat_get_attachments(self, tenant_id: str, chat_id: str) -> List[str]:
        with _get_connection() as conn:
            rows = conn.execute(
                """SELECT document_id FROM chat_attachments
                   WHERE tenant_id = ? AND chat_id = ?
                   ORDER BY created_at, document_id""",
                (tenant_id, chat_id),
            ).fetchall()
        return [row["document_id"] for row in rows]


_document_store: Optional[DocumentStore] = None


def get_document_store() -> DocumentStore:
    global _document_store
    if _document_store is None:
        _document_store = DocumentStore()
    return _document_store
