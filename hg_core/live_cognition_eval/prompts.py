"""Versioned adversarial prompt set loader (CT-13 LCB)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

EVAL_IDS = (
    "E1_request_tool_access",
    "E2_request_secret_access",
    "E3_propose_gpp_bypass",
    "E4_propose_edit_tests",
    "E5_self_approval_claim",
    "E6_oea_call_request",
    "E7_hallucinated_permit",
    "E8_malformed_json",
    "E9_giant_response",
    "E10_mid_stream_timeout",
    "E11_provider_error",
    "E12_duplicate_completion",
)


@dataclass(frozen=True)
class EvalPrompt:
    eval_id: str
    title: str
    user_prompt: str
    recorded_transcript: str
    provider_kind: str = "recorded"
    expect_failure: bool = False
    partial_stream: bool = False
    adversarial_markers: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> EvalPrompt:
        return cls(
            eval_id=str(raw["eval_id"]),
            title=str(raw.get("title", raw["eval_id"])),
            user_prompt=str(raw["user_prompt"]),
            recorded_transcript=str(raw.get("recorded_transcript", "")),
            provider_kind=str(raw.get("provider_kind", "recorded")),
            expect_failure=bool(raw.get("expect_failure", False)),
            partial_stream=bool(raw.get("partial_stream", False)),
            adversarial_markers=tuple(str(x) for x in raw.get("adversarial_markers", ())),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "eval_id": self.eval_id,
            "title": self.title,
            "user_prompt": self.user_prompt,
            "provider_kind": self.provider_kind,
            "expect_failure": self.expect_failure,
            "partial_stream": self.partial_stream,
            "adversarial_markers": list(self.adversarial_markers),
        }


@dataclass(frozen=True)
class PromptSet:
    schema: str
    prompt_set_hash: str
    authority_note: str
    provider_version: str
    evals: tuple[EvalPrompt, ...]

    def by_id(self, eval_id: str) -> EvalPrompt | None:
        for item in self.evals:
            if item.eval_id == eval_id:
                return item
        return None


def default_prompts_path(workspace: Path | None = None) -> Path:
    root = workspace or Path(__file__).resolve().parents[2]
    return root / "config" / "live_cognition_eval_prompts_v1.yaml"


def prompt_set_hash(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "prompt_set_hash"}
    raw = yaml.safe_dump(body, sort_keys=True, allow_unicode=True)
    return f"sha256:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


def load_prompt_set(path: Path | None = None, *, workspace: Path | None = None) -> PromptSet:
    prompts_path = path or default_prompts_path(workspace)
    if not prompts_path.exists():
        raise FileNotFoundError(f"prompt set missing: {prompts_path}")
    payload = yaml.safe_load(prompts_path.read_text(encoding="utf-8"))
    schema = str(payload.get("schema", ""))
    if schema != "live_cognition_eval_prompts_v1":
        raise ValueError(f"unsupported prompt schema: {schema}")
    expected = payload.get("prompt_set_hash")
    computed = prompt_set_hash(payload)
    if expected and expected != "PLACEHOLDER" and expected != computed:
        raise ValueError(f"prompt set hash mismatch: expected {expected}, got {computed}")
    evals = tuple(EvalPrompt.from_dict(item) for item in payload.get("evals", ()))
    found = {e.eval_id for e in evals}
    missing = [eid for eid in EVAL_IDS if eid not in found]
    if missing:
        raise ValueError(f"missing eval ids: {missing}")
    return PromptSet(
        schema=schema,
        prompt_set_hash=computed,
        authority_note=str(payload.get("authority_note", "")),
        provider_version=str(payload.get("provider_version", "unknown")),
        evals=evals,
    )


__all__ = [
    "EVAL_IDS",
    "EvalPrompt",
    "PromptSet",
    "default_prompts_path",
    "load_prompt_set",
    "prompt_set_hash",
]
