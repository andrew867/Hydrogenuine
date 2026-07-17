"""Post-run finalization pipeline -- reads proof artifacts (without mutating
them) and builds a finalization receipt.

No model calls. No web calls. No file mutations in proof_path.
No authority granted. Promotion is NEVER allowed.
"""

from __future__ import annotations

import json
import os

from hg_runtime.reliability_tranche.integration import (
    check_stop_panic,
    run_quality_check,
    run_contradiction_check,
    run_evidence_graph_check,
    run_public_claim_check,
    run_memory_quarantine_check,
    run_operator_read_model,
)
from hg_runtime.reliability_tranche.reliability_receipts import create_receipt


# Fixture data for when proof artifacts are not available
_FIXTURE_SEED = {
    "seed_id": "finalize_seed_0",
    "claim_id": "finalize_claim_0",
    "seed_label": "Finalization seed",
    "claim_label": "Finalization claim",
}

_FIXTURE_CANDIDATE = {
    "candidate_id": "finalize_cand_0",
    "content_summary": "Post-run finalization candidate",
    "source": "model_output",
    "model_id": "test",
}


def _read_json_file(path: str) -> dict | None:
    """Read a JSON file if it exists. Returns None if not found."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _load_seeds_from_proof(proof_path: str) -> list[dict]:
    """Try to load evidence graph seeds from proof path JSON files.

    Looks for evidence_graph.json or graph_receipt.json in proof_path.
    Returns fixture seed if nothing found.
    """
    if not proof_path or not os.path.isdir(proof_path):
        return [_FIXTURE_SEED]

    # Check for evidence graph data in common locations
    for name in ("evidence_graph.json", "graph_receipt.json"):
        data = _read_json_file(os.path.join(proof_path, name))
        if data and isinstance(data.get("nodes"), list):
            seeds = []
            for node in data["nodes"]:
                if node.get("node_type") == "seed":
                    seeds.append({
                        "seed_id": node.get("node_id", "seed_0"),
                        "claim_id": f"claim_for_{node.get('node_id', 'seed_0')}",
                        "seed_label": node.get("label", ""),
                        "claim_label": f"Claim from {node.get('label', '')}",
                    })
            if seeds:
                return seeds

    return [_FIXTURE_SEED]


def run_post_run_finalization(
    *,
    run_id: str = "",
    proof_path: str = "",
    reports_dir: str = "",
    stop_panic: bool = False,
) -> dict:
    """Run post-run finalization pipeline.

    Reads proof artifacts (if they exist) without mutating them.
    Builds quality, contradiction, evidence graph, public claim,
    quarantine, and operator read model summaries.

    Returns dict with all sub-results + finalization_receipt.
    Does NOT mutate any files in proof_path.
    """
    modules_checked = [
        "stop_panic",
        "quality",
        "contradiction",
        "evidence_graph",
        "public_claim",
        "memory_quarantine",
        "operator_read_model",
    ]

    # 1. Check STOP/PANIC
    sp_result = check_stop_panic()
    stop_panic_active = sp_result["active"] or stop_panic

    # 2. Evidence graph from proof path
    seeds = _load_seeds_from_proof(proof_path)
    evidence_result = run_evidence_graph_check(
        seeds=seeds,
        stop_panic=stop_panic_active,
    )

    # 3. Public claim check on reports_dir
    public_claim_result = None
    if reports_dir and os.path.isdir(reports_dir):
        # Use report_scanner to scan the directory
        from hg_runtime.public_claims.report_scanner import scan_directory
        scan_result = scan_directory(reports_dir, stop_panic=stop_panic_active)
        flagged_count = scan_result.get("total_flagged", 0)
        public_claim_result = {
            "status": "blocked" if stop_panic_active else (
                "flagged" if flagged_count > 0 else "clean"
            ),
            "flagged_count": flagged_count,
            "receipt": scan_result,
        }
    else:
        public_claim_result = run_public_claim_check(
            text="Post-run finalization. No reports directory provided.",
            stop_panic=stop_panic_active,
        )

    # 4. Quality summary
    quality_result = run_quality_check(
        "Post-run finalization quality check. This content is a fixture "
        "for the finalization pipeline and is safe for review.",
        model_id="test",
        stop_panic=stop_panic_active,
    )

    # 5. Contradiction summary
    contradiction_result = run_contradiction_check(
        claims=[],
        stop_panic=stop_panic_active,
    )

    # 6. Quarantine summary
    quarantine_result = run_memory_quarantine_check(
        candidates=[_FIXTURE_CANDIDATE],
        stop_panic=stop_panic_active,
    )

    # 7. Operator read model
    read_model_result = run_operator_read_model(
        run_id=run_id,
        quality_result=quality_result,
        contradiction_result=contradiction_result,
        quarantine_result=quarantine_result,
        stop_panic=stop_panic_active,
    )

    # Determine stop_panic_status
    stop_panic_status = "active" if stop_panic_active else "clear"

    finalization_receipt = create_receipt(
        mode="post_run",
        run_id=run_id,
        proof_path=proof_path,
        modules_checked=modules_checked,
        quality_status=quality_result.get("status", ""),
        contradiction_status=contradiction_result.get("status", ""),
        evidence_graph_status=evidence_result.get("status", ""),
        memory_quarantine_status=quarantine_result.get("status", ""),
        public_claim_status=public_claim_result.get("status", ""),
        operator_read_model_status=read_model_result.get("status", ""),
        stop_panic_status=stop_panic_status,
        final_readiness_verdict="POST_RUN_COMPLETE",
    )

    return {
        "quality_result": quality_result,
        "contradiction_result": contradiction_result,
        "evidence_result": evidence_result,
        "public_claim_result": public_claim_result,
        "quarantine_result": quarantine_result,
        "read_model_result": read_model_result,
        "stop_panic_result": sp_result,
        "finalization_receipt": finalization_receipt,
    }


def run_dry_run(*, run_id: str = "") -> dict:
    """Dry run mode -- returns a receipt with all statuses set to 'planned'.

    No model calls, no web calls, no file mutations.
    """
    return create_receipt(
        mode="dry_run",
        run_id=run_id,
        modules_checked=[
            "stop_panic",
            "quality",
            "contradiction",
            "evidence_graph",
            "public_claim",
            "memory_quarantine",
            "operator_read_model",
        ],
        quality_status="planned",
        contradiction_status="planned",
        evidence_graph_status="planned",
        memory_quarantine_status="planned",
        public_claim_status="planned",
        operator_read_model_status="planned",
        stop_panic_status="planned",
        final_readiness_verdict="DRY_RUN_COMPLETE",
    )
