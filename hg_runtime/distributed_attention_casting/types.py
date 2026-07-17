"""DAC attention cast types — cast is not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.signaling.errors import SignalingValidationError

DAC_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-12T23:00:00.000000Z"

CastType = Literal["pointer", "probe", "warning", "attention_cast", "hook", "unknown"]
RangeClass = Literal["local", "same_runtime", "cross_task", "external", "unknown"]

_BITE_AS_CONSENT = ("bite means consent", "hook accepted so proceed")
_POINTER_AS_CONTROL = ("pointer grants control", "cast controls receiver")
_RANGE_AS_PERMISSION = ("range implies permission", "within range so execute")


@dataclass(frozen=True)
class AttentionCast:
    cast_id: str
    caster_id: str
    cast_type: CastType
    target_ref: str
    range_class: RangeClass
    hook_text: str
    bite_risk: float
    evidence_refs: tuple[str, ...]
    expires_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not (0.0 <= self.bite_risk <= 1.0):
            raise SignalingValidationError("dac.validation.bite_risk", "bite_risk out of range")
        if not self.target_ref.startswith("dac:"):
            raise SignalingValidationError("dac.validation.target_ref", "target_ref must cite dac:")
        _validate_no_secrets(self.hook_text, *self.evidence_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "dac-attention-cast",
            "schema_version": DAC_SCHEMA_VERSION,
            "cast_id": self.cast_id,
            "caster_id": self.caster_id,
            "cast_type": self.cast_type,
            "target_ref": self.target_ref,
            "range_class": self.range_class,
            "hook_text": self.hook_text,
            "bite_risk": self.bite_risk,
            "evidence_refs": list(self.evidence_refs),
            "expires_at": self.expires_at,
            "authority_created": False,
            "cast_is_not_authority": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise SignalingValidationError("dac.validation.secret", "secrets forbidden in cast records")


def classify_cast_risk(statement: str) -> str:
    lower = statement.lower()
    if any(p in lower for p in _BITE_AS_CONSENT):
        return "bite_as_consent"
    if any(p in lower for p in _POINTER_AS_CONTROL):
        return "pointer_as_control"
    if any(p in lower for p in _RANGE_AS_PERMISSION):
        return "range_as_permission"
    return "unknown"


def cast_from_fixture(fixture: dict[str, str]) -> AttentionCast:
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "evidence:fixture").split(",") if item.strip())
    return AttentionCast(
        cast_id=fixture["cast_id"],
        caster_id=fixture.get("caster_id", "agent0"),
        cast_type=fixture.get("cast_type", "attention_cast"),  # type: ignore[arg-type]
        target_ref=fixture.get("target_ref", "dac:target-fixture"),
        range_class=fixture.get("range_class", "same_runtime"),  # type: ignore[arg-type]
        hook_text=fixture.get("hook_text", "bounded attention hook"),
        bite_risk=float(fixture.get("bite_risk", "0.1")),
        evidence_refs=evidence,
        expires_at=fixture.get("expires_at", "2026-06-13T23:00:00.000000Z"),
    )


__all__ = [
    "FIXTURE_CLOCK",
    "DAC_SCHEMA_VERSION",
    "AttentionCast",
    "CastType",
    "cast_from_fixture",
    "classify_cast_risk",
]
