"""RTC Phase 1 memory handler — bounded retrieve/store, no authority."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Mapping, Sequence

from hg_runtime.contract import Event, draft, stable_id
from hg_runtime.memory.store import (
    append_tick_summary,
    load_session_context,
    memory_enabled,
    retrieve_summaries,
)
from hg_runtime.memory.types import (
    MemoryReference,
    MemoryRetrieveRequest,
    MemoryRetrieveResult,
    MemoryStoreRequest,
    MemoryStoreResult,
    redact_mapping,
)


def _session_id_from_events(events: Sequence[Event]) -> str | None:
    for event in events:
        if event.get("type") != "CHAT_MESSAGE":
            continue
        payload = event.get("payload", {})
        if isinstance(payload, Mapping):
            session = payload.get("session_id")
            if session:
                return str(session)
    return None


def _bounded_view_context(view: Mapping[str, Any]) -> dict[str, Any]:
    activity = view.get("activity", {})
    if not isinstance(activity, Mapping):
        return {}
    return redact_mapping(
        {
            "recent_ingress": list(activity.get("recent_ingress", []))[-8:],
            "recent_memory_retrievals": list(activity.get("recent_memory_retrievals", []))[-4:],
            "recent_receipts": list(activity.get("recent_receipts", []))[-4:],
            "ticks": view.get("self", {}).get("ticks", 0),
        }
    )


class Phase1MemoryHandler:
    """Real bounded RTC memory — file index + optional session_manager read."""

    handler_id = "rtc.memory.phase1"

    def __init__(self, *, runtime_dir: Path, max_tokens: int = 1500) -> None:
        self._runtime_dir = Path(runtime_dir)
        self._max_tokens = max_tokens

    def retrieve(
        self, view: Mapping[str, Any], events: Sequence[Event]
    ) -> Mapping[str, Any]:
        event_refs = tuple(event["event_id"] for event in events)
        session_id = _session_id_from_events(events)
        runtime_id = str(self._runtime_dir.name)
        request = MemoryRetrieveRequest(
            runtime_id=runtime_id,
            session_id=session_id,
            event_refs=event_refs,
            max_tokens=self._max_tokens,
        )
        parents = list(event_refs)
        drafts: List[dict[str, Any]] = [
            draft(
                "MEMORY_RETRIEVE_REQUESTED",
                request.to_payload(),
                causal_parents=parents,
            )
        ]

        if not memory_enabled():
            result = MemoryRetrieveResult(
                status="noop",
                context={"mode": "memory_disabled"},
                provenance={"query": "memory_disabled", "result_refs": []},
                reason_code="memory_disabled",
            )
            drafts.extend(_retrieve_completion_drafts(result, parents))
            return {"context": result.context, "provenance": result.provenance, "drafts": drafts}

        try:
            summaries = retrieve_summaries(self._runtime_dir)
            context: dict[str, Any] = {
                "rtc_summaries": summaries,
                "recent_event_refs": list(event_refs[-16:]),
                "view": _bounded_view_context(view),
            }
            provenance: dict[str, Any] = {
                "query": "rtc_memory_index",
                "result_refs": [row.get("memory_ref") for row in summaries if row.get("memory_ref")],
                "store": str(self._runtime_dir / "rtc_memory_index.json"),
            }
            if session_id:
                session_ctx = load_session_context(session_id, max_tokens=self._max_tokens)
                if session_ctx:
                    context["session_memory"] = session_ctx
                    provenance["session_id"] = session_id
                    provenance["session_source"] = "hg_core.session_manager.load_compacted_memory"
            result = MemoryRetrieveResult(
                status="ok",
                context=context,
                provenance=provenance,
            )
            drafts.extend(_retrieve_completion_drafts(result, parents))
            return {"context": result.context, "provenance": result.provenance, "drafts": drafts}
        except OSError as exc:
            result = MemoryRetrieveResult(
                status="failed",
                context={},
                provenance={"query": "rtc_memory_index", "result_refs": []},
                reason_code="retrieve_io_error",
            )
            drafts.append(
                draft(
                    "MEMORY_RETRIEVE_FAILED",
                    {**result.to_payload(), "error": str(exc)},
                    causal_parents=parents,
                )
            )
            return {"context": {}, "provenance": result.provenance, "drafts": drafts}

    def store(
        self,
        events: Sequence[Event],
        proposals: Sequence[Event],
        results: Sequence[Event],
    ) -> List[dict[str, Any]]:
        event_refs = tuple(event["event_id"] for event in events)
        proposal_refs = tuple(proposal["event_id"] for proposal in proposals)
        result_refs = tuple(result["event_id"] for result in results)
        session_id = _session_id_from_events(events)
        runtime_id = str(self._runtime_dir.name)
        request = MemoryStoreRequest(
            runtime_id=runtime_id,
            session_id=session_id,
            event_refs=event_refs,
            proposal_refs=proposal_refs,
            result_refs=result_refs,
        )
        parents = list(event_refs + proposal_refs + result_refs)[:64]
        drafts: List[dict[str, Any]] = [
            draft(
                "MEMORY_STORE_REQUESTED",
                request.to_payload(),
                causal_parents=parents,
            )
        ]

        if not memory_enabled():
            result = MemoryStoreResult(status="noop", reference=None, reason_code="memory_disabled")
            drafts.extend(_store_completion_drafts(result, parents))
            return drafts

        try:
            summary = _tick_summary(events, proposals, results)
            memory_ref = append_tick_summary(
                self._runtime_dir,
                summary=summary,
                event_refs=parents,
            )
            reference = MemoryReference(
                memory_ref=memory_ref,
                store="rtc_memory_index",
                event_refs=parents,
            )
            result = MemoryStoreResult(status="ok", reference=reference)
            drafts.extend(_store_completion_drafts(result, parents))
            return drafts
        except OSError as exc:
            result = MemoryStoreResult(status="failed", reference=None, reason_code="store_io_error")
            drafts.append(
                draft(
                    "MEMORY_STORE_FAILED",
                    {**result.to_payload(), "error": str(exc)},
                    causal_parents=parents,
                )
            )
            drafts.append(
                draft(
                    "MEMORY_WRITE_FAILED",
                    {"event_refs": list(parents), "reason": result.reason_code},
                    causal_parents=parents,
                )
            )
            return drafts


def _tick_summary(
    events: Sequence[Event],
    proposals: Sequence[Event],
    results: Sequence[Event],
) -> dict[str, Any]:
    return redact_mapping(
        {
            "ingress_types": [event["type"] for event in events[:8]],
            "proposal_ids": [
                event.get("payload", {}).get("proposal_id")
                for event in proposals
                if isinstance(event.get("payload"), Mapping)
            ][:8],
            "result_types": [event["type"] for event in results[:8]],
            "receipt_refs": [
                event.get("payload", {}).get("receipt_ref")
                for event in results
                if event.get("type") == "EFFECT_RECEIPTED"
            ][:4],
        }
    )


def _retrieve_completion_drafts(
    result: MemoryRetrieveResult, parents: list[str]
) -> List[dict[str, Any]]:
    payload = result.to_payload()
    if result.status == "failed":
        return [
            draft("MEMORY_RETRIEVE_FAILED", payload, causal_parents=parents),
        ]
    completed = draft("MEMORY_RETRIEVE_COMPLETED", payload, causal_parents=parents)
    legacy = draft(
        "MEMORY_RETRIEVED",
        {
            "provenance": result.provenance,
            "event_refs": parents,
            "status": result.status,
        },
        causal_parents=parents,
    )
    return [completed, legacy]


def _store_completion_drafts(
    result: MemoryStoreResult, parents: list[str]
) -> List[dict[str, Any]]:
    payload = result.to_payload()
    if result.status == "failed":
        return [
            draft("MEMORY_STORE_FAILED", payload, causal_parents=parents),
            draft("MEMORY_WRITE_FAILED", {"event_refs": parents, "reason": result.reason_code}, causal_parents=parents),
        ]
    if result.status == "noop":
        return [draft("MEMORY_STORE_COMPLETED", payload, causal_parents=parents)]
    assert result.reference is not None
    completed = draft("MEMORY_STORE_COMPLETED", payload, causal_parents=parents)
    legacy = draft(
        "MEMORY_WRITTEN",
        {
            **result.reference.to_payload(),
            "status": result.status,
        },
        causal_parents=parents,
    )
    return [completed, legacy]


__all__ = ["Phase1MemoryHandler"]
