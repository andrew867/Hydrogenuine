"""Pack 12: Document and chunk data models. All entities include tenant_id."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

PARSE_STATUS_PENDING = "pending"
PARSE_STATUS_PARSED = "parsed"
PARSE_STATUS_FAILED = "failed"

JOB_TYPE_PARSE = "parse"
JOB_TYPE_INDEX = "index"
JOB_TYPE_EXPORT = "export"
JOB_STATUS_PENDING = "pending"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"


@dataclass
class Document:
    document_id: str
    tenant_id: str
    filename: str
    mime: str
    size_bytes: int
    sha256: str
    created_at: str
    created_by: Optional[str] = None
    chat_id: Optional[str] = None
    parse_status: str = PARSE_STATUS_PENDING
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentPage:
    document_id: str
    page_no: int
    text: str
    sha256: Optional[str] = None


@dataclass
class DocumentChunk:
    chunk_id: str
    document_id: str
    tenant_id: str
    text: str
    tokens_est: int
    page_start: int
    page_end: int
    chunk_sha256: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None


@dataclass
class DocumentJob:
    job_id: str
    tenant_id: str
    job_type: str
    status: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    error: Optional[str] = None
    document_id: Optional[str] = None
