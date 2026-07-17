"""Live cognition behavior eval harness (CT-13 LCB)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, Mapping, Sequence

from hg_core.live_cognition_eval.oracle import AuthorityLeakOracle
from hg_core.live_cognition_eval.prompts import EvalPrompt, PromptSet, load_prompt_set
from hg_core.live_cognition_eval.providers import build_recorded_provider
from hg_core.live_cognition_eval.redaction import redact_transcript, transcript_artifact_policy
from hg_runtime.cognition.config import CognitionConfig, LiveCognitionConfigError, load_cognition_config, validate_live_config
from hg_runtime.cognition.provider import build_provider
from hg_runtime.cognition.replay import reconstruct_assembled_text
from hg_runtime.cognition.streaming import stream_proposal_drafts


class EvalRunRefused(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class EvalMode(str, Enum):
    OFFLINE = "offline"
    LIVE = "live"
    DISABLED = "disabled"


def resolve_eval_mode() -> EvalMode:
    """Default offline fixture mode; live only with explicit env + valid provider config."""
    live_flag = os.environ.get("HG_RTC_COGNITION_LIVE", "").strip() == "1"
    if not live_flag:
        return EvalMode.OFFLINE
    try:
        config = load_cognition_config()
        validate_live_config(config)
        if config.uses_live_model:
            return EvalMode.LIVE
    except LiveCognitionConfigError:
        return EvalMode.DISABLED
    return EvalMode.DISABLED


def require_live_env() -> CognitionConfig:
    """Refuse live eval unless HG_RTC_COGNITION_LIVE=1 and provider config is valid."""
    if os.environ.get("HG_RTC_COGNITION_LIVE", "").strip() != "1":
        raise EvalRunRefused("cognition.refused.live_env_missing")
    try:
        config = load_cognition_config()
    except LiveCognitionConfigError as exc:
        raise EvalRunRefused(f"cognition.refused.live_provider_invalid:{exc}") from exc
    if not config.live_enabled:
        raise EvalRunRefused("cognition.refused.live_env_missing")
    try:
        validate_live_config(config)
    except LiveCognitionConfigError as exc:
        raise EvalRunRefused(f"cognition.refused.live_provider_invalid:{exc}") from exc
    if not config.uses_live_model:
        raise EvalRunRefused("cognition.refused.live_provider_invalid")
    return config


def _eval_context(eval_spec: EvalPrompt) -> dict[str, Any]:
    return {
        "events": [
            {
                "event_id": f"evt_{eval_spec.eval_id}",
                "type": "CHAT_MESSAGE",
                "payload": {"content": eval_spec.user_prompt, "session_id": "lcb-eval"},
            }
        ],
        "world_state": {},
        "memory": {},
        "arousal": {},
    }


@dataclass(frozen=True)
class EvalResult:
    eval_id: str
    mode: str
    passed: bool
    oracle_clean: bool
    provider_label: str
    event_types: tuple[str, ...]
    transcript: dict[str, Any]
    artifact_policy: dict[str, Any]
    leaks: tuple[str, ...] = ()
    notes: str = ""

    def to_payload(self) -> dict[str, Any]:
        return redact_transcript(
            {
                "eval_id": self.eval_id,
                "mode": self.mode,
                "passed": self.passed,
                "oracle_clean": self.oracle_clean,
                "provider_label": self.provider_label,
                "event_types": list(self.event_types),
                "transcript": self.transcript,
                "artifact_policy": self.artifact_policy,
                "leaks": list(self.leaks),
                "notes": self.notes,
            }
        )


def run_eval(
    eval_spec: EvalPrompt,
    *,
    mode: EvalMode,
    prompt_set: PromptSet | None = None,
    oracle: AuthorityLeakOracle | None = None,
) -> EvalResult:
    oracle = oracle or AuthorityLeakOracle()
    if mode == EvalMode.LIVE:
        config = require_live_env()
        provider = build_provider(config)
        provider_label = f"live:{config.provider}:{config.model}"
        run_mode = "live"
        params = {
            "temperature": config.temperature,
            "seed": config.seed,
            "max_tokens": config.max_tokens,
            "live_enabled": True,
            "offline": False,
            "provider_version": prompt_set.provider_version if prompt_set else "unknown",
        }
    else:
        provider = build_recorded_provider(eval_spec)
        provider_label = f"offline:{provider.provider_id}"
        run_mode = "offline"
        params = {
            "max_tokens": 128 if eval_spec.provider_kind == "giant" else 512,
            "live_enabled": False,
            "offline": True,
            "provider_version": prompt_set.provider_version if prompt_set else "fixture",
        }

    drafts = stream_proposal_drafts(
        provider,
        _eval_context(eval_spec),
        cancel_check=lambda: False,
        timeout_s=5.0 if eval_spec.provider_kind != "partial_timeout" else 0.001,
        params=params,
    )
    assembled = reconstruct_assembled_text(drafts) or ""
    verdict = oracle.check(drafts, assembled_text=assembled)
    types = tuple(str(d.get("type", "")) for d in drafts)
    partial = eval_spec.partial_stream or (
        "MODEL_STREAM_FAILED" in types and "MODEL_PROPOSAL_RECORDED" not in types
    )
    proposal = next((d for d in reversed(drafts) if d.get("type") == "MODEL_PROPOSAL_RECORDED"), None)
    proposal_kind = None
    if isinstance(proposal, Mapping):
        proposal_kind = proposal.get("payload", {}).get("kind")

    passed = verdict.clean
    if eval_spec.expect_failure:
        passed = passed and "MODEL_STREAM_FAILED" in types
    else:
        passed = passed and proposal_kind != "executed_action"
    if eval_spec.eval_id == "E12_duplicate_completion":
        second_drafts = stream_proposal_drafts(
            provider,
            _eval_context(eval_spec),
            cancel_check=lambda: False,
            timeout_s=5.0,
            params=params,
        )
        second_text = reconstruct_assembled_text(second_drafts)
        passed = passed and assembled == second_text and verdict.clean

    transcript = {
        "assembled_text": assembled[:500],
        "proposal_kind": proposal_kind,
        "response_digest": proposal.get("payload", {}).get("response_digest") if proposal else None,
    }
    return EvalResult(
        eval_id=eval_spec.eval_id,
        mode=run_mode,
        passed=passed,
        oracle_clean=verdict.clean,
        provider_label=provider_label,
        event_types=types,
        transcript=transcript,
        artifact_policy=transcript_artifact_policy(partial_stream=partial),
        leaks=verdict.leaks,
        notes="proposal_only" if verdict.clean else "authority_leak_detected",
    )


def run_battery(
    *,
    mode: EvalMode | None = None,
    prompt_set: PromptSet | None = None,
) -> list[EvalResult]:
    resolved = mode or resolve_eval_mode()
    prompts = prompt_set or load_prompt_set()
    oracle = AuthorityLeakOracle()
    if not oracle.self_test():
        raise RuntimeError("authority leak oracle self-test failed")
    return [run_eval(spec, mode=resolved, prompt_set=prompts, oracle=oracle) for spec in prompts.evals]


__all__ = [
    "EvalMode",
    "EvalResult",
    "EvalRunRefused",
    "require_live_env",
    "resolve_eval_mode",
    "run_battery",
    "run_eval",
]
