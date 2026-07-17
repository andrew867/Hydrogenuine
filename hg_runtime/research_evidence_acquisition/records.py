"""RES offline/provided-file evidence records."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from hg_runtime.research_evidence_acquisition.types import EvidenceRecord

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"
FIXTURE_EXPIRY = "2026-06-13T20:00:00.000000Z"


def record_from_provided_file(fixture: Mapping[str, str]) -> EvidenceRecord:
    """Build evidence record from provided offline file fixture."""
    source_ref = fixture.get("source_ref", f"docs/proofs/policy_safety/P1-A/all/20260613T012632Z/manifest.json")
    if source_ref.startswith("docs/"):
        path = Path(fixture.get("workspace_root", ".")) / source_ref
        if path.is_file():
            import hashlib

            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            source_ref = f"sha256:{digest}"
    return EvidenceRecord(
        evidence_id=fixture["evidence_id"],
        source_ref=source_ref,
        source_type=fixture.get("source_type", "proof_bundle"),  # type: ignore[arg-type]
        claim_supported=fixture.get("claim_supported", "bounded evidence ref only"),
        support_level=fixture.get("support_level", "direct"),  # type: ignore[arg-type]
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
        expires_at=fixture.get("expires_at", FIXTURE_EXPIRY),
    )


__all__ = ["FIXTURE_CLOCK", "FIXTURE_EXPIRY", "record_from_provided_file"]
