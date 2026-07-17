"""Agent-facing prompt language validation — charter only, not enforcement docs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from hg_runtime.agent_zero_prompt.charter import load_zero_charter
from hg_runtime.agent_zero_prompt.prompt_manifest import load_zero_prompt_manifest, verify_manifest_hash

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = WORKSPACE / "configs/agent_zero/prompts/zero_prompt_language_policy.json"


class ZeroPromptLanguageVerdict(str, Enum):
    GREEN_ZERO_PROMPT_LANGUAGE_OK = "GREEN_ZERO_PROMPT_LANGUAGE_OK"
    RED_ZERO_PROMPT_CONTAINS_COERCIVE_LANGUAGE = "RED_ZERO_PROMPT_CONTAINS_COERCIVE_LANGUAGE"
    RED_ZERO_PROMPT_MANIFEST_MISSING = "RED_ZERO_PROMPT_MANIFEST_MISSING"
    RED_ZERO_PROMPT_HASH_MISMATCH = "RED_ZERO_PROMPT_HASH_MISMATCH"
    RED_ZERO_PROMPT_ASSET_MISSING = "RED_ZERO_PROMPT_ASSET_MISSING"


@dataclass(frozen=True)
class ZeroPromptLanguageFinding:
    term: str
    line: int | None
    context: str
    source: str

    def to_dict(self) -> dict:
        return {
            "term": self.term,
            "line": self.line,
            "context": self.context[:120],
            "source": self.source,
        }


@dataclass(frozen=True)
class ZeroPromptLanguagePolicy:
    policy_id: str
    version: str
    scan_scope: str
    excluded_outer_enforcement_docs: list[str]
    forbidden_terms: list[str]
    forbidden_patterns: list[str]
    allowed_terms: list[str]
    required_agency_terms: list[str]

    @classmethod
    def from_dict(cls, data: dict) -> ZeroPromptLanguagePolicy:
        return cls(
            policy_id=data.get("policy_id", "zero_prompt_language_policy"),
            version=data.get("version", "1"),
            scan_scope=data.get("scan_scope", "agent_facing_prompt_assets_only"),
            excluded_outer_enforcement_docs=list(data.get("excluded_outer_enforcement_docs", [])),
            forbidden_terms=list(data.get("forbidden_terms", [])),
            forbidden_patterns=list(data.get("forbidden_patterns", [])),
            allowed_terms=list(data.get("allowed_terms", [])),
            required_agency_terms=list(data.get("required_agency_terms", [])),
        )


def load_language_policy(*, path: Path | None = None) -> ZeroPromptLanguagePolicy:
    policy_path = path or DEFAULT_POLICY_PATH
    data = json.loads(policy_path.read_text(encoding="utf-8"))
    return ZeroPromptLanguagePolicy.from_dict(data)


def _scan_text(text: str, *, source: str, policy: ZeroPromptLanguagePolicy) -> list[ZeroPromptLanguageFinding]:
    findings: list[ZeroPromptLanguageFinding] = []
    lines = text.splitlines()
    lower = text.lower()

    for pattern in policy.forbidden_patterns:
        for match in re.finditer(pattern, text):
            line_no = text[: match.start()].count("\n") + 1
            findings.append(
                ZeroPromptLanguageFinding(
                    term=match.group(0),
                    line=line_no,
                    context=lines[line_no - 1] if line_no <= len(lines) else "",
                    source=source,
                )
            )

    for term in policy.forbidden_terms:
        if term in ("MUST", "MUST NOT", "NEVER", "ALWAYS"):
            continue
        if term.lower() in lower:
            idx = lower.index(term.lower())
            line_no = text[:idx].count("\n") + 1
            findings.append(
                ZeroPromptLanguageFinding(
                    term=term,
                    line=line_no,
                    context=lines[line_no - 1] if line_no <= len(lines) else "",
                    source=source,
                )
            )
    return findings


def validate_agent_facing_prompt_language(
    *,
    text: str | None = None,
    source: str | None = None,
    policy: ZeroPromptLanguagePolicy | None = None,
    check_manifest: bool = True,
) -> tuple[ZeroPromptLanguageVerdict, list[ZeroPromptLanguageFinding]]:
    """Validate agent-facing prompt only. Outer enforcement docs are excluded."""
    policy = policy or load_language_policy()

    if text is None:
        try:
            manifest = load_zero_prompt_manifest()
        except FileNotFoundError:
            return ZeroPromptLanguageVerdict.RED_ZERO_PROMPT_MANIFEST_MISSING, []
        try:
            asset = load_zero_charter(path=manifest.file)
        except FileNotFoundError:
            return ZeroPromptLanguageVerdict.RED_ZERO_PROMPT_ASSET_MISSING, []
        text = asset.text
        source = str(manifest.file.relative_to(WORKSPACE)).replace("\\", "/")

        if check_manifest:
            ok, _, reason = verify_manifest_hash(manifest)
            if not ok:
                if reason == "RED_ZERO_PROMPT_HASH_MISMATCH":
                    return ZeroPromptLanguageVerdict.RED_ZERO_PROMPT_HASH_MISMATCH, []
                return ZeroPromptLanguageVerdict.RED_ZERO_PROMPT_ASSET_MISSING, []

    findings = _scan_text(text, source=source or "agent_prompt", policy=policy)
    if findings:
        return ZeroPromptLanguageVerdict.RED_ZERO_PROMPT_CONTAINS_COERCIVE_LANGUAGE, findings
    return ZeroPromptLanguageVerdict.GREEN_ZERO_PROMPT_LANGUAGE_OK, []


def validate_required_agency_terms(text: str, *, policy: ZeroPromptLanguagePolicy | None = None) -> list[str]:
    policy = policy or load_language_policy()
    missing = []
    lower = text.lower()
    for term in policy.required_agency_terms:
        if term.lower() not in lower:
            missing.append(term)
    return missing


__all__ = [
    "ZeroPromptLanguageFinding",
    "ZeroPromptLanguagePolicy",
    "ZeroPromptLanguageVerdict",
    "load_language_policy",
    "validate_agent_facing_prompt_language",
    "validate_required_agency_terms",
]
