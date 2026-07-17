"""Scenario schema for the reusable GRS demo runner.

Doctrine encoded here, not in prose:
- live_local_model mode FAILS if the endpoint is unavailable — never silent fallback.
- fixture mode is visibly labelled and can never produce public GREEN.
- the local signed demo operator is not production auth (field is pinned false).
- cloud providers are disabled unless explicitly allowed.
- source mode is explicit (fixture / live_allowlist / disabled).
"""
from __future__ import annotations

from typing import Any

MODES = {"fixture", "live_local_model", "guided_replay"}
SOURCE_MODES = {"fixture", "live_allowlist", "disabled"}
OPERATOR_MODES = {"fixture_simulated_operator", "local_signed_demo_operator",
                  "guided_replay_operator"}


class ScenarioError(ValueError):
    """Scenario config is invalid; runs must not start."""


def _require(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def validate_scenario(s: dict[str, Any]) -> list[str]:
    """Return a list of violations (empty = valid). Fail closed on anything odd."""
    errors: list[str] = []
    for field in ("scenario_id", "title", "description", "question", "mode",
                  "model", "sources", "quality_gate", "quarantine",
                  "operator_review", "outputs", "claim_boundaries"):
        _require(field in s, f"missing required field: {field}", errors)
    if errors:
        return errors

    _require(s["mode"] in MODES, f"mode must be one of {sorted(MODES)}", errors)

    model = s["model"]
    _require(isinstance(model.get("require_live_model"), bool),
             "model.require_live_model must be bool", errors)
    _require(model.get("cloud_providers_allowed", False) is False
             or model.get("cloud_providers_allowed_reason"),
             "cloud providers require explicit cloud_providers_allowed_reason", errors)
    if s["mode"] == "live_local_model":
        _require(bool(model.get("endpoint")), "live_local_model requires model.endpoint", errors)
        _require(model.get("require_live_model") is True,
                 "live_local_model requires model.require_live_model=true (no silent fallback)",
                 errors)

    sources = s["sources"]
    _require(sources.get("mode") in SOURCE_MODES,
             f"sources.mode must be one of {sorted(SOURCE_MODES)}", errors)
    if sources.get("mode") == "live_allowlist":
        _require(bool(sources.get("allowlist")),
                 "live_allowlist requires a non-empty sources.allowlist", errors)
        _require(int(sources.get("minimum_source_count", 0)) >= 1,
                 "live_allowlist requires minimum_source_count >= 1", errors)

    op = s["operator_review"]
    _require(op.get("mode") in OPERATOR_MODES,
             f"operator_review.mode must be one of {sorted(OPERATOR_MODES)}", errors)
    _require(op.get("production_operator_auth") is False,
             "operator_review.production_operator_auth must be false "
             "(local signed demo operator is not production auth)", errors)

    q = s["quarantine"]
    _require(isinstance(q.get("enabled"), bool), "quarantine.enabled must be bool", errors)
    if q.get("enabled"):
        _require(q.get("promotion_requires_review") is True,
                 "quarantine requires promotion_requires_review=true", errors)

    cb = s["claim_boundaries"]
    for key in ("no_model_correctness", "no_production_auth", "no_customer_deployment",
                "no_certification", "source_is_not_truth"):
        _require(cb.get(key) is True, f"claim_boundaries.{key} must be true", errors)

    return errors


def load_scenario(data: dict[str, Any]) -> dict[str, Any]:
    errors = validate_scenario(data)
    if errors:
        raise ScenarioError("; ".join(errors))
    return data


def publicability(s: dict[str, Any]) -> str:
    """fixture/guided_replay can never be public-live; live can be public-capable."""
    if s["mode"] != "live_local_model" or s["sources"]["mode"] != "live_allowlist":
        return "INTERNAL_ONLY"
    if s["operator_review"]["mode"] == "fixture_simulated_operator":
        return "INTERNAL_ONLY"
    return "PUBLIC_CAPABLE"


def data_tier(s: dict[str, Any]) -> str:
    live_model = s["mode"] == "live_local_model"
    live_sources = s["sources"]["mode"] == "live_allowlist"
    if live_model and live_sources:
        return "live"
    if live_model or live_sources:
        return "mixed"
    return "fixture"
