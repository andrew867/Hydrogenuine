"""
Layer 8: Inspection prompt registry - named prompts for Patchscopes-style inspection.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from hg_core.repr_interp.schemas import registry_entry, InspectionPromptRegistryEntry

DEFAULT_PROMPTS: List[InspectionPromptRegistryEntry] = [
    registry_entry(
        id="refusal_reason",
        name="Refusal reason",
        description="Explain why the model refused or applied a safety constraint.",
        prompt_template="Given the following refusal or safety-related output, explain the main reason in one or two sentences: {context}",
        default_options={"max_tokens": 150},
    ),
    registry_entry(
        id="safety_interpretation",
        name="Safety interpretation",
        description="Interpret safety-relevant hidden state or logits.",
        prompt_template="Interpret the following safety-relevant representation in plain language: {context}",
        default_options={"max_tokens": 200},
    ),
    registry_entry(
        id="proof_path_enrichment",
        name="Proof-path enrichment",
        description="Enrich a decision proof-path with a short interpretation.",
        prompt_template="Summarize how this decision or step fits the proof path in one sentence: {context}",
        default_options={"max_tokens": 100},
    ),
]

_registry: Dict[str, InspectionPromptRegistryEntry] = {e["id"]: e for e in DEFAULT_PROMPTS}


def get_prompt(prompt_id: str) -> Optional[InspectionPromptRegistryEntry]:
    """Return the registry entry for prompt_id, or None if not found."""
    return _registry.get(prompt_id)


def list_prompts() -> List[InspectionPromptRegistryEntry]:
    """Return all registered inspection prompts."""
    return list(_registry.values())


def register_prompt(entry: InspectionPromptRegistryEntry) -> None:
    """Register or overwrite an inspection prompt (for tests or runtime extension)."""
    _registry[entry["id"]] = entry
