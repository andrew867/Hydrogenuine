"""Phase 19 platform proof reverification."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.external_write_authority.action_ledger import (
    Phase19Verdict,
    load_ledger_entries,
    phase18_live_proof_status,
)
from hg_runtime.external_write_authority.live_smoke import PHASE18_ROOT
from hg_runtime.external_write_authority.schema import new_id, now_iso

PHASE19_REVERIFY_DIR = PHASE18_ROOT.parent / "phase19" / "reverifications"


@dataclass
class PlatformProofReverification:
    reverification_id: str
    live_dispatch_result_ref: str
    platform: str
    platform_object_id: str | None
    platform_url: str | None
    content_sha256_expected: str
    content_sha256_observed: str | None
    visibility_status: str
    proof_method: str
    observed_at: str
    verdict: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "reverification_id": self.reverification_id,
            "live_dispatch_result_ref": self.live_dispatch_result_ref,
            "platform": self.platform,
            "platform_object_id": self.platform_object_id,
            "platform_url": self.platform_url,
            "content_sha256_expected": self.content_sha256_expected,
            "content_sha256_observed": self.content_sha256_observed,
            "visibility_status": self.visibility_status,
            "proof_method": self.proof_method,
            "observed_at": self.observed_at,
            "verdict": self.verdict,
            "hash": self.hash,
        }

    def with_hash(self) -> PlatformProofReverification:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return PlatformProofReverification(**{**self.__dict__, "hash": compute_record_hash(body)})


def reverify_platform_proofs() -> list[PlatformProofReverification]:
    PHASE19_REVERIFY_DIR.mkdir(parents=True, exist_ok=True)
    proof_status = phase18_live_proof_status()
    entries = load_ledger_entries()
    live_entries = [e for e in entries if e.external_side_effect]

    if not proof_status["live_proof_exists"] or not live_entries:
        return []

    proofs_dir = PHASE18_ROOT / "platform_proofs"
    proof_by_dispatch: dict[str, dict] = {}
    if proofs_dir.is_dir():
        for p in proofs_dir.glob("*.json"):
            data = json.loads(p.read_text(encoding="utf-8"))
            proof_by_dispatch[data.get("live_dispatch_result_ref", "")] = data

    results: list[PlatformProofReverification] = []
    for entry in live_entries:
        ref = entry.live_dispatch_result_ref or ""
        proof = proof_by_dispatch.get(ref, {})
        observed = proof.get("content_sha256_observed") or entry.content_sha256
        visibility = proof.get("visibility_status") or entry.platform_proof_ref or "missing"
        if not entry.platform_url and not entry.platform_object_id:
            verdict = Phase19Verdict.YELLOW_NO_PROOF
            visibility = "missing"
        elif observed != entry.content_sha256:
            verdict = Phase19Verdict.RED_HASH_MISMATCH
        elif visibility in ("visibility_delayed", "not_found", "missing"):
            verdict = Phase19Verdict.YELLOW_VISIBILITY
        else:
            verdict = Phase19Verdict.GREEN

        rev = PlatformProofReverification(
            reverification_id=new_id("p19-reverify"),
            live_dispatch_result_ref=ref,
            platform=entry.platform,
            platform_object_id=entry.platform_object_id,
            platform_url=entry.platform_url,
            content_sha256_expected=entry.content_sha256,
            content_sha256_observed=observed,
            visibility_status=str(visibility),
            proof_method="ledger_and_stored_proof",
            observed_at=now_iso(),
            verdict=verdict,
        ).with_hash()
        (PHASE19_REVERIFY_DIR / f"{rev.reverification_id}.json").write_text(
            json.dumps(rev.to_payload(), indent=2) + "\n", encoding="utf-8"
        )
        results.append(rev)
    return results
