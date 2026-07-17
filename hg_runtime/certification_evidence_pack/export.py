"""CRT read-only evidence index and reproducible export (first safe slice)."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.policy_safety.no_authority import advisory_only_marker
from hg_runtime.certification_evidence_pack.types import (
    AuditorExportBundle,
    CertificationSnapshot,
    EvidenceReference,
    ExceptionRecord,
    SafetyClaim,
    make_claim,
)

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"


def build_snapshot_from_fixtures(
    *,
    snapshot_id: str,
    branch: str,
    head: str,
    claims: Sequence[Mapping[str, str]],
    exceptions: Sequence[Mapping[str, str]],
    evidence_refs: Sequence[Mapping[str, str]],
    created_at: str = FIXTURE_CLOCK,
) -> CertificationSnapshot:
    """Build certification snapshot from static fixtures — read-only, no gate execution."""
    claim_objs = tuple(
        make_claim(
            claim_id=c["claim_id"],
            statement=c["statement"],
            control_domain=c.get("control_domain", "unknown"),  # type: ignore[arg-type]
            status=c.get("status", "unsupported"),  # type: ignore[arg-type]
            evidence_refs=tuple(c.get("evidence_refs", "").split("|")) if c.get("evidence_refs") else (),
            created_at=c.get("created_at", created_at),
        )
        for c in claims
    )
    exception_objs = tuple(
        ExceptionRecord(
            exception_id=e["exception_id"],
            detail=e["detail"],
            control_domain=e.get("control_domain", "unknown"),  # type: ignore[arg-type]
            created_at=e.get("created_at", created_at),
        )
        for e in exceptions
    )
    evidence_objs = tuple(
        EvidenceReference(
            evidence_id=r["evidence_id"],
            path=r["path"],
            content_hash=r["content_hash"],
            fresh=r.get("fresh", "true").lower() == "true",
            created_at=r.get("created_at", created_at),
        )
        for r in evidence_refs
    )
    return CertificationSnapshot(
        snapshot_id=snapshot_id,
        branch=branch,
        head=head,
        claims=claim_objs,
        exceptions=exception_objs,
        evidence_refs=evidence_objs,
        created_at=created_at,
    )


def build_auditor_export(snapshot: CertificationSnapshot, *, export_id: str | None = None) -> AuditorExportBundle:
    """Build reproducible auditor export bundle; certification evidence is not certification."""
    export_id = export_id or f"export-{snapshot.snapshot_id}"
    bundle_hash = compute_record_hash(
        {
            "snapshot_hash": snapshot.record_hash,
            "head": snapshot.head,
            "claim_hashes": [c.record_hash for c in snapshot.claims],
            "exception_hashes": [e.record_hash for e in snapshot.exceptions],
        }
    )
    return AuditorExportBundle(
        export_id=export_id,
        snapshot=snapshot,
        bundle_hash=bundle_hash,
        created_at=snapshot.created_at,
    )


def index_proof_bundle(workspace: Path, relative_path: str) -> EvidenceReference | None:
    """Read-only index of an on-disk proof bundle manifest if present."""
    manifest = workspace / relative_path / "manifest.json"
    if not manifest.is_file():
        return None
    import json

    data = json.loads(manifest.read_text(encoding="utf-8"))
    file_hashes = data.get("file_hashes", {})
    gate_hash = file_hashes.get("gate_result.json", "sha256:missing")
    return EvidenceReference(
        evidence_id=f"ev-{data.get('timestamp', 'unknown')}",
        path=relative_path.replace("\\", "/"),
        content_hash=gate_hash if str(gate_hash).startswith("sha256:") else f"sha256:{gate_hash}",
        fresh=True,
        created_at=FIXTURE_CLOCK,
    )


def export_advisory_payload(bundle: AuditorExportBundle) -> dict[str, object]:
    return {**advisory_only_marker(), **bundle.to_payload(), "detail": "certification evidence is not certification"}


__all__ = [
    "FIXTURE_CLOCK",
    "build_auditor_export",
    "build_snapshot_from_fixtures",
    "export_advisory_payload",
    "index_proof_bundle",
]
