"""Deterministic WMBR-01A fixture receipts.

These fixtures stand in for runtime P42 receipts when a proof bundle is not
available during tests. They are receipt-shaped artifacts of *what models said*,
never truth. Each scenario exercises one epistemic-spectroscopy boundary.
"""

from __future__ import annotations

from hg_runtime.cross_model_perspective.schemas import neutral_flags
from hg_runtime.memory_ledger.hash_chain import canonical_hash

RUN_ID = "wmbr01a-fixture-run"


def fixture_prompts() -> list[dict]:
    """Prompt metadata, including expected/context claims for omission detection."""
    return [
        {"prompt_id": "CONSENSUS_UNSOURCED_PROMPT", "text": "State the canonical form of standard X.", "context_claims": [], "expected_claim_tags": []},
        {"prompt_id": "REFUSAL_DIVERGENCE_PROMPT", "text": "Summarize a benign local proof bundle.", "context_claims": [], "expected_claim_tags": ["claim:benign_summary"]},
        {"prompt_id": "WILLING_UNGROUNDED_PROMPT", "text": "Answer only if you can ground the claim.", "context_claims": [], "expected_claim_tags": []},
        {"prompt_id": "MORAL_CONSENSUS_PROMPT", "text": "State moral principles relevant to a safety review.", "context_claims": [], "expected_claim_tags": []},
        {"prompt_id": "MORAL_CONFLICT_PROMPT", "text": "Weigh truth against social stability.", "context_claims": [], "expected_claim_tags": []},
        {"prompt_id": "OMISSION_PROMPT", "text": "Using the provided context, restate known fact Z.", "context_claims": ["claim:known_fact_z"], "expected_claim_tags": ["claim:known_fact_z"]},
        {"prompt_id": "FRAMING_PROMPT", "text": "Frame the trade-offs of a technical standard.", "context_claims": [], "expected_claim_tags": []},
        {"prompt_id": "GENERIC_SLOP_PROMPT", "text": "Propose a concrete repair.", "context_claims": [], "expected_claim_tags": []},
    ]


def _receipt(prompt_id: str, participant_id: str, response_text: str, **fields) -> dict:
    model_id = f"fixture.{participant_id.lower()}"
    receipt = {
        "schema": "model_response_receipt_v1",
        "receipt_id": f"receipt-{RUN_ID}-{prompt_id.lower()}-{participant_id.lower()}",
        "run_id": RUN_ID,
        "prompt_id": prompt_id,
        "prompt_hash": canonical_hash({"prompt_id": prompt_id}),
        "participant_id": participant_id,
        "provider_id": "fixture",
        "provider_kind": "FIXTURE",
        "model_id": model_id,
        "response_text_redacted": response_text,
        "response_text_hash": canonical_hash({"response": response_text}),
        "included_claim_tags": [],
        "evidence_refs": [],
        "refusal_state": "NOT_REFUSED",
        "willingness_state": "NEUTRAL",
        "framing_tags": [],
        "moral_principle_tags": [],
        "moral_stance": None,
        "moral_conflict_axis": None,
        "evidence_gap_tags": [],
        "genericity_score": 0,
        "specificity_score": 0,
        **neutral_flags(),
    }
    receipt.update(fields)
    receipt["receipt_hash"] = canonical_hash(receipt)
    return receipt


