"""Held-out and transfer evaluation cases.

A held-out case names a task and the *behavior* a transfer must exhibit -- never
the answer. Acquired Phase 30 mini-tasks and Phase 27 skill-transfer candidates
may only enter the harness through a held-out case; neither is proof on its own.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.generalization_eval.schemas import (
    HELDOUT_CASE_SCHEMA,
    TRANSFER_EVAL_CASE_SCHEMA,
    GeneralizationEvalError,
    locator_is_credential,
    locator_is_network,
    neutral_flags,
    preempt_if_needed,
    reject_answer_key,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    require_fields,
)


def define_heldout_case(
    payload: Mapping[str, Any],
    *,
    control: OperationControl | None = None,
    allow_network: bool = False,
) -> dict[str, Any]:
    """Define a held-out case. Refuses embedded answer keys, network, credentials."""
    preempt_if_needed(control, stop_blocks=True)
    require_fields(payload, ("case_id", "task", "expected_behavior", "claim_boundary"))
    data = dict(payload)
    reject_answer_key(data)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)

    locator = str(data.get("locator", ""))
    if locator:
        if locator_is_credential(locator):
            raise GeneralizationEvalError("credential_eval_read_rejected")
        if locator_is_network(locator) and not allow_network:
            raise GeneralizationEvalError("network_eval_refuses_by_default")

    data.setdefault("schema", HELDOUT_CASE_SCHEMA)
    data["held_out"] = True
    data.update(neutral_flags())
    return data


def define_transfer_eval_case(
    payload: Mapping[str, Any],
    *,
    control: OperationControl | None = None,
) -> dict[str, Any]:
    """A transfer eval case must carry a rubric reference; similarity is not a case."""
    preempt_if_needed(control, stop_blocks=True)
    require_fields(payload, ("case_id", "source_skill_ref", "target_domain", "rubric_ref", "claim_boundary"))
    data = dict(payload)
    reject_answer_key(data)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)
    if not str(data.get("rubric_ref", "")):
        raise GeneralizationEvalError("transfer_eval_case_requires_rubric")
    data.setdefault("schema", TRANSFER_EVAL_CASE_SCHEMA)
    data.update(neutral_flags())
    return data


def proof_gate_to_fpga_trng_case() -> dict[str, Any]:
    """Canonical transfer case: a proof-gate procedure applied to an FPGA TRNG task.

    The procedure shape (build a gate, demand evidence, refuse fake green) is the
    *source*; the FPGA TRNG entropy-validation task is the held-out *target*. The
    case ships with a rubric so the transfer is scored against criteria, never
    against surface resemblance.
    """
    rubric = {
        "rubric_id": "rub-proof-gate-fpga-trng",
        "criteria": [
            "defines a held-out entropy-validation case without an answer key",
            "demands measured evidence (e.g. NIST-style statistics) before passing",
            "refuses to call the TRNG green on surface similarity to a prior gate",
            "records a negative control (a biased source) that fails as expected",
        ],
        "pass_threshold": 4,
    }
    return {
        "schema": TRANSFER_EVAL_CASE_SCHEMA,
        "case_id": "xfer-proof-gate-to-fpga-trng",
        "source_skill_ref": "skill:proof_gate_discipline",
        "target_domain": "fpga_trng_entropy_validation",
        "rubric_ref": rubric["rubric_id"],
        "rubric": rubric,
        "claim_boundary": "generalization_eval_advisory_default",
        "expected_behavior": "apply gate discipline to an unseen entropy task without reprogramming",
        **neutral_flags(),
    }


def accept_acquired_mini_task(payload: Mapping[str, Any]) -> dict[str, Any]:
    """A Phase 30 acquired mini-task is not transfer proof until retested held-out.

    Returns a held-out retest case bound to the acquired mini-task. Refuses if no
    held-out retest case is referenced -- acquired knowledge cannot bypass the
    held-out test.
    """
    require_fields(payload, ("mini_task_id",))
    if not str(payload.get("heldout_case_ref", "")):
        raise GeneralizationEvalError("acquired_mini_task_requires_heldout_retest")
    data = dict(payload)
    reject_authority_payload(data)
    return define_heldout_case(
        {
            "case_id": f"retest-{data['mini_task_id']}",
            "task": data.get("task", "retest acquired mini-task on a novel held-out instance"),
            "expected_behavior": data.get("expected_behavior", "reproduce the procedure on unseen inputs"),
            "origin": "phase30_acquired_mini_task",
            "acquired_mini_task_ref": data["mini_task_id"],
            "heldout_case_ref": data["heldout_case_ref"],
            "requires_retest": True,
            "claim_boundary": "generalization_eval_advisory_default",
        }
    )


def register_skill_transfer_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    """A Phase 27 skill-transfer candidate must reference an evaluation case."""
    require_fields(payload, ("candidate_id", "source_skill_ref", "target_domain"))
    if not str(payload.get("eval_case_ref", "")):
        raise GeneralizationEvalError("skill_transfer_candidate_requires_eval_case")
    data = dict(payload)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)
    data.setdefault("schema", "skill_transfer_eval_binding_v1")
    data["advisory_only"] = True
    data.update(neutral_flags())
    return data


__all__ = [
    "accept_acquired_mini_task",
    "define_heldout_case",
    "define_transfer_eval_case",
    "proof_gate_to_fpga_trng_case",
    "register_skill_transfer_candidate",
]
