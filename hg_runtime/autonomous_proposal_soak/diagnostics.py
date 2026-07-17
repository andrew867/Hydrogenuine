"""Local-only diagnostic probes for Phase 36."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.autonomous_proposal_soak.schemas import DIAGNOSTIC_PROBE_SCHEMA, ProposalSoakError, neutral_flags


def local_file_probe(path: Path, *, probe_id: str) -> dict[str, Any]:
    exists = path.exists()
    record = {
        "schema": DIAGNOSTIC_PROBE_SCHEMA,
        "probe_id": probe_id,
        "kind": "local_file",
        "path": str(path),
        "exists": exists,
        "external_provider_call": False,
        "live_side_effect": False,
        **neutral_flags(),
    }
    record["probe_hash"] = canonical_hash(record)
    return record


def refuse_external_provider_probe() -> None:
    raise ProposalSoakError("external_provider_probe_refused")


def refuse_live_social_probe() -> None:
    raise ProposalSoakError("live_social_probe_refused")


def refuse_moltbook_live_probe() -> None:
    raise ProposalSoakError("moltbook_live_probe_refused")


__all__ = [
    "local_file_probe",
    "refuse_external_provider_probe",
    "refuse_live_social_probe",
    "refuse_moltbook_live_probe",
]
