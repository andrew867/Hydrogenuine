"""Platform proof guard — post-dispatch verification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_runtime.external_write_authority.action_ledger import ExternalActionLedgerEntry, LEDGER_DIR
from hg_runtime.external_write_authority.schema import new_id as p19_new_id
from hg_runtime.real_soak_launch.schema import RealSoakLaunchVerdict, now_iso
import json


@dataclass
class PlatformProofGuardDecision:
    decision_id: str
    verdict: str
    platform_object_id: str | None
    platform_url: str | None
    content_hash_match: bool | None
    ledger_entry_ref: str | None
    created_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "verdict": self.verdict,
            "platform_object_id": self.platform_object_id,
            "platform_url": self.platform_url,
            "content_hash_match": self.content_hash_match,
            "ledger_entry_ref": self.ledger_entry_ref,
            "created_at": self.created_at,
        }


def evaluate_platform_proof(
    *,
    content_sha256: str,
    platform_object_id: str | None,
    platform_url: str | None,
    proof_content_sha256: str | None,
    dispatch_receipt_ref: str | None,
    proof_delayed: bool = False,
    duplicate_object: bool = False,
) -> PlatformProofGuardDecision:
    if proof_delayed:
        return PlatformProofGuardDecision(
            decision_id=f"proof-guard-{now_iso()}",
            verdict=RealSoakLaunchVerdict.YELLOW_PROOF_DELAYED.value,
            platform_object_id=platform_object_id,
            platform_url=platform_url,
            content_hash_match=None,
            ledger_entry_ref=None,
            created_at=now_iso(),
        )

    if not platform_object_id and not platform_url:
        return PlatformProofGuardDecision(
            decision_id=f"proof-guard-{now_iso()}",
            verdict=RealSoakLaunchVerdict.RED_NO_PROOF.value,
            platform_object_id=None,
            platform_url=None,
            content_hash_match=False,
            ledger_entry_ref=None,
            created_at=now_iso(),
        )

    if duplicate_object:
        return PlatformProofGuardDecision(
            decision_id=f"proof-guard-{now_iso()}",
            verdict="RED_DUPLICATE_DISPATCH",
            platform_object_id=platform_object_id,
            platform_url=platform_url,
            content_hash_match=False,
            ledger_entry_ref=None,
            created_at=now_iso(),
        )

    hash_match = proof_content_sha256 == content_sha256 if proof_content_sha256 else None
    if proof_content_sha256 and not hash_match:
        return PlatformProofGuardDecision(
            decision_id=f"proof-guard-{now_iso()}",
            verdict=RealSoakLaunchVerdict.RED_CONTENT_MISMATCH.value,
            platform_object_id=platform_object_id,
            platform_url=platform_url,
            content_hash_match=False,
            ledger_entry_ref=None,
            created_at=now_iso(),
        )

    ledger_ref = None
    if dispatch_receipt_ref:
        LEDGER_DIR.mkdir(parents=True, exist_ok=True)
        entry = ExternalActionLedgerEntry(
            ledger_entry_id=p19_new_id("p245-ledger"),
            live_dispatch_result_ref=dispatch_receipt_ref,
            platform="moltbook",
            action_type="publish_post",
            content_sha256=content_sha256,
            external_side_effect=True,
            platform_object_id=platform_object_id,
            platform_url=platform_url,
            platform_proof_ref=f"proof-{platform_object_id or 'unknown'}",
            created_at=now_iso(),
            source="real_soak_launch",
        ).with_hash()
        path = LEDGER_DIR / f"{entry.ledger_entry_id}.json"
        path.write_text(json.dumps(entry.to_payload(), indent=2) + "\n", encoding="utf-8")
        ledger_ref = entry.ledger_entry_id

    verdict = "GREEN_PLATFORM_PROOF_OK"
    if hash_match is False:
        verdict = RealSoakLaunchVerdict.RED_CONTENT_MISMATCH.value

    return PlatformProofGuardDecision(
        decision_id=f"proof-guard-{now_iso()}",
        verdict=verdict,
        platform_object_id=platform_object_id,
        platform_url=platform_url,
        content_hash_match=hash_match,
        ledger_entry_ref=ledger_ref,
        created_at=now_iso(),
    )


def proof_missing_cannot_be_green(verdict: str) -> bool:
    return verdict.startswith("RED_") or verdict == RealSoakLaunchVerdict.RED_PROOF_GREEN.value
