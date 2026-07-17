"""Proof bundle metadata indexer — no secret dumps."""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.agent_zero_self_mirror.repo_index import WORKSPACE, _should_exclude
from hg_runtime.agent_zero_self_mirror.schema import IndexStatus, ProofBundleIndex

PROOFS_ROOT = WORKSPACE / "docs" / "proofs"


def build_proof_index() -> ProofBundleIndex:
    bundles: list[dict] = []
    if not PROOFS_ROOT.is_dir():
        return ProofBundleIndex(status=IndexStatus.UNAVAILABLE, bundles=[])
    for gate_dir in sorted(PROOFS_ROOT.iterdir()):
        if not gate_dir.is_dir():
            continue
        for bundle_dir in sorted(gate_dir.iterdir(), reverse=True):
            if not bundle_dir.is_dir():
                continue
            rel = str(bundle_dir.relative_to(WORKSPACE)).replace("\\", "/")
            if _should_exclude(rel):
                continue
            files = []
            for f in bundle_dir.iterdir():
                if f.is_file() and f.suffix == ".json":
                    files.append(f.name)
            latest_report = None
            for name in ("final_gate_report.json", "gate_report.json"):
                p = bundle_dir / name
                if p.is_file():
                    try:
                        latest_report = json.loads(p.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        pass
                    break
            bundles.append({
                "bundle_path": rel,
                "gate_family": gate_dir.name,
                "bundle_id": bundle_dir.name,
                "json_files": files[:20],
                "verdict": (latest_report or {}).get("verdict"),
                "advisory_only": True,
                "permission_granted": False,
                "authority_created": False,
            })
            if len(bundles) >= 100:
                break
    return ProofBundleIndex(status=IndexStatus.READY if bundles else IndexStatus.PARTIAL, bundles=bundles)


def latest_proof_bundle() -> dict | None:
    idx = build_proof_index()
    return idx.bundles[0] if idx.bundles else None


__all__ = ["build_proof_index", "latest_proof_bundle"]
