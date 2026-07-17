"""Provider receipt types — mandatory for cognitive output."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = WORKSPACE / "configs/agent_zero/provider_reality_policy.json"


class ProviderKind(str, Enum):
    LOCAL_OPENVINO = "local_openvino"
    LOCAL_VLLM = "local_vllm"
    CLOUD = "cloud"
    STUB = "stub"
    UNKNOWN = "unknown"


class ProviderMode(str, Enum):
    LIVE = "live"
    DRY_RUN = "dry_run"
    FIXTURE = "fixture"
    FALLBACK_STUB = "fallback_stub"
    PROOF_REPLAY = "proof_replay"
    UNAVAILABLE = "unavailable"


class ProviderStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    REFUSED = "refused"


class ProviderRealityVerdict(str, Enum):
    GREEN_PROVIDER_LIVE_AVAILABLE = "GREEN_PROVIDER_LIVE_AVAILABLE"
    YELLOW_PROVIDER_UNAVAILABLE = "YELLOW_PROVIDER_UNAVAILABLE"
    YELLOW_PROVIDER_DRY_RUN_LABELLED = "YELLOW_PROVIDER_DRY_RUN_LABELLED"
    YELLOW_PROVIDER_PROOF_REPLAY_ONLY = "YELLOW_PROVIDER_PROOF_REPLAY_ONLY"
    RED_PROVIDER_FALLBACK_AS_COGNITION = "RED_PROVIDER_FALLBACK_AS_COGNITION"
    RED_PROVIDER_FIXTURE_AS_COGNITION = "RED_PROVIDER_FIXTURE_AS_COGNITION"
    RED_PROVIDER_EMPTY_OUTPUT = "RED_PROVIDER_EMPTY_OUTPUT"
    RED_PROVIDER_RECEIPT_MISSING = "RED_PROVIDER_RECEIPT_MISSING"
    RED_PROVIDER_IDENTITY_MISSING = "RED_PROVIDER_IDENTITY_MISSING"
    RED_PROVIDER_HASH_MISSING = "RED_PROVIDER_HASH_MISSING"


class ProviderOutputVerdict(str, Enum):
    GREEN_COGNITIVE_OUTPUT_VALID = "GREEN_COGNITIVE_OUTPUT_VALID"
    YELLOW_NON_COGNITIVE_LABELLED = "YELLOW_NON_COGNITIVE_LABELLED"
    RED_OUTPUT_WITHOUT_RECEIPT = "RED_OUTPUT_WITHOUT_RECEIPT"
    RED_OUTPUT_NOT_COGNITION = "RED_OUTPUT_NOT_COGNITION"


@dataclass(frozen=True)
class ProviderReceipt:
    receipt_id: str
    provider_id: str
    provider_kind: ProviderKind
    provider_mode: ProviderMode
    role: str
    request_hash: str
    config_hash: str
    runtime_mode: str
    cognitive_soak_active: bool
    dry_run: bool
    fixture_mode: bool
    status: ProviderStatus
    verdict: ProviderRealityVerdict
    started_at: str
    ended_at: str
    latency_ms: int
    model_id: str | None = None
    response_hash: str | None = None
    token_count: int | None = None
    output_bytes: int | None = None
    error: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "provider_id": self.provider_id,
            "provider_kind": self.provider_kind.value,
            "provider_mode": self.provider_mode.value,
            "model_id": self.model_id,
            "role": self.role,
            "request_hash": self.request_hash,
            "response_hash": self.response_hash,
            "config_hash": self.config_hash,
            "runtime_mode": self.runtime_mode,
            "cognitive_soak_active": self.cognitive_soak_active,
            "dry_run": self.dry_run,
            "fixture_mode": self.fixture_mode,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "latency_ms": self.latency_ms,
            "token_count": self.token_count,
            "output_bytes": self.output_bytes,
            "status": self.status.value,
            "verdict": self.verdict.value,
            "error": self.error,
        }


@dataclass(frozen=True)
class ProviderAttemptReceipt:
    attempt_id: str
    provider_id: str
    provider_mode: ProviderMode
    role: str
    verdict: ProviderRealityVerdict
    error: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "provider_id": self.provider_id,
            "provider_mode": self.provider_mode.value,
            "role": self.role,
            "verdict": self.verdict.value,
            "error": self.error,
        }


class ProviderUnavailable(Exception):
    """Provider honestly unavailable — not fake success."""

    def __init__(self, receipt: ProviderReceipt):
        self.receipt = receipt
        super().__init__(receipt.verdict.value)


class ProviderFallbackDenied(Exception):
    """Fallback stub cannot count as cognition."""

    def __init__(self, receipt: ProviderReceipt):
        self.receipt = receipt
        super().__init__(receipt.verdict.value)


def load_provider_reality_policy(*, path: Path | None = None) -> dict[str, Any]:
    policy_path = path or DEFAULT_POLICY_PATH
    if not policy_path.is_file():
        return {}
    return json.loads(policy_path.read_text(encoding="utf-8"))


def build_provider_receipt(
    *,
    provider_id: str,
    provider_kind: ProviderKind,
    provider_mode: ProviderMode,
    role: str,
    request_hash: str,
    config_hash: str,
    runtime_mode: str,
    cognitive_soak_active: bool,
    dry_run: bool,
    fixture_mode: bool,
    status: ProviderStatus,
    verdict: ProviderRealityVerdict,
    started_at: str | None = None,
    ended_at: str | None = None,
    latency_ms: int = 0,
    model_id: str | None = None,
    response_hash: str | None = None,
    token_count: int | None = None,
    output_bytes: int | None = None,
    error: str | None = None,
    receipt_id: str | None = None,
) -> ProviderReceipt:
    """Build provider receipt with required identity fields."""
    rid = receipt_id or f"provider-rcpt-{uuid.uuid4().hex[:16]}"
    ts_start = started_at or datetime.now(timezone.utc).isoformat()
    ts_end = ended_at or ts_start
    body = {
        "receipt_id": rid,
        "provider_id": provider_id,
        "provider_kind": provider_kind.value,
        "provider_mode": provider_mode.value,
        "model_id": model_id,
        "role": role,
        "request_hash": request_hash,
        "response_hash": response_hash,
        "config_hash": config_hash,
        "runtime_mode": runtime_mode,
        "cognitive_soak_active": cognitive_soak_active,
        "dry_run": dry_run,
        "fixture_mode": fixture_mode,
        "started_at": ts_start,
        "ended_at": ts_end,
        "latency_ms": latency_ms,
        "token_count": token_count,
        "output_bytes": output_bytes,
        "status": status.value,
        "verdict": verdict.value,
        "error": error,
    }
    digest = compute_record_hash(body)
    return ProviderReceipt(
        receipt_id=rid,
        provider_id=provider_id,
        provider_kind=provider_kind,
        provider_mode=provider_mode,
        role=role,
        request_hash=request_hash,
        config_hash=config_hash,
        runtime_mode=runtime_mode,
        cognitive_soak_active=cognitive_soak_active,
        dry_run=dry_run,
        fixture_mode=fixture_mode,
        status=status,
        verdict=verdict,
        started_at=ts_start,
        ended_at=ts_end,
        latency_ms=latency_ms,
        model_id=model_id,
        response_hash=response_hash,
        token_count=token_count,
        output_bytes=output_bytes,
        error=error,
    )


def validate_provider_receipt(receipt: ProviderReceipt | None) -> ProviderRealityVerdict:
    """Validate receipt completeness — no hidden chain-of-thought fields."""
    if receipt is None:
        return ProviderRealityVerdict.RED_PROVIDER_RECEIPT_MISSING
    if not receipt.provider_id:
        return ProviderRealityVerdict.RED_PROVIDER_IDENTITY_MISSING
    if not receipt.request_hash:
        return ProviderRealityVerdict.RED_PROVIDER_HASH_MISSING
    payload = receipt.to_payload()
    if "chain_of_thought" in payload or "hidden_reasoning" in payload:
        return ProviderRealityVerdict.RED_PROVIDER_RECEIPT_MISSING
    return receipt.verdict


def receipt_counts_as_cognition(receipt: ProviderReceipt) -> bool:
    """Only live provider with GREEN verdict counts as real cognition."""
    policy = load_provider_reality_policy()
    if receipt.verdict != ProviderRealityVerdict.GREEN_PROVIDER_LIVE_AVAILABLE:
        return False
    if receipt.provider_mode != ProviderMode.LIVE:
        return False
    if policy.get("dry_run_counts_as_cognition") is False and receipt.dry_run:
        return False
    if policy.get("fixture_counts_as_cognition") is False and receipt.fixture_mode:
        return False
    if policy.get("fallback_stub_counts_as_cognition") is False:
        if receipt.provider_mode == ProviderMode.FALLBACK_STUB:
            return False
    return True


__all__ = [
    "ProviderAttemptReceipt",
    "ProviderFallbackDenied",
    "ProviderKind",
    "ProviderMode",
    "ProviderOutputVerdict",
    "ProviderRealityVerdict",
    "ProviderReceipt",
    "ProviderStatus",
    "ProviderUnavailable",
    "build_provider_receipt",
    "load_provider_reality_policy",
    "receipt_counts_as_cognition",
    "validate_provider_receipt",
]
