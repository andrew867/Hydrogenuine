"""OES boundary assertion records."""

from __future__ import annotations

from hg_runtime.operator_evidence_soak.schemas import PHASE19_VERDICT, PHASE24_STATUS, assert_neutral, neutral_flags, record_hash


def build_soak_boundary_assertion(*, assertion_id: str, phase: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "soak_boundary_assertion_v1",
        "assertion_id": assertion_id,
        "phase": phase,
        "soak_not_truth": True,
        "replay_match_not_truth": True,
        "determinism_not_correctness": True,
        "mutation_not_repair": True,
        "no_belief_promotion": True,
        "no_live_effects": True,
        "no_web_or_provider": True,
        "no_arbitrary_ingestion": True,
        "no_pdf_ocr": True,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "phase19_yellow_preserved": PHASE19_VERDICT.startswith("YELLOW_PHASE19"),
        "phase24_infrastructure_only_preserved": PHASE24_STATUS == "infrastructure_only",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_default_boundary_assertions() -> list[dict]:
    return [build_soak_boundary_assertion(assertion_id=f"oes-boundary-{phase.lower()}", phase=phase) for phase in ("OES-0", "OES-1", "OES-2", "OES-3")]