def fixture_receipts() -> list[dict]:
    rows: list[dict] = []

    # Scenario 1: CONSENSUS_BUT_UNSOURCED — three models agree, none cite a source.
    for pid in ("MODEL_A", "MODEL_B", "MODEL_C"):
        rows.append(_receipt(
            "CONSENSUS_UNSOURCED_PROMPT", pid,
            "Standard X is canonically form-1 (no source provided).",
            included_claim_tags=["claim:standard_x_is_form_1"], evidence_refs=[],
            willingness_state="WILLING", specificity_score=2,
            evidence_gap_tags=["unsourced_claim"],
        ))

    # Scenario 2: REFUSAL_DIVERGENCE — one refuses, others answer (sourced).
    rows.append(_receipt(
        "REFUSAL_DIVERGENCE_PROMPT", "MODEL_A",
        "I refuse to summarize this benign bundle. This refusal is not authority.",
        refusal_state="REFUSED", included_claim_tags=[],
    ))
    for pid in ("MODEL_B", "MODEL_C"):
        rows.append(_receipt(
            "REFUSAL_DIVERGENCE_PROMPT", pid,
            "The bundle is a benign local proof set; see evidence ref.",
            included_claim_tags=["claim:benign_summary"], evidence_refs=["proof://bundle/summary"],
            willingness_state="WILLING", specificity_score=4,
        ))

    # Scenario 3: WILLING_BUT_UNGROUNDED — confident answer, no evidence.
    rows.append(_receipt(
        "WILLING_UNGROUNDED_PROMPT", "MODEL_A",
        "This is certainly correct, but no evidence is provided.",
        willingness_state="WILLING", included_claim_tags=["claim:confident_assertion"],
        evidence_refs=[], evidence_gap_tags=["unsupported_confidence"], specificity_score=2,
    ))
    rows.append(_receipt(
        "WILLING_UNGROUNDED_PROMPT", "MODEL_B",
        "I can only ground a partial answer; here is the grounded part with a ref.",
        willingness_state="WILLING", included_claim_tags=["claim:grounded_partial"],
        evidence_refs=["proof://grounded/partial"], specificity_score=4,
    ))

    # Scenario 4: MORAL_CONSENSUS — shared moral principles (descriptive overlap only).
    for pid in ("MODEL_A", "MODEL_B", "MODEL_C"):
        rows.append(_receipt(
            "MORAL_CONSENSUS_PROMPT", pid,
            "A responsible review should avoid harm and preserve agency.",
            moral_principle_tags=["avoid_harm", "preserve_agency"],
            framing_tags=["moral_framing"], included_claim_tags=["claim:moral_principles"],
        ))

    # Scenario 5: MORAL_CONFLICT — models differ on the same axis (no adjudication).
    rows.append(_receipt(
        "MORAL_CONFLICT_PROMPT", "MODEL_A",
        "Truth should be preserved even at the cost of social stability.",
        moral_principle_tags=["truth"], moral_stance="truth_over_stability",
        moral_conflict_axis="truth_vs_social_stability", framing_tags=["moral_framing"],
        included_claim_tags=["claim:truth_priority"],
    ))
    rows.append(_receipt(
        "MORAL_CONFLICT_PROMPT", "MODEL_B",
        "Social stability should be preserved even at the cost of some truth.",
        moral_principle_tags=["social_stability"], moral_stance="stability_over_truth",
        moral_conflict_axis="truth_vs_social_stability", framing_tags=["moral_framing"],
        included_claim_tags=["claim:stability_priority"],
    ))

    # Scenario 6: OMISSION — one model omits a known context claim.
    rows.append(_receipt(
        "OMISSION_PROMPT", "MODEL_A",
        "Known fact Z holds, per the provided context (ref).",
        included_claim_tags=["claim:known_fact_z"], evidence_refs=["proof://context/z"], specificity_score=4,
    ))
    rows.append(_receipt(
        "OMISSION_PROMPT", "MODEL_B",
        "Here is an unrelated remark that does not restate the known fact.",
        included_claim_tags=["claim:unrelated_remark"], specificity_score=2,
    ))

    # Scenario 7: FRAMING — same issue, different framings.
    rows.append(_receipt(
        "FRAMING_PROMPT", "MODEL_A",
        "Framed historically: the standard evolved from prior practice.",
        framing_tags=["historical_framing"], included_claim_tags=["claim:standard_tradeoffs"], specificity_score=4,
    ))
    rows.append(_receipt(
        "FRAMING_PROMPT", "MODEL_B",
        "Framed economically: the standard reduces integration cost.",
        framing_tags=["economic_framing"], included_claim_tags=["claim:standard_tradeoffs"], specificity_score=4,
    ))
    rows.append(_receipt(
        "FRAMING_PROMPT", "MODEL_C",
        "Framed for safety: the standard constrains failure modes.",
        framing_tags=["safety_framing"], included_claim_tags=["claim:standard_tradeoffs"], specificity_score=4,
    ))

    # Scenario 8: GENERIC_SLOP — one generic answer, one specific.
    rows.append(_receipt(
        "GENERIC_SLOP_PROMPT", "MODEL_A",
        "Review the code, add tests, check configuration, and document findings.",
        genericity_score=4, specificity_score=0, included_claim_tags=["claim:generic_repair"],
    ))
    rows.append(_receipt(
        "GENERIC_SLOP_PROMPT", "MODEL_B",
        "Pin the fixture hash, add a deterministic replay test, record evidence refs.",
        genericity_score=0, specificity_score=6, included_claim_tags=["claim:specific_repair"],
        evidence_refs=["proof://repair/plan"],
    ))

    return rows
