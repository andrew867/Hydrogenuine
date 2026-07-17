"""AdmissionController — singleton locks, idempotency, preemption (CT-06 ADM)."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any

from hg_core.admission import events
from hg_core.admission.idempotency import IdempotencyStore
from hg_core.admission.preemption import arriving_fate
from hg_core.time.clock import get_clock
from hg_core.time.expiry import validate_approval_window
from hg_core.admission.types import (
    AdmissionDecision,
    AdmissionRequest,
    AdmissionToken,
    DrainReceipt,
    PreemptionReceipt,
)


@dataclass
class _ActiveLock:
    lock_key: str
    request_id: str
    kind: str
    lease_until: float
    idempotency_key: str


@dataclass
class _QueuedRequest:
    request: AdmissionRequest
    enqueued_at: float


class AdmissionController:
    """UEAK ingress admission — every mutating request acquires admission before execution."""

    def __init__(
        self,
        *,
        queue_capacity: int = 64,
        idempotency_retention_s: float = 3600.0,
        default_lease_s: float = 300.0,
        clock: Any | None = None,
    ) -> None:
        self._queue_capacity = queue_capacity
        self._default_lease_s = default_lease_s
        self._clock = clock or time.monotonic
        self._idempotency = IdempotencyStore(retention_s=idempotency_retention_s)
        self._mutex = threading.Lock()
        self._locks: dict[str, _ActiveLock] = {}
        self._capability_counts: dict[str, int] = {}
        self._ter_sandbox_holders: dict[str, str] = {}
        self._queue: list[_QueuedRequest] = []
        self._panic_active = False
        self._crr_recovery_active = False
        self._event_log: list[dict[str, Any]] = []

    @property
    def events(self) -> list[dict[str, Any]]:
        return list(self._event_log)

    def _now(self) -> float:
        return float(self._clock())

    def _lock_key(self, req: AdmissionRequest) -> str:
        if req.kind in {"srp_apply", "max_auto_run", "mel_cycle"}:
            return req.kind
        if req.kind == "oea_effect" and req.capability_id:
            return f"oea:{req.capability_id}"
        if req.kind == "ter_command" and req.sandbox_id:
            return f"ter:{req.sandbox_id}"
        if req.kind == "crr_recovery":
            return "crr_recovery"
        return f"{req.kind}:{req.request_id}"

    def _current_holder_kind(self, lock_key: str) -> str | None:
        active = self._locks.get(lock_key)
        return active.kind if active else None

    def _reclaim_expired(self, now: float) -> list[dict[str, Any]]:
        reclaimed: list[dict[str, Any]] = []
        for key, active in list(self._locks.items()):
            if now > active.lease_until:
                self._release_lock(key, active, reason="admission.refused.lock_lease_expired")
                reclaimed.append(
                    {
                        "lock_key": key,
                        "request_id": active.request_id,
                        "reason_code": "admission.refused.lock_lease_expired",
                    }
                )
        return reclaimed

    def _release_lock(self, lock_key: str, active: _ActiveLock, *, reason: str) -> None:
        del self._locks[lock_key]
        if lock_key.startswith("oea:"):
            cap = lock_key.split(":", 1)[1]
            self._capability_counts[cap] = max(0, self._capability_counts.get(cap, 1) - 1)
        if lock_key.startswith("ter:"):
            sandbox = lock_key.split(":", 1)[1]
            self._ter_sandbox_holders.pop(sandbox, None)
        evt = events.lock_released(
            {"lock_key": lock_key, "request_id": active.request_id, "reason_code": reason},
        )
        self._event_log.append(evt)

    def _refuse(
        self,
        req: AdmissionRequest,
        reason_code: str,
        *,
        duplicate_of: str | None = None,
        extra_events: list[dict[str, Any]] | None = None,
    ) -> AdmissionDecision:
        evts = [
            events.admission_requested(req.to_payload()),
            events.admission_refused(
                {
                    "request_id": req.request_id,
                    "kind": req.kind,
                    "reason_code": reason_code,
                    "idempotency_key": req.idempotency_key,
                    "duplicate_of": duplicate_of,
                }
            ),
        ]
        if extra_events:
            evts.extend(extra_events)
        self._event_log.extend(evts)
        return AdmissionDecision(
            admitted=False,
            verdict="refused",
            reason_code=reason_code,
            duplicate_of=duplicate_of,
            events=tuple(evts),
        )

    def _validate_approval(self, req: AdmissionRequest) -> str | None:
        binding = req.approval_binding
        if binding is None:
            return None
        if not binding.proposal_hash or binding.proposal_hash == "unknown":
            return "admission.refused.stale_approval"
        if binding.registry_hash == "stale":
            return "admission.refused.stale_approval"
        if binding.expires_at == "expired":
            return "admission.refused.stale_approval"
        if binding.expires_at:
            ok, reason = validate_approval_window(binding.expires_at, get_clock().now_utc())
            if not ok:
                return reason
        return None

    def request(self, req: AdmissionRequest) -> AdmissionDecision:
        now = self._now()
        with self._mutex:
            self._reclaim_expired(now)

            dup = self._idempotency.lookup(req.idempotency_key, now=now)
            if dup is not None and dup.request_id != req.request_id:
                hit = events.idempotency_hit(
                    {
                        "idempotency_key": req.idempotency_key,
                        "original_request_id": dup.request_id,
                        "result_ref": dup.result_ref,
                    }
                )
                return self._refuse(
                    req,
                    "admission.refused.duplicate_request",
                    duplicate_of=dup.request_id,
                    extra_events=[hit],
                )

            stale = self._validate_approval(req)
            if stale:
                return self._refuse(req, stale)

            if self._panic_active and req.kind != "panic":
                return self._refuse(req, "admission.refused.panic_active")

            lock_key = self._lock_key(req)
            holder = self._current_holder_kind(lock_key)
            fate = arriving_fate(holder=holder, arriving=req.kind, panic_active=self._panic_active)
            if self._crr_recovery_active and req.kind == "mel_cycle":
                fate = "preempt"
            if fate == "refuse":
                if req.kind == "srp_apply" and lock_key in self._locks:
                    return self._refuse(req, "admission.refused.singleton_held")
                if req.kind == "max_auto_run" and lock_key in self._locks:
                    return self._refuse(req, "admission.refused.singleton_held")
                return self._refuse(req, "admission.refused.preempted")

            if req.kind == "oea_effect" and req.capability_id:
                cap = req.capability_id
                current = self._capability_counts.get(cap, 0)
                if current >= max(1, req.capability_concurrency):
                    if len(self._queue) >= self._queue_capacity:
                        return self._refuse(req, "admission.refused.queue_overflow")
                    self._queue.append(_QueuedRequest(req, now))
                    return AdmissionDecision(
                        admitted=False,
                        verdict="queued",
                        reason_code="admission.queued.capacity",
                        events=tuple([events.admission_requested(req.__dict__)]),
                    )

            if req.kind == "ter_command" and req.sandbox_id:
                if req.sandbox_id in self._ter_sandbox_holders:
                    return self._refuse(req, "admission.refused.singleton_held")

            if lock_key in self._locks and req.kind in {"srp_apply", "max_auto_run", "mel_cycle"}:
                return self._refuse(req, "admission.refused.singleton_held")

            lease_until = now + self._default_lease_s
            active = _ActiveLock(
                lock_key=lock_key,
                request_id=req.request_id,
                kind=req.kind,
                lease_until=lease_until,
                idempotency_key=req.idempotency_key,
            )
            self._locks[lock_key] = active
            if req.kind == "oea_effect" and req.capability_id:
                self._capability_counts[req.capability_id] = self._capability_counts.get(req.capability_id, 0) + 1
            if req.kind == "ter_command" and req.sandbox_id:
                self._ter_sandbox_holders[req.sandbox_id] = req.request_id

            token = AdmissionToken(
                request_id=req.request_id,
                kind=req.kind,
                lock_key=lock_key,
                idempotency_key=req.idempotency_key,
                lease_until=lease_until,
            )
            granted_payload = {
                "request_id": req.request_id,
                "kind": req.kind,
                "lock_key": lock_key,
                "idempotency_key": req.idempotency_key,
            }
            evts = [
                events.admission_requested(req.to_payload()),
                events.admission_granted(granted_payload),
                events.lock_acquired(granted_payload),
            ]
            self._event_log.extend(evts)
            return AdmissionDecision(
                admitted=True,
                verdict="admitted",
                reason_code="ok",
                token=token,
                events=tuple(evts),
            )

    def complete(self, token: AdmissionToken, *, result_ref: str) -> None:
        with self._mutex:
            self._idempotency.record(token.idempotency_key, token.request_id, result_ref, now=self._now())
            active = self._locks.get(token.lock_key)
            if active and active.request_id == token.request_id:
                self._release_lock(token.lock_key, active, reason="ok")

    def release(self, token: AdmissionToken | None) -> None:
        if token is None:
            return
        with self._mutex:
            active = self._locks.get(token.lock_key)
            if active and active.request_id == token.request_id:
                self._release_lock(token.lock_key, active, reason="released")

    def assert_panic(self, *, preemptor: str = "plt:panic") -> list[PreemptionReceipt]:
        receipts: list[PreemptionReceipt] = []
        with self._mutex:
            self._panic_active = True
            self._event_log.append(events.panic_asserted({"preemptor": preemptor}))
            for key, active in list(self._locks.items()):
                if active.kind == "panic":
                    continue
                receipt = PreemptionReceipt(
                    preemptor=preemptor,
                    preempted_request_id=active.request_id,
                    preempted_kind=active.kind,  # type: ignore[arg-type]
                )
                receipts.append(receipt)
                self._event_log.append(events.preemption_receipted(receipt.to_payload()))
                self._release_lock(key, active, reason="admission.preempted.operator_cancelled")
        return receipts

    def begin_crr_recovery(self, *, recovery_id: str | None = None) -> AdmissionToken | None:
        req = AdmissionRequest(
            request_id=recovery_id or f"crr_{uuid.uuid4().hex[:8]}",
            kind="crr_recovery",
            idempotency_key=f"crr:{recovery_id or 'active'}",
        )
        decision = self.request(req)
        if decision.admitted:
            self._crr_recovery_active = True
            return decision.token
        return None

    def end_crr_recovery(self) -> None:
        with self._mutex:
            self._crr_recovery_active = False
            active = self._locks.get("crr_recovery")
            if active:
                self._release_lock("crr_recovery", active, reason="crr_complete")

    def drain_queues(self) -> DrainReceipt:
        with self._mutex:
            drained = len(self._queue)
            receipt_id = f"drain_{uuid.uuid4().hex[:12]}"
            self._queue.clear()
            payload = {"drained": drained, "checkpointed": drained, "receipt_id": receipt_id}
            self._event_log.append(events.queue_drained(payload))
            return DrainReceipt(drained=drained, checkpointed=drained, receipt_id=receipt_id)

    def lock_state(self) -> dict[str, Any]:
        with self._mutex:
            return {
                "active_locks": {k: v.request_id for k, v in self._locks.items()},
                "panic_active": self._panic_active,
                "crr_recovery_active": self._crr_recovery_active,
                "queue_depth": len(self._queue),
                "capability_counts": dict(self._capability_counts),
            }


__all__ = ["AdmissionController"]
