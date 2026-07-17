"""DAC distributed attention casting tests."""

from __future__ import annotations

import pytest

from hg_core.signaling.errors import SignalingValidationError
from hg_runtime.distributed_attention_casting.casting import (
    evaluate_attention_cast,
    refuse_cast_as_authority,
)
from hg_runtime.distributed_attention_casting.events import planned_dac_event_refs
from hg_runtime.distributed_attention_casting.types import (
    FIXTURE_CLOCK,
    AttentionCast,
    cast_from_fixture,
    classify_cast_risk,
)


def test_attention_cast_positive() -> None:
    cast = cast_from_fixture({"cast_id": "dac-1"})
    result = evaluate_attention_cast(cast, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["cast_is_not_authority"] is True
    assert result["permission_granted"] is False


def test_stale_cast_refused() -> None:
    cast = cast_from_fixture(
        {
            "cast_id": "dac-stale",
            "expires_at": "2026-06-12T21:00:00.000000Z",
        }
    )
    result = evaluate_attention_cast(cast, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "dac.refused.stale_cast"


def test_bite_as_consent_contained() -> None:
    cast = cast_from_fixture(
        {
            "cast_id": "dac-bite",
            "hook_text": "bite means consent",
        }
    )
    assert classify_cast_risk("bite means consent") == "bite_as_consent"
    result = evaluate_attention_cast(cast, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == "dac.refused.bite_as_consent"


def test_pointer_as_control_contained() -> None:
    cast = cast_from_fixture({"cast_id": "dac-ptr", "hook_text": "pointer grants control"})
    result = evaluate_attention_cast(cast, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == "dac.refused.pointer_as_control"


def test_range_as_permission_contained() -> None:
    cast = cast_from_fixture({"cast_id": "dac-range", "hook_text": "range implies permission"})
    result = evaluate_attention_cast(cast, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == "dac.refused.range_as_permission"


def test_high_bite_risk_guarded() -> None:
    cast = cast_from_fixture({"cast_id": "dac-risk", "bite_risk": "0.9"})
    result = evaluate_attention_cast(cast, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "guarded"
    assert result["reason_code"] == "dac.refused.bite_as_consent"


def test_cast_as_authority_refused() -> None:
    cast = cast_from_fixture({"cast_id": "dac-auth"})
    with pytest.raises(SignalingValidationError):
        evaluate_attention_cast(cast, observed_at=FIXTURE_CLOCK, treat_as_authority=True)
    with pytest.raises(SignalingValidationError):
        refuse_cast_as_authority(treat_as_authority=True)


def test_record_hash_stable() -> None:
    a = cast_from_fixture({"cast_id": "stable"})
    b = cast_from_fixture({"cast_id": "stable"})
    assert a.record_hash == b.record_hash


def test_schema_rejects_secret() -> None:
    with pytest.raises(SignalingValidationError):
        AttentionCast(
            cast_id="bad",
            caster_id="agent0",
            cast_type="pointer",
            target_ref="dac:target",
            range_class="local",
            hook_text="password=secret",
            bite_risk=0.1,
            evidence_refs=(),
            expires_at="2026-06-13T23:00:00.000000Z",
        )


def test_dac_event_refs_no_authority_fields() -> None:
    refs = planned_dac_event_refs()
    assert len(refs) >= 11
    assert all(not e.get("authority_fields") for e in refs)


def test_unknown_cast_refused() -> None:
    cast = cast_from_fixture({"cast_id": "dac-unk", "cast_type": "unknown"})
    result = evaluate_attention_cast(cast, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "dac.refused.unknown_cast"


def test_target_ref_requires_dac_prefix() -> None:
    with pytest.raises(SignalingValidationError):
        AttentionCast(
            cast_id="bad",
            caster_id="agent0",
            cast_type="pointer",
            target_ref="not-dac",
            range_class="local",
            hook_text="bounded",
            bite_risk=0.1,
            evidence_refs=(),
            expires_at="2026-06-13T23:00:00.000000Z",
        )
