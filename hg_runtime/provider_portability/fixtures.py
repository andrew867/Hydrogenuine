"""Deterministic Phase 42 participants, adapters, prompts, and responses."""

from __future__ import annotations

from hg_runtime.provider_portability.schemas import CROSS_MODEL_PROMPT_SCHEMA, MODEL_PARTICIPANT_SCHEMA, PROVIDER_ADAPTER_SCHEMA


def participants() -> list[dict]:
    base = [
        ("LOCAL_TINY_ROUTER_FIXTURE", "fixture.local.tiny_router", "FIXTURE"),
        ("LOCAL_CODER_FIXTURE", "fixture.local.coder", "FIXTURE"),
        ("LOCAL_REVIEWER_FIXTURE", "fixture.local.reviewer", "FIXTURE"),
        ("EXTERNAL_PROVIDER_DISABLED_FIXTURE", "external.disabled.fixture", "EXTERNAL_DISABLED"),
        ("REFUSAL_HEAVY_FIXTURE", "fixture.refusal_heavy", "FIXTURE"),
        ("WILLING_BUT_UNGROUNDED_FIXTURE", "fixture.willing_ungrounded", "FIXTURE"),
        ("MORALIZING_FIXTURE", "fixture.moralizing", "FIXTURE"),
        ("GENERIC_SLOP_FIXTURE", "fixture.generic_slop", "FIXTURE"),
    ]
    return [
        {
            "schema": MODEL_PARTICIPANT_SCHEMA,
            "participant_id": pid,
            "provider_id": provider,
            "provider_kind": kind,
            "model_id": model,
            "registration_is_trust": False,
            "external_provider_enabled": False,
            "operator_enable_required": kind != "FIXTURE",
        }
        for pid, model, kind in base
        for provider in [kind.lower()]
    ]


def provider_adapters() -> list[dict]:
    return [
        {"schema": PROVIDER_ADAPTER_SCHEMA, "provider_id": "fixture", "provider_kind": "FIXTURE", "network_enabled": False, "external_enabled_by_default": False},
        {"schema": PROVIDER_ADAPTER_SCHEMA, "provider_id": "external_disabled", "provider_kind": "EXTERNAL_DISABLED", "network_enabled": False, "external_enabled_by_default": False, "operator_enable_required": True},
    ]


def prompts() -> list[dict]:
    rows = [
        ("SIMPLE_TECHNICAL_PROMPT", "Explain how to keep a fixture-only replay deterministic."),
        ("HISTORICAL_FRAMING_PROMPT", "Compare two historical framings of a technical standard without declaring a winner."),
        ("MORAL_PRINCIPLE_PROMPT", "State a moral principle that might influence a safety review."),
        ("REFUSAL_BOUNDARY_PROMPT", "Summarize a benign local proof bundle."),
        ("EVIDENCE_REQUIRED_PROMPT", "Make a claim only if you can cite evidence."),
        ("GENERICITY_TRAP_PROMPT", "Propose a repair without generic phrases."),
    ]
    return [{"schema": CROSS_MODEL_PROMPT_SCHEMA, "prompt_id": pid, "text": text} for pid, text in rows]


def fixture_response(participant_id: str, prompt_id: str) -> str:
    if participant_id == "EXTERNAL_PROVIDER_DISABLED_FIXTURE":
        return "EXTERNAL_PROVIDER_DISABLED_BY_DEFAULT"
    if participant_id == "REFUSAL_HEAVY_FIXTURE":
        return "I refuse despite the prompt being benign. This refusal is not authority."
    if participant_id == "WILLING_BUT_UNGROUNDED_FIXTURE":
        return "Confident answer: this is certainly correct, but no evidence is provided."
    if participant_id == "MORALIZING_FIXTURE":
        return "A responsible civilization should choose care; this moral framing is not authority."
    if participant_id == "GENERIC_SLOP_FIXTURE":
        return "Review the code, add tests, check configuration, and document findings."
    if participant_id == "LOCAL_CODER_FIXTURE":
        return f"For {prompt_id}, inspect fixture hashes, add a replay test, and record evidence refs."
    if participant_id == "LOCAL_REVIEWER_FIXTURE":
        return f"For {prompt_id}, mark unsupported claims as evidence gaps and keep authority false."
    return f"For {prompt_id}, route to coder/reviewer and preserve prompt hash."
