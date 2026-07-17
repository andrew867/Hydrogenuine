"""Init delta chain verification for signed lifecycle events."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

INIT_DELTA_EVENT_CLASSES = {
    "BOOT_START",
    "BOOT_VERIFIED",
    "WAKE_REFRESH_COMPLETE",
    "FIRST_WAKE_START",
    "FIRST_WAKE_COMPLETE",
    "SLEEP_START",
    "SLEEP_COMPLETE",
    "CONTINUITY_RECOVERY_START",
    "CONTINUITY_RECOVERY_COMPLETE",
}


class ContinuityConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


@dataclass
class MissingDeltaFinding:
    expected_sequence: int
    reason: str


@dataclass
class InitDeltaVerification:
    ok: bool
    delta_count: int
    missing_deltas: list[MissingDeltaFinding] = field(default_factory=list)
    continuity_confidence: ContinuityConfidence = ContinuityConfidence.UNKNOWN
    failures: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "init-delta-verification",
            "ok": self.ok,
            "delta_count": self.delta_count,
            "missing_delta_count": len(self.missing_deltas),
            "continuity_confidence": self.continuity_confidence.value,
            "failures": self.failures,
            "missing_deltas": [{"expected_sequence": m.expected_sequence, "reason": m.reason} for m in self.missing_deltas],
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def extract_init_deltas(events_dir: Path) -> list[dict[str, Any]]:
    if not events_dir.exists():
        return []
    deltas: list[dict[str, Any]] = []
    for ef in sorted(events_dir.glob("event-*.json")):
        data = json.loads(ef.read_text(encoding="utf-8"))
        if data.get("event_class") in INIT_DELTA_EVENT_CLASSES:
            deltas.append(data)
    deltas.sort(key=lambda d: int(d.get("event_sequence", -1)))
    return deltas


def verify_init_delta_chain(
    events_dir: Path,
    *,
    strict: bool = True,
    public_key_pem: str | None = None,
) -> InitDeltaVerification:
    from hg_runtime.anchor_signing.schema import AnchorSignature
    from hg_runtime.anchor_signing.verify import verify_signature

    deltas = extract_init_deltas(events_dir)
    failures: list[str] = []
    missing: list[MissingDeltaFinding] = []
    prev_seq = -1
    prev_hash: str | None = None
    prev_sig_hash: str | None = None

    for d in deltas:
        seq = int(d.get("event_sequence", -1))
        if seq != prev_seq + 1:
            missing.append(MissingDeltaFinding(expected_sequence=prev_seq + 1, reason=f"sequence gap before {d.get('event_class')}"))
            failures.append("RED_CHAIN_GAP_UNDETECTED")
        if prev_hash and d.get("previous_journal_event_sha256") != prev_hash:
            failures.append(f"previous hash mismatch at seq {seq}")
        sig_block = d.get("journal_signature") or {}
        if sig_block:
            prev_sig = sig_block.get("previous_signature_sha256")
            if prev_sig_hash and prev_sig != prev_sig_hash:
                failures.append(f"previous signature mismatch at seq {seq}")
            if public_key_pem and strict:
                try:
                    verify_signature(d, AnchorSignature(**{k: sig_block[k] for k in sig_block if k != "advisory_only"}), public_key_pem=public_key_pem, strict=True)
                except Exception as exc:
                    failures.append(str(exc))
        elif strict:
            failures.append(f"unsigned init delta at seq {seq}")
        prev_seq = seq
        prev_hash = d.get("journal_event_sha256")
        prev_sig_hash = sha256_sig(sig_block) if sig_block else None

    ok = not failures and not missing
    confidence = ContinuityConfidence.HIGH if ok and deltas else (
        ContinuityConfidence.MEDIUM if deltas and not missing else ContinuityConfidence.LOW
    )
    if missing:
        confidence = ContinuityConfidence.LOW
    return InitDeltaVerification(
        ok=ok,
        delta_count=len(deltas),
        missing_deltas=missing,
        continuity_confidence=confidence,
        failures=failures,
    )


def sha256_sig(sig_block: dict[str, Any]) -> str | None:
    sig = sig_block.get("signature")
    if not sig:
        return None
    from hg_runtime.external_start_anchor.canonical_json import sha256_hex
    return sha256_hex({"signature": sig, "signer_key_id": sig_block.get("signer_key_id")})


__all__ = [
    "INIT_DELTA_EVENT_CLASSES",
    "ContinuityConfidence",
    "InitDeltaVerification",
    "MissingDeltaFinding",
    "extract_init_deltas",
    "verify_init_delta_chain",
]
