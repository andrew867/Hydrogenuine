"""EXCITON external write authority monitor snapshot."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.external_write_authority.schema import (
    CandidateStatus,
    ExternalWriteAuthorityVerdict,
    PermitStatus,
    STORE_ROOT,
    now_iso,
)


@dataclass
class ExternalWriteAuthorityMonitorSnapshot:
    candidate_count: int
    pending_candidates: int
    refused_candidates: int
    dry_run_dispatches: int
    expired_candidates: int
    revoked_permits: int
    dry_run_only: bool
    live_dispatch_allowed: bool
    last_refusal_reason: str | None
    verdict: str
    freshness: str
    proof_refs: tuple[str, ...] = ()
    items: tuple[dict[str, Any], ...] = ()

    def to_payload(self) -> dict[str, Any]:
        return {
            "candidate_count": self.candidate_count,
            "pending_candidates": self.pending_candidates,
            "refused_candidates": self.refused_candidates,
            "dry_run_dispatches": self.dry_run_dispatches,
            "expired_candidates": self.expired_candidates,
            "revoked_permits": self.revoked_permits,
            "dry_run_only": self.dry_run_only,
            "live_dispatch_allowed": self.live_dispatch_allowed,
            "last_refusal_reason": self.last_refusal_reason,
            "proof_refs": list(self.proof_refs),
            "freshness": self.freshness,
            "verdict": self.verdict,
            "items": list(self.items),
        }


def build_monitor_snapshot(*, run_id: str | None = None) -> ExternalWriteAuthorityMonitorSnapshot:
    from hg_runtime.external_write_authority.schema import load_policy

    policy = load_policy()
    root = STORE_ROOT
    if run_id:
        root = root / run_id

    items: list[dict[str, Any]] = []
    pending = refused = expired = dry_runs = revoked = 0
    last_refusal: str | None = None

    if root.is_dir():
        for cand_path in sorted(root.glob("**/candidates/*.json")):
            data = json.loads(cand_path.read_text(encoding="utf-8"))
            status = data.get("status", "")
            items.append(
                {
                    "type": "candidate",
                    "candidate_id": data.get("candidate_id"),
                    "platform": data.get("requested_platform"),
                    "action_type": data.get("requested_action_type"),
                    "scope": data.get("scope"),
                    "risk_class": data.get("risk_class"),
                    "status": status,
                    "permit_status": None,
                }
            )
            if status in (CandidateStatus.CANDIDATE_CREATED.value, CandidateStatus.AWAITING_AUTHORITY.value):
                pending += 1
            elif status == CandidateStatus.AUTHORITY_DENIED.value:
                refused += 1
            elif status == CandidateStatus.EXPIRED.value:
                expired += 1
            elif status == CandidateStatus.DRY_RUN_COMPLETED.value:
                dry_runs += 1

        for permit_path in sorted(root.glob("**/permits/*.json")):
            data = json.loads(permit_path.read_text(encoding="utf-8"))
            if data.get("status") == PermitStatus.REVOKED.value:
                revoked += 1
            for item in items:
                if item.get("candidate_id") == data.get("candidate_ref"):
                    item["permit_status"] = data.get("status")
                    item["dry_run_only"] = data.get("dry_run_only", True)
                    item["live_dispatch_allowed"] = data.get("live_dispatch_allowed", False)

        refusal_paths = sorted(root.glob("**/receipts/*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for rp in refusal_paths:
            data = json.loads(rp.read_text(encoding="utf-8"))
            if "refusal_receipt_id" in data:
                reasons = data.get("deny_reasons") or []
                if reasons:
                    last_refusal = reasons[-1]
                break

    verdict = ExternalWriteAuthorityVerdict.YELLOW_EXTERNAL_WRITE_DRY_RUN_ONLY.value
    if policy.get("live_dispatch_allowed"):
        verdict = ExternalWriteAuthorityVerdict.RED_LIVE_DISPATCH_FORBIDDEN.value

    return ExternalWriteAuthorityMonitorSnapshot(
        candidate_count=len([i for i in items if i.get("type") == "candidate"]),
        pending_candidates=pending,
        refused_candidates=refused,
        dry_run_dispatches=dry_runs,
        expired_candidates=expired,
        revoked_permits=revoked,
        dry_run_only=bool(policy.get("dry_run_only", True)),
        live_dispatch_allowed=bool(policy.get("live_dispatch_allowed", False)),
        last_refusal_reason=last_refusal,
        proof_refs=(),
        freshness=now_iso(),
        verdict=verdict,
        items=tuple(items),
    )
