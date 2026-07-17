"""Pack 12: Tenant-scoped artifact paths for documents and exports."""

from __future__ import annotations

import os
from pathlib import Path


def get_documents_root(tenant_id: str) -> Path:
    """Base path for tenant document blobs: <root>/tenants/<tenant_id>/documents."""
    root = os.environ.get("HG_DOCUMENTS_ROOT", "memory/tenants")
    return Path(root) / tenant_id / "documents"


def get_exports_root(tenant_id: str) -> Path:
    """Base path for tenant export artifacts: <root>/tenants/<tenant_id>/exports."""
    root = os.environ.get("HG_DOCUMENTS_ROOT", "memory/tenants")
    return Path(root) / tenant_id / "exports"


def document_blob_path(tenant_id: str, document_id: str, filename: str) -> Path:
    """Path for a single document blob. Creates parent dirs on write."""
    base = get_documents_root(tenant_id) / document_id
    return base / filename
