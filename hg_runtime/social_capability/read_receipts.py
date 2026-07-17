"""Live read receipts — mandatory proof of what was read."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.social_capability.source_refs import validate_source_refs


class LiveReadCredentialStatus(str, Enum):
    CREDENTIALS_PRESENT = "credentials_present"
    CREDENTIALS_MISSING = "credentials_missing"
    CREDENTIALS_INVALID = "credentials_invalid"
    CREDENTIALS_UNCHECKED = "credentials_unchecked"
    CREDENTIALS_REDACTED = "credentials_redacted"


class LiveReadVerdict(str, Enum):
    GREEN_LIVE_READ_OK = "GREEN_LIVE_READ_OK"
    YELLOW_CREDENTIALS_MISSING = "YELLOW_CREDENTIALS_MISSING"
    YELLOW_CREDENTIALS_INVALID = "YELLOW_CREDENTIALS_INVALID"
    YELLOW_LIVE_API_UNREACHABLE = "YELLOW_LIVE_API_UNREACHABLE"
    YELLOW_LIVE_API_RATE_LIMITED = "YELLOW_LIVE_API_RATE_LIMITED"
    YELLOW_NO_ITEMS_RETURNED = "YELLOW_NO_ITEMS_RETURNED"
    YELLOW_LIVE_READ_DISABLED = "YELLOW_LIVE_READ_DISABLED"
    RED_FIXTURE_FEED_USED_IN_RUNTIME = "RED_FIXTURE_FEED_USED_IN_RUNTIME"
    RED_LIVE_READ_WITHOUT_RECEIPT = "RED_LIVE_READ_WITHOUT_RECEIPT"
    RED_WRITE_ACTION_ATTEMPTED = "RED_WRITE_ACTION_ATTEMPTED"
    RED_EMPTY_SUCCESS = "RED_EMPTY_SUCCESS"


FORBIDDEN_RECEIPT_KEYS = frozenset({
    "token",
    "api_key",
    "password",
    "secret",
    "credential_value",
    "hg_moltbook_token",
    "hg_fourclaw_token",
})


@dataclass(frozen=True)
class LiveReadReceipt:
    receipt_id: str
    request_id: str
    surface: str
    runtime_mode: str
    fixture_mode: bool
    credential_status: LiveReadCredentialStatus
    api_called: bool
    api_call_kind: str
    item_count: int
    source_refs: tuple[str, ...]
    read_started_at: str
    read_finished_at: str
    latency_ms: int
    verdict: LiveReadVerdict
    error: str | None = None
    hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "receipt_id": self.receipt_id,
            "request_id": self.request_id,
            "surface": self.surface,
            "runtime_mode": self.runtime_mode,
            "fixture_mode": self.fixture_mode,
            "credential_status": self.credential_status.value,
            "api_called": self.api_called,
            "api_call_kind": self.api_call_kind,
            "item_count": self.item_count,
            "source_refs": list(self.source_refs),
            "read_started_at": self.read_started_at,
            "read_finished_at": self.read_finished_at,
            "latency_ms": self.latency_ms,
            "verdict": self.verdict.value,
            "error": self.error,
            "hash": self.hash,
        }
        for key in FORBIDDEN_RECEIPT_KEYS:
            payload.pop(key, None)
        return payload


def build_live_read_receipt(
    *,
    request_id: str,
    surface: str,
    runtime_mode: str,
    fixture_mode: bool,
    credential_status: LiveReadCredentialStatus,
    api_called: bool,
    api_call_kind: str,
    item_count: int,
    source_refs: list[str],
    read_started_at: str,
    read_finished_at: str,
    latency_ms: int,
    verdict: LiveReadVerdict,
    error: str | None = None,
    receipt_id: str | None = None,
) -> LiveReadReceipt:
    """Build live read receipt with deterministic hash."""
    rid = receipt_id or f"live-read-{uuid.uuid4().hex[:16]}"
    body = {
        "receipt_id": rid,
        "request_id": request_id,
        "surface": surface,
        "runtime_mode": runtime_mode,
        "fixture_mode": fixture_mode,
        "credential_status": credential_status.value,
        "api_called": api_called,
        "api_call_kind": api_call_kind,
        "item_count": item_count,
        "source_refs": list(source_refs),
        "read_started_at": read_started_at,
        "read_finished_at": read_finished_at,
        "latency_ms": latency_ms,
        "verdict": verdict.value,
        "error": error,
    }
    digest = compute_record_hash(body)
    return LiveReadReceipt(
        receipt_id=rid,
        request_id=request_id,
        surface=surface,
        runtime_mode=runtime_mode,
        fixture_mode=fixture_mode,
        credential_status=credential_status,
        api_called=api_called,
        api_call_kind=api_call_kind,
        item_count=item_count,
        source_refs=tuple(source_refs),
        read_started_at=read_started_at,
        read_finished_at=read_finished_at,
        latency_ms=latency_ms,
        verdict=verdict,
        error=error,
        hash=digest,
    )


def validate_live_read_receipt(receipt: LiveReadReceipt | None) -> LiveReadVerdict:
    """Validate receipt invariants — no secrets, refs required when items present."""
    if receipt is None:
        return LiveReadVerdict.RED_LIVE_READ_WITHOUT_RECEIPT
    payload = receipt.to_payload()
    for key in payload:
        if key.lower() in FORBIDDEN_RECEIPT_KEYS:
            return LiveReadVerdict.RED_LIVE_READ_WITHOUT_RECEIPT
    if receipt.item_count > 0 and not validate_source_refs(list(receipt.source_refs)):
        return LiveReadVerdict.RED_LIVE_READ_WITHOUT_RECEIPT
    if receipt.verdict == LiveReadVerdict.GREEN_LIVE_READ_OK and receipt.item_count <= 0:
        return LiveReadVerdict.RED_EMPTY_SUCCESS
    expected = compute_record_hash({
        k: v for k, v in payload.items() if k != "hash"
    })
    if receipt.hash and receipt.hash != expected:
        return LiveReadVerdict.RED_LIVE_READ_WITHOUT_RECEIPT
    return receipt.verdict


def verdict_counts_as_success(verdict: LiveReadVerdict) -> bool:
    """Only explicit GREEN with items counts as read success."""
    return verdict == LiveReadVerdict.GREEN_LIVE_READ_OK


__all__ = [
    "LiveReadCredentialStatus",
    "LiveReadReceipt",
    "LiveReadVerdict",
    "build_live_read_receipt",
    "validate_live_read_receipt",
    "verdict_counts_as_success",
]
