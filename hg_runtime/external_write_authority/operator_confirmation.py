"""Operator external write confirmation — separate from review decision."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from hg_runtime.external_write_authority.schema import (
    STORE_ROOT,
    load_policy,
    new_id,
    now_iso,
)


@dataclass
class OperatorExternalWriteConfirmation:
    operator_confirmation_id: str
    operator_ref: str
    candidate_ref: str
    authority_request_ref: str
    confirmation_phrase: str
    confirmed_platform: str
    confirmed_action_type: str
    confirmed_scope: str
    confirmed_content_hash: str
    created_at: str
    expires_at: str
    status: str
    fixture: bool = True
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "operator_confirmation_id": self.operator_confirmation_id,
            "operator_ref": self.operator_ref,
            "candidate_ref": self.candidate_ref,
            "authority_request_ref": self.authority_request_ref,
            "confirmation_phrase": self.confirmation_phrase,
            "confirmed_platform": self.confirmed_platform,
            "confirmed_action_type": self.confirmed_action_type,
            "confirmed_scope": self.confirmed_scope,
            "confirmed_content_hash": self.confirmed_content_hash,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "fixture": self.fixture,
            "hash": self.hash,
        }

    def with_hash(self) -> OperatorExternalWriteConfirmation:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        from hg_core.policy_safety.hashing import compute_record_hash

        return OperatorExternalWriteConfirmation(**{**self.__dict__, "hash": compute_record_hash(body)})

    def is_expired(self, *, at: str | None = None) -> bool:
        ts = at or now_iso()
        try:
            exp = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            cur = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return cur >= exp
        except ValueError:
            return True


APPROVE_ALL_PATTERNS = (
    re.compile(r"^approve\s*all$", re.I),
    re.compile(r"^approve_all$", re.I),
    re.compile(r"^grant\s*all$", re.I),
)


def phrase_is_approve_all(phrase: str) -> bool:
    return any(p.match(phrase.strip()) for p in APPROVE_ALL_PATTERNS)


def _store(run_id: str) -> Path:
    return STORE_ROOT / run_id / "confirmations"


def create_dry_operator_confirmation(
    *,
    run_id: str,
    operator_ref: str,
    candidate_id: str,
    authority_request_id: str,
    phrase: str,
    platform: str,
    action_type: str,
    scope: str,
    content_hash: str,
) -> OperatorExternalWriteConfirmation:
    if phrase_is_approve_all(phrase):
        raise ValueError("approve-all phrase rejected")
    policy = load_policy()
    ttl = int(policy.get("operator_confirmation_ttl_seconds", 900))
    created = now_iso()
    exp = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat()
    conf = OperatorExternalWriteConfirmation(
        operator_confirmation_id=new_id("ext-op-conf"),
        operator_ref=operator_ref,
        candidate_ref=candidate_id,
        authority_request_ref=authority_request_id,
        confirmation_phrase=phrase,
        confirmed_platform=platform,
        confirmed_action_type=action_type,
        confirmed_scope=scope,
        confirmed_content_hash=content_hash,
        created_at=created,
        expires_at=exp,
        status="confirmed",
        fixture=True,
    ).with_hash()
    path = _store(run_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{conf.operator_confirmation_id}.json").write_text(
        json.dumps(conf.to_payload(), indent=2) + "\n", encoding="utf-8"
    )
    return conf


def load_confirmation(run_id: str, confirmation_id: str) -> OperatorExternalWriteConfirmation | None:
    path = _store(run_id) / f"{confirmation_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return OperatorExternalWriteConfirmation(
        operator_confirmation_id=data["operator_confirmation_id"],
        operator_ref=data["operator_ref"],
        candidate_ref=data["candidate_ref"],
        authority_request_ref=data["authority_request_ref"],
        confirmation_phrase=data["confirmation_phrase"],
        confirmed_platform=data["confirmed_platform"],
        confirmed_action_type=data["confirmed_action_type"],
        confirmed_scope=data["confirmed_scope"],
        confirmed_content_hash=data["confirmed_content_hash"],
        created_at=data["created_at"],
        expires_at=data["expires_at"],
        status=data["status"],
        fixture=data.get("fixture", True),
        hash=data.get("hash"),
    )
