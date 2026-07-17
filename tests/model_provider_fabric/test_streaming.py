"""Streaming token bus tests."""

from __future__ import annotations

from hg_runtime.model_provider_fabric.streaming import emit_non_streaming_as_events


def test_non_streaming_emits_started_delta_completed() -> None:
    events = emit_non_streaming_as_events(
        provider_id="cpu-fallback-stub",
        model_id="stub",
        role="ORGAN_BACKGROUND",
        organ_id="organ:AIS",
        request_id="req:1",
        full_text="hello",
    )
    kinds = [e.event_kind for e in events]
    assert kinds == ["MODEL_RESPONSE_STARTED", "MODEL_RESPONSE_DELTA", "MODEL_RESPONSE_COMPLETED"]
    assert all(e.to_payload()["permission_granted"] is False for e in events)
