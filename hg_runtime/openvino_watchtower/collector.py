"""OpenVINO Watchtower collector — aggregates events, spans, and probes."""

from __future__ import annotations

import hashlib
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from hg_runtime.openvino_watchtower.agent_zero_probe import (
    KNOWN_ORGANS,
    default_organ_map,
    merge_organ_events,
)
from hg_runtime.openvino_watchtower.events import emit_event, read_recent_events
from hg_runtime.openvino_watchtower.gpu_probe import probe_intel_gpu
from hg_runtime.openvino_watchtower.openvino_probe import probe_openvino_runtime
from hg_runtime.openvino_watchtower.process_probe import probe_process_metrics
from hg_runtime.openvino_watchtower.schema import (
    DeviceStatus,
    InferenceSpan,
    ModelStatus,
    ProviderStatus,
    TelemetryRedactionPolicy,
    new_span_id,
)
from hg_runtime.openvino_watchtower.snapshot import build_snapshot_dict
from hg_runtime.openvino_watchtower.phase2_snapshot import enrich_snapshot_phase2
from hg_runtime.openvino_watchtower.store import WatchtowerStore

WORKSPACE = Path(__file__).resolve().parents[2]


class OpenVINOWatchtowerCollector:
    """In-memory collector with optional persistence."""

    def __init__(self, store: WatchtowerStore | None = None) -> None:
        self.store = store or WatchtowerStore()
        self._lock = threading.Lock()
        self._active: dict[str, InferenceSpan] = {}
        self._recent: list[InferenceSpan] = []
        self._request_count = 0
        self._error_count = 0
        self._latencies: list[float] = []
        self._queue_depths: dict[str, int] = {}
        self._organ_activity = default_organ_map()
        self._receipt_refs: list[str] = []
        self._proof_refs: list[str] = []
        self._last_event_at: str | None = None
        self._last_updated: str | None = None
        self._redaction = TelemetryRedactionPolicy()
        self._provider = ProviderStatus()
        self._model = ModelStatus()
        self._device = DeviceStatus()
        self._openvino_status: dict[str, Any] = {}
        self._started = False

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
        emit_event("WATCHTOWER_STARTED", payload={"collector": "OpenVINOWatchtowerCollector"})
        self.refresh_probes()

    def stop(self) -> None:
        emit_event("WATCHTOWER_STOPPED")
        with self._lock:
            self._started = False

    @staticmethod
    def _hash_text(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def refresh_probes(self, *, allow_network: bool = True) -> None:
        ov = probe_openvino_runtime(allow_network=allow_network)
        proc = probe_process_metrics()
        gpu = probe_intel_gpu()
        with self._lock:
            self._openvino_status = ov
            self._process_metrics = proc
            self._gpu_metrics = gpu
            if ov.get("present"):
                emit_event("OPENVINO_RUNTIME_DETECTED", payload={"runtime_version": ov.get("runtime_version")})
            else:
                emit_event("OPENVINO_RUNTIME_MISSING")
            mode = "live-local"
            if ov.get("fallback_stub"):
                mode = "fixture"
            if not ov.get("reachable"):
                mode = "unavailable" if not ov.get("present") else "dry-run"
            self._provider = ProviderStatus(
                provider_id="openvino_windows",
                mode=mode,
                reachable=bool(ov.get("reachable")),
                healthy=bool(ov.get("healthy") and ov.get("model_loaded")),
                openvino_present=bool(ov.get("present")),
                runtime_version=ov.get("runtime_version"),
                verdict=str(ov.get("verdict", "YELLOW_PROVIDER_UNREACHABLE")),
            )
            self._device = DeviceStatus(
                device=ov.get("resolved_device"),
                resolved_device=ov.get("resolved_device"),
            )
            self._model = ModelStatus(
                model_id=ov.get("model_id"),
                loaded=bool(ov.get("model_loaded")),
            )
            self._organ_activity = merge_organ_events(
                self._organ_activity,
                {"model_provider": {"state": "active" if ov.get("healthy") else "waiting"}},
            )
            self._last_updated = datetime.now(timezone.utc).isoformat()

    def on_model_load_started(self, *, model_id: str, model_path: str | None = None) -> None:
        emit_event("MODEL_LOAD_STARTED", model_id=model_id, payload={"model_path": model_path})
        with self._lock:
            self._model = ModelStatus(model_id=model_id, model_path=model_path, loaded=False)

    def on_model_load_completed(self, *, model_id: str, duration_ms: float, model_hash: str | None = None) -> None:
        emit_event(
            "MODEL_LOAD_COMPLETED",
            model_id=model_id,
            payload={"duration_ms": duration_ms, "model_hash": model_hash},
        )
        with self._lock:
            self._model = ModelStatus(
                model_id=model_id,
                loaded=True,
                load_duration_ms=duration_ms,
                model_hash=model_hash,
                last_load_at=datetime.now(timezone.utc).isoformat(),
            )

    def on_model_load_failed(self, *, model_id: str, error: str) -> None:
        emit_event("MODEL_LOAD_FAILED", model_id=model_id, payload={"error": error})
        with self._lock:
            self._error_count += 1
            self._model.last_error = error

    def on_compile_started(self, *, model_id: str, device: str) -> None:
        emit_event("MODEL_COMPILE_STARTED", model_id=model_id, device=device)

    def on_compile_completed(self, *, model_id: str, device: str, duration_ms: float) -> None:
        emit_event(
            "MODEL_COMPILE_COMPLETED",
            model_id=model_id,
            device=device,
            payload={"duration_ms": duration_ms},
        )
        with self._lock:
            self._device = DeviceStatus(device=device, resolved_device=device, compile_target=device)
            self._model.compile_duration_ms = duration_ms

    def on_compile_failed(self, *, model_id: str, device: str, error: str) -> None:
        emit_event("MODEL_COMPILE_FAILED", model_id=model_id, device=device, payload={"error": error})
        with self._lock:
            self._error_count += 1

    def begin_inference(
        self,
        *,
        request_id: str | None = None,
        organ_id: str | None = None,
        task: str | None = None,
        model_id: str | None = None,
        device: str | None = None,
        action_id: str | None = None,
        prompt_text: str | None = None,
        queue_item_ref: str | None = None,
        authority_chain_ref: str | None = None,
    ) -> InferenceSpan:
        rid = request_id or uuid4().hex
        span = InferenceSpan(
            span_id=new_span_id(),
            request_id=rid,
            organ_id=organ_id,
            task=task,
            action_id=action_id,
            model_id=model_id,
            device=device,
            started_at=datetime.now(timezone.utc).isoformat(),
            queue_item_ref=queue_item_ref,
            authority_chain_ref=authority_chain_ref,
            status="active",
            prompt_hash=self._hash_text(prompt_text) if prompt_text else None,
            prompt_length=len(prompt_text) if prompt_text else None,
        )
        emit_event(
            "INFERENCE_REQUEST_RECEIVED",
            span_id=span.span_id,
            request_id=rid,
            organ_id=organ_id,
            model_id=model_id,
            device=device,
            payload={"task": task, "action_id": action_id},
        )
        emit_event(
            "INFERENCE_STARTED",
            span_id=span.span_id,
            request_id=rid,
            organ_id=organ_id,
            model_id=model_id,
            device=device,
        )
        with self._lock:
            self._active[span.span_id] = span
            self._request_count += 1
            if organ_id:
                self._organ_activity = merge_organ_events(
                    self._organ_activity, {organ_id: {"state": "active", "task": task}}
                )
            self._last_event_at = datetime.now(timezone.utc).isoformat()
        return span

    def on_chunk(self, span_id: str, *, delta: str = "", token_count: int = 0) -> None:
        emit_event(
            "INFERENCE_CHUNK_EMITTED",
            span_id=span_id,
            payload={"delta_length": len(delta), "token_count": token_count},
        )
        with self._lock:
            span = self._active.get(span_id)
            if not span:
                return
            span.chunk_count += 1
            span.token_count += max(token_count, 1 if delta else 0)
            self._last_event_at = datetime.now(timezone.utc).isoformat()

    def complete_inference(
        self,
        span_id: str,
        *,
        output_text: str | None = None,
        receipt_ref: str | None = None,
        proof_ref: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        emit_event("INFERENCE_COMPLETED", span_id=span_id)
        with self._lock:
            span = self._active.pop(span_id, None)
            if not span:
                return
            span.status = "completed"
            span.completed_at = now.isoformat()
            if span.started_at:
                try:
                    t0 = datetime.fromisoformat(span.started_at.replace("Z", "+00:00"))
                    span.duration_ms = round((now - t0).total_seconds() * 1000.0, 2)
                    if span.duration_ms and span.token_count:
                        span.tokens_per_second = round(span.token_count / (span.duration_ms / 1000.0), 2)
                    if span.duration_ms is not None:
                        self._latencies.append(span.duration_ms)
                        self._latencies = self._latencies[-50:]
                except ValueError:
                    pass
            if output_text:
                span.output_hash = self._hash_text(output_text)
                span.output_length = len(output_text)
            span.receipt_ref = receipt_ref
            span.proof_ref = proof_ref
            if receipt_ref:
                self._receipt_refs.append(receipt_ref)
            if proof_ref:
                self._proof_refs.append(proof_ref)
            self._recent.insert(0, span)
            self._recent = self._recent[:50]
            if span.organ_id:
                self._organ_activity = merge_organ_events(
                    self._organ_activity, {span.organ_id: {"state": "idle", "task": None}}
                )
            self._last_event_at = now.isoformat()

    def fail_inference(self, span_id: str, *, error: str) -> None:
        now = datetime.now(timezone.utc)
        emit_event("INFERENCE_FAILED", span_id=span_id, payload={"error": error})
        with self._lock:
            span = self._active.pop(span_id, None)
            if not span:
                return
            span.status = "failed"
            span.error = error
            span.completed_at = now.isoformat()
            self._error_count += 1
            self._recent.insert(0, span)
            self._recent = self._recent[:50]
            if span.organ_id:
                self._organ_activity = merge_organ_events(
                    self._organ_activity, {span.organ_id: {"state": "error", "detail": error}}
                )
            self._last_event_at = now.isoformat()

    def set_queue_depth(self, queue_name: str, depth: int) -> None:
        emit_event("QUEUE_DEPTH_CHANGED", payload={"queue": queue_name, "depth": depth})
        with self._lock:
            self._queue_depths[queue_name] = depth
            self._last_event_at = datetime.now(timezone.utc).isoformat()

    def set_organ_activity(self, organ_id: str, *, state: str, task: str | None = None) -> None:
        if organ_id not in KNOWN_ORGANS:
            organ_id = "model_provider"
        emit_event(
            "ORGAN_ACTIVITY_UPDATED",
            organ_id=organ_id,
            payload={"state": state, "task": task},
        )
        with self._lock:
            self._organ_activity = merge_organ_events(
                self._organ_activity, {organ_id: {"state": state, "task": task}}
            )

    def ingest_event(self, event: dict[str, Any]) -> None:
        self._last_event_at = event.get("ts")

    def build_state(self) -> dict[str, Any]:
        with self._lock:
            rolling = None
            if self._latencies:
                rolling = round(sum(self._latencies) / len(self._latencies), 2)
            return {
                "last_updated": self._last_updated or datetime.now(timezone.utc).isoformat(),
                "last_event_at": self._last_event_at,
                "provider_status": self._provider,
                "openvino_status": self._openvino_status,
                "model_status": self._model,
                "device_status": self._device,
                "active_inference_spans": list(self._active.values()),
                "recent_inference_spans": list(self._recent),
                "organ_activity": self._organ_activity,
                "queue_depths": dict(self._queue_depths),
                "gpu_metrics": getattr(self, "_gpu_metrics", {}),
                "process_metrics": getattr(self, "_process_metrics", {}),
                "error_summary": {
                    "error_count": self._error_count,
                    "last_errors": [s.error for s in self._recent if s.error][:5],
                },
                "receipt_refs": self._receipt_refs[-20:],
                "proof_refs": self._proof_refs[-20:],
                "redaction": self._redaction,
                "request_count": self._request_count,
                "error_count": self._error_count,
                "rolling_latency_ms": rolling,
            }

    def snapshot(self, *, persist: bool = True, allow_network: bool | None = None) -> dict[str, Any]:
        import os

        if allow_network is None:
            allow_network = os.environ.get("HG_OPENVINO_WATCHTOWER_PROBE_NETWORK", "").lower() in {
                "1",
                "true",
                "yes",
            }
        self.refresh_probes(allow_network=allow_network)
        data = build_snapshot_dict(self.build_state())
        data = enrich_snapshot_phase2(data)
        if persist:
            self.store.write_snapshot(data)
        return data

    def replay_events(self, limit: int = 200) -> None:
        for ev in read_recent_events(limit):
            self.ingest_event(ev)


_GLOBAL: OpenVINOWatchtowerCollector | None = None


def get_collector() -> OpenVINOWatchtowerCollector:
    global _GLOBAL
    if _GLOBAL is None:
        _GLOBAL = OpenVINOWatchtowerCollector()
    return _GLOBAL


__all__ = ["OpenVINOWatchtowerCollector", "get_collector"]
