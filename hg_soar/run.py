"""SOAR Phase 1 run orchestration — pure, no bus, no execution."""

from __future__ import annotations

import os
from typing import Mapping

from hg_soar.critique import apply_critique, audit_d7
from hg_soar.d7 import arbitrate_d7
from hg_soar.domains import evaluate_all_domains
from hg_soar.types import SOARRun


def soar_enabled() -> bool:
    return os.environ.get("HG_SOAR_ENABLED", "1").strip().lower() not in ("0", "false", "no")


def run_soar(
    proposal: Mapping[str, object],
    *,
    context_refs: tuple[str, ...],
) -> SOARRun:
    """Evaluate D1–D7, arbitrate D7, audit with D7-Critique, return binding."""
    proposal_id = str(proposal.get("payload", {}).get("proposal_id") or proposal.get("event_id"))
    from hg_runtime.contract import stable_id

    request_id = stable_id("soar_req", proposal_id)
    input_refs = (proposal.get("event_id", proposal_id),) + context_refs

    evaluations = evaluate_all_domains(proposal=proposal, input_refs=input_refs)
    primary = arbitrate_d7(
        request_id=request_id,
        proposal_ref=proposal_id,
        evaluations=evaluations,
    )
    critique = audit_d7(primary, evaluations=evaluations)
    binding = apply_critique(primary, critique)

    return SOARRun(
        request_id=request_id,
        proposal_ref=proposal_id,
        domain_evaluations=evaluations,
        d7_decision=primary,
        d7_critique=critique,
        binding=binding,
        input_refs=input_refs,
    )


__all__ = ["run_soar", "soar_enabled"]
