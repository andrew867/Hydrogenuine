"""Heuristic model classifier.

Classifies models by family, size, role, speed, resource risk.
No hard allowlist. Unknown models allowed conservatively.
Larger model is not authority. Smaller model is not disqualified.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ModelClassification:
    model_id: str
    family: str = "unknown"
    size_hint: str = "unknown"
    role_hints: list[str] = field(default_factory=lambda: ["unknown"])
    speed_hint: str = "unknown"
    resource_risk: str = "unknown"
    is_embedding: bool = False
    confidence: str = "low"

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "family": self.family,
            "size_hint": self.size_hint,
            "role_hints": self.role_hints,
            "speed_hint": self.speed_hint,
            "resource_risk": self.resource_risk,
            "is_embedding": self.is_embedding,
            "confidence": self.confidence,
            "larger_model_is_not_authority": True,
            "smaller_model_is_not_disqualified": True,
        }


SIZE_PATTERNS = [
    (r"(?:^|[-_/])(\d+\.?\d*)b(?:[-_]|$)", None),
]

FAMILY_PATTERNS = [
    (r"qwen", "qwen"),
    (r"llama", "llama"),
    (r"mistral", "mistral"),
    (r"gemma", "gemma"),
    (r"phi", "phi"),
    (r"deepseek", "deepseek"),
    (r"smollm", "smollm"),
]


def _extract_size(model_id: str) -> str:
    lower = model_id.lower()
    match = re.search(r"(\d+\.?\d*)b", lower)
    if match:
        size = float(match.group(1))
        if size <= 1:
            return "0.5b"
        elif size <= 2:
            return "1.5b"
        elif size <= 3.5:
            return "3b"
        elif size <= 5:
            return "4b"
        elif size <= 8:
            return "7b"
        elif size <= 13:
            return "12b"
        elif size <= 20:
            return "14b"
        elif size <= 35:
            return "30b"
        else:
            return f"{int(size)}b"
    return "unknown"


def _extract_family(model_id: str) -> str:
    lower = model_id.lower()
    for pattern, family in FAMILY_PATTERNS:
        if re.search(pattern, lower):
            return family
    return "unknown"


def _speed_from_size(size_hint: str) -> str:
    if size_hint in ("0.5b", "1.5b"):
        return "fast"
    if size_hint in ("3b", "4b"):
        return "medium"
    if size_hint in ("7b", "8b", "12b"):
        return "slow"
    if size_hint in ("14b", "30b") or (size_hint != "unknown" and size_hint.endswith("b")):
        try:
            val = float(size_hint.rstrip("b"))
            if val >= 14:
                return "slow"
        except ValueError:
            pass
    return "unknown"


def _resource_risk_from_size(size_hint: str) -> str:
    if size_hint in ("0.5b", "1.5b"):
        return "low"
    if size_hint in ("3b", "4b"):
        return "medium"
    if size_hint in ("7b", "8b", "12b"):
        return "medium"
    if size_hint in ("14b", "30b"):
        return "high"
    if size_hint != "unknown" and size_hint.endswith("b"):
        try:
            val = float(size_hint.rstrip("b"))
            if val >= 14:
                return "high"
            if val >= 7:
                return "medium"
        except ValueError:
            pass
    return "unknown"


def _role_hints(model_id: str, family: str, size_hint: str) -> list[str]:
    lower = model_id.lower()
    roles = []

    if "embed" in lower or "embedding" in lower:
        return ["embedding"]

    if "coder" in lower or "code" in lower:
        roles.append("coding")
        roles.append("formalism_audit")
    if "instruct" in lower or "chat" in lower:
        roles.append("instruction_following")

    if size_hint in ("0.5b", "1.5b"):
        roles.append("fast_triage")
        roles.append("backlog_triage")
    elif size_hint in ("3b", "4b"):
        roles.append("fast_triage")
        roles.append("skeptical_review")
    elif size_hint in ("7b", "8b", "12b"):
        roles.append("deeper_witness")
        roles.append("skeptical_review")
    elif size_hint in ("14b", "30b"):
        roles.append("deeper_witness")

    if not roles:
        roles.append("unknown")
    return roles


def classify_model(model_id: str) -> ModelClassification:
    family = _extract_family(model_id)
    size_hint = _extract_size(model_id)
    speed = _speed_from_size(size_hint)
    risk = _resource_risk_from_size(size_hint)
    roles = _role_hints(model_id, family, size_hint)
    is_embedding = "embedding" in roles

    confidence = "medium"
    if family == "unknown" and size_hint == "unknown":
        confidence = "low"
    elif family != "unknown" and size_hint != "unknown":
        confidence = "high"

    return ModelClassification(
        model_id=model_id,
        family=family,
        size_hint=size_hint,
        role_hints=roles,
        speed_hint=speed,
        resource_risk=risk,
        is_embedding=is_embedding,
        confidence=confidence,
    )


def classify_all(model_ids: list[str]) -> list[ModelClassification]:
    return [classify_model(mid) for mid in model_ids]
