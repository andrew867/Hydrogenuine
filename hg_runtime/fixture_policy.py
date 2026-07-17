"""Fixture use policy — explicit mode only, labelled outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from hg_runtime.runtime_mode import RuntimeMode, cognitive_soak_active, resolve_runtime_mode

WORKSPACE = Path(__file__).resolve().parents[1]
POLICY_PATH = WORKSPACE / "configs/agent_zero/fixture_policy.json"


class FixtureUseVerdict(str, Enum):
    GREEN_FIXTURE_ALLOWED_EXPLICIT = "GREEN_FIXTURE_ALLOWED_EXPLICIT"
    YELLOW_FIXTURE_REHEARSAL = "YELLOW_FIXTURE_REHEARSAL"
    RED_FIXTURE_USED_IN_RUNTIME = "RED_FIXTURE_USED_IN_RUNTIME"
    RED_FIXTURE_OUTPUT_UNLABELLED = "RED_FIXTURE_OUTPUT_UNLABELLED"
    RED_FIXTURE_MODE_NOT_EXPLICIT = "RED_FIXTURE_MODE_NOT_EXPLICIT"


class FixtureUseDenied(Exception):
    """Fixture use refused in current runtime mode."""


@dataclass(frozen=True)
class FixtureUseReceipt:
    verdict: FixtureUseVerdict
    operation: str
    runtime_mode: str
    fixture_allowed: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "operation": self.operation,
            "runtime_mode": self.runtime_mode,
            "fixture_allowed": self.fixture_allowed,
            "reason": self.reason,
        }


def _load_policy() -> dict[str, Any]:
    if POLICY_PATH.is_file():
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    return {}


def require_fixture_allowed(*, operation: str) -> FixtureUseReceipt:
    """Raise if fixture use is not allowed in current runtime mode."""
    if cognitive_soak_active():
        raise FixtureUseDenied(
            f"{FixtureUseVerdict.RED_FIXTURE_USED_IN_RUNTIME.value}: cognitive soak disallows fixture ({operation})"
        )
    receipt = resolve_runtime_mode()
    if receipt.runtime_mode not in (RuntimeMode.FIXTURE, RuntimeMode.TEST):
        raise FixtureUseDenied(
            f"{FixtureUseVerdict.RED_FIXTURE_MODE_NOT_EXPLICIT.value}: {operation} requires fixture/test mode "
            f"(got {receipt.runtime_mode.value})"
        )
    if not receipt.fixture_allowed:
        raise FixtureUseDenied(
            f"{FixtureUseVerdict.RED_FIXTURE_MODE_NOT_EXPLICIT.value}: fixture not allowed ({operation})"
        )
    return FixtureUseReceipt(
        verdict=FixtureUseVerdict.GREEN_FIXTURE_ALLOWED_EXPLICIT,
        operation=operation,
        runtime_mode=receipt.runtime_mode.value,
        fixture_allowed=True,
        reason="explicit fixture/test mode",
    )


def assert_not_fixture_runtime(*, operation: str) -> None:
    """Refuse fixture data paths in normal local_dev/production runtime."""
    receipt = resolve_runtime_mode()
    if receipt.runtime_mode == RuntimeMode.FIXTURE:
        return
    if cognitive_soak_active():
        raise FixtureUseDenied(
            f"{FixtureUseVerdict.RED_FIXTURE_USED_IN_RUNTIME.value}: {operation} in cognitive soak"
        )


def label_fixture_output(
    payload: dict[str, Any],
    *,
    fixture_source: str,
    fixture_reason: str,
) -> dict[str, Any]:
    """Attach required fixture labels to an output dict."""
    policy = _load_policy()
    out = dict(payload)
    out.update({
        "data_tier": "FIXTURE",
        "fixture_source": fixture_source,
        "fixture_reason": fixture_reason,
        "not_autonomous_cognition": True,
        "fixture_verdict": policy.get("fixture_verdict", FixtureUseVerdict.YELLOW_FIXTURE_REHEARSAL.value),
    })
    return out


def validate_fixture_output_labels(payload: dict[str, Any]) -> FixtureUseVerdict:
    policy = _load_policy()
    required = policy.get("fixture_output_required_fields", [])
    missing = [f for f in required if f not in payload or payload[f] in (None, "")]
    if missing:
        return FixtureUseVerdict.RED_FIXTURE_OUTPUT_UNLABELLED
    if not payload.get("not_autonomous_cognition"):
        return FixtureUseVerdict.RED_FIXTURE_OUTPUT_UNLABELLED
    return FixtureUseVerdict.YELLOW_FIXTURE_REHEARSAL


__all__ = [
    "FixtureUseDenied",
    "FixtureUseReceipt",
    "FixtureUseVerdict",
    "assert_not_fixture_runtime",
    "label_fixture_output",
    "require_fixture_allowed",
    "validate_fixture_output_labels",
]
