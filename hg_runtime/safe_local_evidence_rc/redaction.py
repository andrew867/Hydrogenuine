"""SLE-RC redaction helpers."""

from __future__ import annotations

import json
import re
from typing import Any

from hg_runtime.safe_local_evidence_rc.schemas import assert_neutral, neutral_flags, record_hash

SECRET_RE = re.compile(r"(api[_-]?key|password|bearer\s+[a-z0-9._-]+|sk-[a-zA-Z0-9])", re.IGNORECASE)


def secret_scan(payload: Any) -> bool:
    text = json.dumps(payload, sort_keys=True, default=str)
    cleaned = text.replace("secret_redaction_passed", "").replace("secrets_emitted", "")
    return SECRET_RE.search(cleaned) is None


def build_rc_redaction_record(*, redaction_id: str, target_ref: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "rc_redaction_record_v1",
        "redaction_id": redaction_id,
        "target_ref": target_ref,
        "redaction_is_erasure": False,
        "original_retained": True,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
