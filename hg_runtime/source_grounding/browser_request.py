"""Source request schema and factory."""

from __future__ import annotations

import hashlib
import json

SCHEMA_VERSION = "source_request_v1"


def create_request(*, run_id: str = "", seed_id: str = "", evidence_gap_id: str = "",
                   query: str = "", purpose: str = "", allowed_domains: list[str] | None = None,
                   denied_domains: list[str] | None = None, requires_login: bool = False,
                   read_only: bool = True, operator_review_required: bool = False) -> dict:
    req = {
        "schema": SCHEMA_VERSION,
        "request_id": "",
        "run_id": run_id,
        "seed_id": seed_id,
        "evidence_gap_id": evidence_gap_id,
        "query": query,
        "purpose": purpose,
        "allowed_domains": allowed_domains or [],
        "denied_domains": denied_domains or [],
        "requires_login": requires_login,
        "read_only": read_only,
        "operator_review_required": operator_review_required,
        "runtime_decision": "",
        "external_effect_authorized": False,
    }
    raw = json.dumps(req, sort_keys=True)
    req["request_id"] = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return req
