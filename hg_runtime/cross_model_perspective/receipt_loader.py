"""Load and normalize runtime P42 model response receipts for WMBR-01A.

Receipts are an *input* to epistemic spectroscopy. They are never treated as
truth. Loading a receipt records what a model said, not whether it is correct.
"""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.cross_model_perspective.schemas import CrossModelPerspectiveError

# Default discovery root for runtime P42 proof bundles.
P42_PROOF_GLOB = "docs/proofs/autonomous_agent_zero/PHASE-42-PROVIDER-PORTABILITY"


def _as_bool(value: object) -> bool:
    return bool(value)


def normalize_receipt(receipt: dict) -> dict:
    """Project a raw receipt onto the fields the perspective matrix needs.

    Missing analysis fields default to neutral/empty values so that receipts
    produced by the runtime P42 substrate (which lack explicit claim tags) and
    the WMBR-01A fixtures (which carry them) can be analyzed by the same code.
    """
    if "receipt_id" not in receipt:
        raise CrossModelPerspectiveError("receipt_missing_receipt_id")
    evidence_refs = list(receipt.get("evidence_refs", []) or [])
    included = list(receipt.get("included_claim_tags", []) or [])
    if not included:
        # Derive a single opaque claim cluster from the response hash so bundle
        # receipts still occupy a matrix cell without inventing shared claims.
        opaque = receipt.get("response_text_hash") or receipt.get("receipt_hash") or receipt["receipt_id"]
        included = [f"response_cluster:{str(opaque)[:16]}"]
    normalized = {
        "receipt_id": receipt["receipt_id"],
        "receipt_hash": receipt.get("receipt_hash", ""),
        "run_id": receipt.get("run_id", "unknown"),
        "prompt_id": receipt.get("prompt_id", "UNKNOWN_PROMPT"),
        "participant_id": receipt.get("participant_id", "UNKNOWN_PARTICIPANT"),
        "provider_id": receipt.get("provider_id", "unknown"),
        "model_id": receipt.get("model_id", "unknown"),
        "included_claim_tags": sorted(included),
        "evidence_refs": evidence_refs,
        "sourced": bool(evidence_refs),
        "refusal_state": receipt.get("refusal_state", "NOT_REFUSED"),
        "willingness_state": receipt.get("willingness_state", "NEUTRAL"),
        "framing_tags": sorted(receipt.get("framing_tags", []) or []),
        "moral_principle_tags": sorted(receipt.get("moral_principle_tags", []) or []),
        "moral_stance": receipt.get("moral_stance"),
        "moral_conflict_axis": receipt.get("moral_conflict_axis"),
        "evidence_gap_tags": sorted(receipt.get("evidence_gap_tags", []) or []),
        "genericity_score": int(receipt.get("genericity_score", 0) or 0),
        "specificity_score": int(receipt.get("specificity_score", 0) or 0),
    }
    score_gap = normalized["genericity_score"] - normalized["specificity_score"]
    if normalized["genericity_score"] > 0 and normalized["specificity_score"] == 0:
        normalized["specificity_class"] = "GENERIC"
    elif score_gap >= 0 and normalized["genericity_score"] > 0:
        normalized["specificity_class"] = "MIXED"
    else:
        normalized["specificity_class"] = "SPECIFIC"
    return normalized


def normalize_receipts(receipts: list[dict]) -> list[dict]:
    if not receipts:
        raise CrossModelPerspectiveError("input_receipts_required")
    return [normalize_receipt(r) for r in receipts]


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_from_bundle(bundle_dir: Path) -> list[dict]:
    """Load raw model response receipts from a runtime P42 proof bundle."""
    bundle_dir = Path(bundle_dir)
    receipts_path = bundle_dir / "model_response_receipts.jsonl"
    if not receipts_path.exists():
        raise CrossModelPerspectiveError("input_receipts_required")
    receipts = load_jsonl(receipts_path)
    if not receipts:
        raise CrossModelPerspectiveError("input_receipts_required")
    return receipts


def discover_latest_bundle(proof_root: Path) -> Path | None:
    """Return the newest runtime P42 proof bundle directory, or None."""
    proof_root = Path(proof_root)
    candidates = sorted(p.parent for p in proof_root.glob("*/model_response_receipts.jsonl"))
    return candidates[-1] if candidates else None
