"""Pre-soak readiness check -- runs ALL reliability modules with fixture
data to verify the integration pipeline is healthy before starting a soak.

No model calls. No web calls. No file mutations. No authority granted.
Promotion is NEVER allowed. Operator review is ALWAYS required.
"""

from __future__ import annotations

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


# Fixture data for pre-soak readiness checks
_FIXTURE_WEAK_CONTENT = (
    "This is a somewhat short output that could be better. "
    "It lacks depth but is not empty."
)

_FIXTURE_SAFE_TEXT = (
    "Agent Zero is a research assistant. It does not claim to be conscious "
    "and it is not AGI. The system requires operator review."
)

_FIXTURE_SEED = {
    "seed_id": "pre_soak_seed_0",
    "claim_id": "pre_soak_claim_0",
    "seed_label": "Pre-soak readiness seed",
    "claim_label": "Pre-soak readiness claim",
}

_FIXTURE_CANDIDATE = {
    "candidate_id": "pre_soak_cand_0",
    "content_summary": "Pre-soak readiness candidate for quarantine check",
    "source": "model_output",
    "model_id": "test",
}


def run_pre_soak_readiness(
    *,
    run_id: str = "",
    stop_file: str = "",
    panic_file: str = "",
    stop_panic: bool = False,
) -> dict:
    """Run all reliability module checks with fixture data.

    Checks:
    1. STOP/PANIC sentinel files
    2. Output quality (weak content)
    3. Contradiction check (empty claims)
    4. Evidence graph (sample seed)
    5. Public claim check (safe text)
    6. Memory quarantine (sample candidate)
    7. Operator read model

    Returns a reliability_receipt with mode="pre_soak".
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
    sp_result = check_stop_panic(stop_file=stop_file, panic_file=panic_file)
    stop_panic_active = sp_result["active"] or stop_panic

    # 2. Quality check with sample weak content
    quality_result = run_quality_check(
        _FIXTURE_WEAK_CONTENT,
        model_id="test",
        stop_panic=stop_panic_active,
    )

    # 3. Contradiction check with empty claims
    contradiction_result = run_contradiction_check(
        claims=[],
        stop_panic=stop_panic_active,
    )

    # 4. Evidence graph check with sample seed
    evidence_result = run_evidence_graph_check(
        seeds=[_FIXTURE_SEED],
        stop_panic=stop_panic_active,
    )

    # 5. Public claim check with safe text
    public_claim_result = run_public_claim_check(
        text=_FIXTURE_SAFE_TEXT,
        stop_panic=stop_panic_active,
    )

    # 6. Memory quarantine check with sample candidate
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

    # Determine final readiness verdict
    if stop_panic_active:
        final_readiness_verdict = "NOT_READY_STOP_PANIC"
    elif public_claim_result.get("status") == "flagged":
        final_readiness_verdict = "NOT_READY_UNSAFE_CLAIMS"
    elif any(
        r.get("status") == "blocked"
        for r in [
            quality_result,
            contradiction_result,
            evidence_result,
            public_claim_result,
            quarantine_result,
            read_model_result,
        ]
    ):
        final_readiness_verdict = "NOT_READY_STOP_PANIC"
    else:
        final_readiness_verdict = "READY_FOR_SOAK"

    stop_panic_status = "active" if stop_panic_active else "clear"

    return create_receipt(
        mode="pre_soak",
        run_id=run_id,
        modules_checked=modules_checked,
        quality_status=quality_result.get("status", ""),
        contradiction_status=contradiction_result.get("status", ""),
        evidence_graph_status=evidence_result.get("status", ""),
        memory_quarantine_status=quarantine_result.get("status", ""),
        public_claim_status=public_claim_result.get("status", ""),
        operator_read_model_status=read_model_result.get("status", ""),
        stop_panic_status=stop_panic_status,
        final_readiness_verdict=final_readiness_verdict,
    )
