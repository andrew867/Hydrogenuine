"""Evidence sources for status synthesis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]


@dataclass
class StatusSource:
    source_id: str
    label: str
    verdict: str
    stale: bool
    missing: bool
    ref: str | None = None
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "label": self.label,
            "verdict": self.verdict,
            "stale": self.stale,
            "missing": self.missing,
            "ref": self.ref,
            "detail": self.detail,
        }


def _load_exciton_snapshot() -> dict[str, Any] | None:
    try:
        from hg_runtime.exciton.status_aggregator import AggregatorConfig, build_snapshot

        return build_snapshot(AggregatorConfig(offline_fixture=True)).to_payload()
    except Exception:
        return None


def _load_watchtower_snapshot() -> dict[str, Any] | None:
    try:
        from hg_runtime.openvino_watchtower.exciton_panel import load_watchtower_snapshot

        return load_watchtower_snapshot(prefer_api=False)
    except Exception:
        return None


def _load_operator_queue_summary() -> dict[str, Any] | None:
    try:
        from hg_runtime.operator_action_queue.queue import open_default_queue

        q = open_default_queue(WORKSPACE)
        pending = len(q.list_items())
        return {"pending_count": pending}
    except Exception:
        return None


def gather_status_sources() -> list[StatusSource]:
    sources: list[StatusSource] = []

    exciton = _load_exciton_snapshot()
    if exciton:
        verdict = exciton.get("overall_verdict", "UNKNOWN")
        stale = str(verdict).startswith("YELLOW") or "STALE" in str(verdict).upper()
        sources.append(
            StatusSource("exciton", "EXCITON snapshot", verdict, stale=stale, missing=False, ref="exciton/status")
        )
    else:
        sources.append(StatusSource("exciton", "EXCITON snapshot", "missing", stale=False, missing=True))

    wt = _load_watchtower_snapshot()
    if wt:
        fresh = wt.get("freshness_verdict", "contact_lost")
        stale = fresh not in ("fresh", "GREEN", "warning")
        sources.append(
            StatusSource("watchtower", "Inference Watchtower", str(fresh), stale=stale, missing=False, ref="openvino_watchtower")
        )
    else:
        sources.append(StatusSource("watchtower", "Inference Watchtower", "missing", stale=False, missing=True))

    oq = _load_operator_queue_summary()
    if oq:
        pending = oq.get("pending_count", oq.get("queued", 0))
        sources.append(
            StatusSource(
                "operator_queue",
                "Operator Queue",
                f"pending={pending}",
                stale=False,
                missing=False,
                ref="operator_action_queue",
            )
        )
    else:
        sources.append(StatusSource("operator_queue", "Operator Queue", "missing", stale=False, missing=True))

    return sources


__all__ = ["StatusSource", "gather_status_sources"]
