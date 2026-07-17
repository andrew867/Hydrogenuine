"""Proof bundle sealing — refuse to seal bundles containing canaries (CT-02)."""

from __future__ import annotations

from pathlib import Path

from hg_core.secrets.redact import RedactionFailure
from hg_core.secrets.scan import scan_directory


def seal_proof_bundle(proof_dir: Path) -> tuple[bool, list[dict[str, str]]]:
    """Return (ok, hits). Any hit means the bundle must not be sealed."""
    hits = scan_directory(proof_dir)
    return len(hits) == 0, hits


def refuse_seal_if_leak(proof_dir: Path) -> None:
    ok, hits = seal_proof_bundle(proof_dir)
    if not ok:
        raise RedactionFailure(f"bundle_contains_secrets:{len(hits)}_hits")


__all__ = ["refuse_seal_if_leak", "seal_proof_bundle"]
