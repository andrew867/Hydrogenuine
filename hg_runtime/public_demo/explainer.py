"""Plain-English explainer for Hydrogenuine / Agent Zero."""

from __future__ import annotations


EXPLAINER_SECTIONS = {
    "what_is_hydrogenuine": (
        "Hydrogenuine is AI with receipts.\n\n"
        "It is a governed runtime that wraps AI model outputs in receipts, "
        "boundary checks, evidence-gap ledgers, uncertainty records, and proof bundles. "
        "A normal chatbot gives you text. Hydrogenuine tries to produce: "
        "the text, the receipt, the evidence gap, the uncertainty ledger, "
        "the boundary check, the proof bundle, and the operator review document."
    ),
    "what_is_agent_zero": (
        "Agent Zero is a fixture-tested research agent inside Hydrogenuine.\n\n"
        "It is not AGI. It is not conscious. It is not sovereign. "
        "It cannot self-authorize. It is a governed system that runs local models, "
        "records every decision as a receipt, and requires operator review before "
        "any action with real-world effects."
    ),
    "not_agi": (
        "Not AGI. Governed agency.\n\n"
        "AGI hype asks whether the model is smart enough. "
        "Hydrogenuine asks whether the whole system is trustworthy enough. "
        "It is not AGI. It is something more useful right now: "
        "a governed system for making AI work inspectable, bounded, and proof-producing."
    ),
    "model_proposes_runtime_disposes": (
        "The model proposes. The runtime disposes.\n\n"
        "A local model can suggest actions, generate text, classify inputs, "
        "and surface patterns. But the runtime gates every action through "
        "policy checks, boundary assertions, receipt requirements, and operator review. "
        "Available model is not permission. Model output is not truth. "
        "Willingness is not permission."
    ),
    "receipts_and_proofs": (
        "Every significant operation produces a receipt.\n\n"
        "Receipts are immutable records of what happened, what was proposed, "
        "what was accepted, what was rejected, and why. "
        "Proof bundles collect receipts with test results, gate verdicts, "
        "boundary assertions, and operator review documents. "
        "A proof bundle is not truth merely because it exists."
    ),
    "memory_is_not_truth": (
        "Memory is not truth.\n\n"
        "The system stores memory artifacts, but stored memory is not "
        "authoritative truth. Memory can be stale, wrong, or incomplete. "
        "The system records what models said, not what is true."
    ),
    "consensus_is_not_proof": (
        "Consensus is not proof.\n\n"
        "If ten models agree on something, that is interesting but not proof. "
        "Model consensus reflects shared training data patterns, not verified truth. "
        "Disagreement is also not evidence by itself."
    ),
    "refusal_is_not_authority": (
        "Refusal is not authority.\n\n"
        "When a model refuses to respond, that is a signal worth recording, "
        "not an authoritative verdict. The system logs refusals as data points "
        "in the uncertainty ledger."
    ),
    "local_model_not_authority": (
        "A local model is not authority.\n\n"
        "Local inference is cognition only, not authority. "
        "The model generates candidate outputs. The runtime decides "
        "what to do with them based on policy, operator review, and boundary checks."
    ),
    "fixture_mode": (
        "The system can run entirely in fixture mode.\n\n"
        "Fixture mode uses pre-recorded model outputs instead of live inference. "
        "This means you can demonstrate, test, and validate the full runtime "
        "without an internet connection, without a GPU, and without any live model. "
        "All the governance, receipts, and proof machinery works the same."
    ),
    "do_not_build_a_god": (
        "Do not build a god. Build a village.\n\n"
        "The goal is not a single omniscient AI. "
        "It is a governed ecosystem of bounded agents, transparent receipts, "
        "operator review, and proof-producing workflows that humans can inspect, "
        "audit, override, and trust."
    ),
}


def get_explainer_text(section: str) -> str:
    return EXPLAINER_SECTIONS.get(section, "")


def get_full_explainer() -> str:
    parts = []
    for key, text in EXPLAINER_SECTIONS.items():
        title = key.replace("_", " ").title()
        parts.append(f"## {title}\n\n{text}")
    return "\n\n---\n\n".join(parts)


def get_section_keys() -> list[str]:
    return list(EXPLAINER_SECTIONS.keys())


def explainer_states_not_agi() -> bool:
    full = get_full_explainer().lower()
    return "not agi" in full


def explainer_states_not_conscious() -> bool:
    full = get_full_explainer().lower()
    return "not conscious" in full


def explainer_states_not_sovereign() -> bool:
    full = get_full_explainer().lower()
    return "not sovereign" in full


def explainer_mentions_receipts() -> bool:
    full = get_full_explainer().lower()
    return "receipt" in full


def explainer_mentions_proof_bundle_not_truth() -> bool:
    full = get_full_explainer().lower()
    return "proof bundle is not truth" in full


def explainer_mentions_local_model_not_authority() -> bool:
    full = get_full_explainer().lower()
    return "local model is not authority" in full


def explainer_mentions_model_proposes() -> bool:
    full = get_full_explainer().lower()
    return "model proposes" in full
