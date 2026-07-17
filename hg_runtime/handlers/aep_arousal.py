"""RTC arousal stage — Phase 1 AEP processor (restrict-only, no authority)."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from typing import TYPE_CHECKING

from hg_runtime.contract import Event

if TYPE_CHECKING:
    from hg_aep.types import AEPSignal

_AEP_HISTORY_TYPES = frozenset(
    {
        "AEP_SIGNAL_EMITTED",
        "AEP_SIGNAL_RECORDED",
        "AEP_AROUSAL_STATE_UPDATED",
        "AEP_MODULATION_RECORDED",
    }
)


def _signal_from_emitted(event: Mapping[str, Any]) -> "AEPSignal":
    from hg_aep.types import AEPSignal
    payload = event.get("payload", {})
    if not isinstance(payload, Mapping):
        payload = {}
    signal_id = str(payload.get("signal_id") or event["event_id"])
    signal_class = str(payload.get("class") or payload.get("signal_class") or "UNKNOWN")
    source = payload.get("source", {})
    if not isinstance(source, Mapping):
        source = {"component": "unknown", "ref": signal_id}
    parents = payload.get("causal_parents", ())
    if not isinstance(parents, (list, tuple)):
        parents = ()
    return AEPSignal(
        signal_id=signal_id,
        signal_class=signal_class,
        severity=int(payload.get("severity", 0)),
        scope=str(payload.get("scope", "global")),
        source=dict(source),
        evidence_refs=tuple(payload.get("evidence_refs", ())),
        emitted_at=str(payload.get("emitted_at") or event.get("created_at") or ""),
        ttl_s=payload.get("ttl_s"),
        decay_half_life_s=payload.get("decay_half_life_s"),
        causal_parents=(str(event["event_id"]), *tuple(str(p) for p in parents)),
    )


class Phase1AEPArousalHandler:
    """Process AEP_SIGNAL_EMITTED into recorded/arousal/modulation drafts on tick."""

    handler_id = "rtc.aep.phase1_arousal"

    def process_tick(
        self,
        events: Sequence[Event],
        view: Mapping[str, Any],
        prior_events: Sequence[Mapping[str, Any]],
    ) -> tuple[list[dict[str, Any]], Mapping[str, Any]]:
        del view
        recorded_ids = {
            str(event.get("payload", {}).get("signal_id"))
            for event in prior_events
            if event.get("type") == "AEP_SIGNAL_RECORDED"
        }
        drafts: list[dict[str, Any]] = []
        clock = ""
        seen_emit_ids: set[str] = set()
        pending_emits: list[Mapping[str, Any]] = []
        for event in (*prior_events, *events):
            if event.get("type") != "AEP_SIGNAL_EMITTED":
                continue
            emit_id = str(event.get("event_id", ""))
            if emit_id in seen_emit_ids:
                continue
            seen_emit_ids.add(emit_id)
            signal_id = str(event.get("payload", {}).get("signal_id") or emit_id)
            if signal_id in recorded_ids:
                continue
            pending_emits.append(event)

        from hg_aep.processor import process_signal_drafts
        from hg_aep.replay import reconstruct_arousal_state

        for event in pending_emits:
            signal = _signal_from_emitted(event)
            clock = str(event.get("created_at") or signal.emitted_at or clock)
            drafts.extend(
                process_signal_drafts(
                    signal,
                    prior_events=[*prior_events, *events],
                    scope=signal.scope,
                    computed_at=clock,
                    parent_event_id=str(event["event_id"]),
                )
            )
            recorded_ids.add(signal.signal_id)

        history = [event for event in (*prior_events, *events) if event.get("type") in _AEP_HISTORY_TYPES]
        if not clock and history:
            clock = str(history[-1].get("created_at") or "")
        if not clock:
            clock = "1970-01-01T00:00:00.000000Z"
        arousal = reconstruct_arousal_state(history, scope="global", computed_at=clock)
        state = {
            "max_severity": int(arousal.get("max_severity", 0)),
            "dimensions": dict(arousal.get("levels", {})),
            "scope": arousal.get("scope", "global"),
        }
        return drafts, state

    def read(
        self, events: Sequence[Event], view: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        from hg_aep.replay import reconstruct_arousal_state, signals_from_rtc_events

        env = view.get("environment", {})
        if isinstance(env, Mapping):
            arousal = env.get("arousal")
            if isinstance(arousal, Mapping) and arousal:
                return arousal
        signals = signals_from_rtc_events(events)
        if not signals:
            return {"max_severity": 0, "dimensions": {}}
        arousal = reconstruct_arousal_state(
            events,
            scope="global",
            computed_at=str(events[-1].get("created_at") or signals[-1].emitted_at),
        )
        return {
            "max_severity": int(arousal.get("max_severity", 0)),
            "dimensions": dict(arousal.get("levels", {})),
        }


__all__ = ["Phase1AEPArousalHandler"]
