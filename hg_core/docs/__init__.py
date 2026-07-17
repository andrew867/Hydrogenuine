"""Pack 12: Document ingestion, chunking, retrieval, and office exports. All resources tenant-scoped."""

from hg_core.docs.models import (
    Document,
    DocumentChunk,
    DocumentJob,
    DocumentPage,
)
from hg_core.docs.paths import get_documents_root, get_exports_root
from hg_core.docs.store import DocumentStore, get_document_store

__all__ = [
    "Document",
    "DocumentChunk",
    "DocumentJob",
    "DocumentPage",
    "DocumentStore",
    "get_document_store",
    "get_documents_root",
    "get_exports_root",
]
