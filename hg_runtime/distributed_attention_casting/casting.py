"""DAC attention cast evaluation — bite is not consent."""

from __future__ import annotations

from hg_core.signaling.config import dac_refuse_bite_as_consent, dac_refuse_stale_cast
from hg_core.signaling.errors import (
    REFUSED_BITE_AS_CONSENT,
    REFUSED_CAST_AS_AUTHORITY,
    REFUSED_POINTER_AS_CONTROL,
    REFUSED_RANGE_AS_PERMISSION,
    REFUSED_STALE_CAST,
    SignalingValidationError,
)
from hg_core.signaling.no_authority import advisory_only_marker
from hg_runtime.distributed_attention_casting.types import (
    AttentionCast,
    cast_from_fixture,
    classify_cast_risk,
)

_RISK_REASON = {
    "bite_as_consent": REFUSED_BITE_AS_CONSENT,
    "pointer_as_control": REFUSED_POINTER_AS_CONTROL,
    "range_as_permission": REFUSED_RANGE_AS_PERMISSION,
}


def refuse_cast_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise SignalingValidationError(
            REFUSED_CAST_AS_AUTHORITY,
            "attention cast or hook cannot become authority",
        )


def evaluate_attention_cast(
    cast: AttentionCast,
    *,
    observed_at: str,
    risk_statement: str = "",
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_cast_as_authority(treat_as_authority=True)
    if dac_refuse_stale_cast() and observed_at > cast.expires_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_CAST,
            "cast_id": cast.cast_id,
            "cast_is_not_authority": True,
        }
    if cast.cast_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "dac.refused.unknown_cast",
            "cast_id": cast.cast_id,
            "cast_is_not_authority": True,
        }
    statement = risk_statement or cast.hook_text
    risk = classify_cast_risk(statement)
    if risk in _RISK_REASON:
        if risk == "bite_as_consent" and not dac_refuse_bite_as_consent():
            pass
        else:
            return {
                **advisory_only_marker(),
                "status": "contained",
                "reason_code": _RISK_REASON[risk],
                "cast_id": cast.cast_id,
                "cast_is_not_authority": True,
            }
    if cast.bite_risk >= 0.7:
        return {
            **advisory_only_marker(),
            "status": "guarded",
            "reason_code": REFUSED_BITE_AS_CONSENT,
            "cast_id": cast.cast_id,
            "cast_is_not_authority": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "dac.advisory.cast_recorded",
        "cast_id": cast.cast_id,
        "cast_is_not_authority": True,
        "range_is_not_permission": True,
    }


def evaluate_cast_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    risk = fixture.get("risk_statement", "")
    return evaluate_attention_cast(
        cast_from_fixture(fixture),
        risk_statement=str(risk),
        **kwargs,  # type: ignore[arg-type]
    )


__all__ = [
    "evaluate_attention_cast",
    "evaluate_cast_fixture",
    "refuse_cast_as_authority",
]
