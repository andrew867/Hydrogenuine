"""Optoacoustic proof reconstruction operator service (P2-5)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_quantum.persistence.optoacoustic_linker import OptoacousticLinker


class _ReconstructionState:
    def __init__(self) -> None:
        self.seeded = False
        self.fingerprint_id = ""
        self.linker: Optional[OptoacousticLinker] = None
        self.proof_snapshot_ids: List[str] = []


_STATE = _ReconstructionState()


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _workspace_root() -> Path:
    try:
        from hg_lib.config import get_workspace_root

        return Path(get_workspace_root())
    except Exception:
        return Path(".")


def reset_proof_reconstruction_state() -> None:
    _STATE.seeded = False
    _STATE.fingerprint_id = ""
    _STATE.linker = None
    _STATE.proof_snapshot_ids.clear()


def seed_proof_reconstruction_demo(*, fingerprint_id: str = "fp_recon_demo") -> Dict[str, Any]:
    store_dir = _workspace_root() / "memory" / "governance" / "optoacoustic_links"
    linker = OptoacousticLinker(fingerprint_id=fingerprint_id, store_dir=store_dir)
    proof_ids: List[str] = []
    for i in range(4):
        mesh = {
            "event_id": f"mesh_recon_{i}",
            "type": "job_progress",
            "ts": float(i),
            "fingerprint_id": fingerprint_id,
        }
        proof = {"snapshot_id": f"proof_recon_{i}", "type": "swarm_proof", "seq": i}
        linker.link_mesh_to_proof(mesh, proof)
        proof_ids.append(proof["snapshot_id"])
    _STATE.seeded = True
    _STATE.fingerprint_id = fingerprint_id
    _STATE.linker = linker
    _STATE.proof_snapshot_ids = proof_ids
    return {"ok": True, "fingerprint_id": fingerprint_id, "proof_snapshot_ids": proof_ids}


def _ensure_seeded() -> None:
    if not _STATE.seeded:
        seed_proof_reconstruction_demo()


def get_reconstruction_dashboard() -> Dict[str, Any]:
    _ensure_seeded()
    assert _STATE.linker is not None
    timeline = _STATE.linker.reconstruct_from_proof_trail(_STATE.proof_snapshot_ids)
    return {
        "ok": True,
        "fingerprint_id": _STATE.fingerprint_id,
        "proof_snapshot_ids": list(_STATE.proof_snapshot_ids),
        "timeline": timeline,
        "event_count": len(timeline),
        "generated_at": _iso_now(),
    }


def reconstruct_from_ids(proof_snapshot_ids: List[str]) -> Dict[str, Any]:
    _ensure_seeded()
    assert _STATE.linker is not None
    timeline = _STATE.linker.reconstruct_from_proof_trail(proof_snapshot_ids)
    return {
        "ok": True,
        "requested_ids": proof_snapshot_ids,
        "timeline": timeline,
        "event_count": len(timeline),
        "generated_at": _iso_now(),
    }
