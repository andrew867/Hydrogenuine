"""Phase 31 Generalization Evaluation Harness.

Measures whether a learned pattern, skill, or acquired procedure transfers to a
held-out novel task without task-specific reprogramming. It is an evaluation
harness, not an authority layer: it rejects vibe-based generalization, surface
similarity, answer-key leakage, cherry-picked tasks, and broad competence claims
beyond tested held-out scope. It never grants authority, authorizes a tool, or
widens scope.
"""

from __future__ import annotations

from hg_runtime.generalization_eval.schemas import (
    GeneralizationEvalError,
    is_broad_scope,
    locator_is_credential,
    locator_is_network,
    neutral_flags,
    reject_answer_key,
    reject_authority_payload,
)
from hg_runtime.generalization_eval.cases import (
    accept_acquired_mini_task,
    define_heldout_case,
    define_transfer_eval_case,
    proof_gate_to_fpga_trng_case,
    register_skill_transfer_candidate,
)
from hg_runtime.generalization_eval.splits import create_case_split, require_split_record
from hg_runtime.generalization_eval.leakage import audit_leakage, require_leakage_audit
from hg_runtime.generalization_eval.rubrics import create_rubric, has_rubric
from hg_runtime.generalization_eval.scoring import score_transfer
from hg_runtime.generalization_eval.controls import run_negative_control, run_positive_control
from hg_runtime.generalization_eval.claims import bounded_claim_scope, build_claim_scope
from hg_runtime.generalization_eval.receipts import (
    build_domain_readiness,
    build_generalization_receipt,
    build_generalization_result,
)
from hg_runtime.generalization_eval.replay import (
    EvalRecord,
    EvalReplayResult,
    GeneralizationEvalLog,
)
from hg_runtime.generalization_eval.gate import (
    evaluate_phase31_gate,
    validate_phase31_proof_bundle,
)

__all__ = [
    "EvalRecord",
    "EvalReplayResult",
    "GeneralizationEvalError",
    "GeneralizationEvalLog",
    "accept_acquired_mini_task",
    "audit_leakage",
    "bounded_claim_scope",
    "build_claim_scope",
    "build_domain_readiness",
    "build_generalization_receipt",
    "build_generalization_result",
    "create_case_split",
    "create_rubric",
    "define_heldout_case",
    "define_transfer_eval_case",
    "evaluate_phase31_gate",
    "has_rubric",
    "is_broad_scope",
    "locator_is_credential",
    "locator_is_network",
    "neutral_flags",
    "proof_gate_to_fpga_trng_case",
    "register_skill_transfer_candidate",
    "reject_answer_key",
    "reject_authority_payload",
    "require_leakage_audit",
    "require_split_record",
    "run_negative_control",
    "run_positive_control",
    "score_transfer",
    "validate_phase31_proof_bundle",
]
