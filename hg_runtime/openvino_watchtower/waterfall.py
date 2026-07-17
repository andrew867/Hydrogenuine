"""Inference span waterfall timings."""

from __future__ import annotations

from typing import Any


def build_waterfall(snapshot: dict[str, Any], events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    model = snapshot.get("model_status") or {}
    spans_out: list[dict[str, Any]] = []

    for span in (snapshot.get("recent_inference_spans") or []) + (snapshot.get("active_inference_spans") or []):
        sid = span.get("span_id")
        phases = {
            "model_load_ms": model.get("load_duration_ms"),
            "compile_ms": model.get("compile_duration_ms"),
            "queue_wait_ms": span.get("queue_wait_ms"),
            "organ_wait_ms": span.get("organ_wait_ms"),
            "first_token_ms": span.get("first_token_ms") or span.get("duration_ms"),
            "total_inference_ms": span.get("duration_ms"),
            "chunks_per_sec": span.get("tokens_per_second"),
        }
        spans_out.append(
            {
                "span_id": sid,
                "organ_id": span.get("organ_id"),
                "task": span.get("task"),
                "status": span.get("status"),
                "phases": phases,
            }
        )

    return {
        "spans": spans_out,
        "failure_count": snapshot.get("error_count", 0),
        "timeout_count": sum(1 for s in spans_out if s.get("status") == "failed"),
        "authority_created": False,
        "permission_granted": False,
    }


__all__ = ["build_waterfall"]
