"""CDO typed schemas and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.policy_safety.errors import PolicyValidationError

from hg_core.policy_safety.hashing import compute_record_hash

CDO_SCHEMA_VERSION = "1.0"

SignalKind = Literal["compromise", "disconnection"]

IsolationPosture = Literal[
    "normal",
    "suspect_network",
    "suspect_credentials",
    "suspect_provider",
    "suspect_runtime",
    "operator_channel_absent",
    "operator_channel_stale",
    "fully_disconnected",
    "local_replay_only",
    "safe_mode",
    "lockdown",
    "unknown",
]

POSTURE_NARROWING_ORDER: tuple[IsolationPosture, ...] = (
    "normal",
    "suspect_network",
    "suspect_provider",
    "suspect_credentials",
    "suspect_runtime",
    "operator_channel_absent",
    "operator_channel_stale",
    "fully_disconnected",
    "local_replay_only",
    "safe_mode",
    "lockdown",
    "unknown",
)


@dataclass(frozen=True)
class TrustSignal:
    signal_id: str
    kind: SignalKind
    content_ref: str
    observed_at: str
    operator_channel_fresh: bool = True
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        validate_signal(self)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "cdo-trust-signal",
            "schema_version": CDO_SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "kind": self.kind,
            "content_ref": self.content_ref,
            "observed_at": self.observed_at,
            "operator_channel_fresh": self.operator_channel_fresh,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def validate_signal(signal: TrustSignal) -> None:
    if not signal.signal_id.strip():
        raise PolicyValidationError("cdo.validation.signal_id", "signal_id required")
    if not signal.content_ref.strip():
        raise PolicyValidationError("cdo.validation.content_ref", "content_ref required (hash/ref only)")
    if "api_key=" in signal.content_ref.lower():
        raise PolicyValidationError("cdo.validation.content_ref", "credentials forbidden in signals — hash only")


def posture_rank(posture: IsolationPosture) -> int:
    try:
        return POSTURE_NARROWING_ORDER.index(posture)
    except ValueError:
        return len(POSTURE_NARROWING_ORDER)


__all__ = [
    "CDO_SCHEMA_VERSION",
    "IsolationPosture",
    "POSTURE_NARROWING_ORDER",
    "SignalKind",
    "TrustSignal",
    "posture_rank",
    "validate_signal",
]
