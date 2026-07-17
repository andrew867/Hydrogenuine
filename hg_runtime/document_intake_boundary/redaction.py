"""DIB redaction helpers."""

from __future__ import annotations

import json
import re
from typing import Any

from hg_runtime.document_intake_boundary.schemas import assert_neutral, neutral_flags, record_hash

SECRET_RE = re.compile(r"(api[_-]?key|password|bearer\s+[a-z0-9._-]+|sk-[a-zA-Z0-9])", re.IGNORECASE)


def secret_scan(payload: Any) -> bool:
    text = json.dumps(payload, sort_keys=True, default=str)
    cleaned = text.replace("secret_redaction_passed", "").replace("secrets_emitted", "")
    return SECRET_RE.search(cleaned) is None


def build_document_redaction_record(*, redaction_id: str, file_id: str, secret_like_content_redacted: bool = False) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "document_redaction_record_v1",
        "redaction_id": redaction_id,
        "file_id": file_id,
        "redaction_is_erasure": False,
        "original_retained": True,
        "secret_like_content_redacted": secret_like_content_redacted,
        "doctrine_note": "Redaction is not erasure.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def redact_text(text: str) -> tuple[str, bool]:
    redacted, count = SECRET_RE.subn("[REDACTED_SECRET_LIKE_TOKEN]", text)
    return redacted, count > 0
