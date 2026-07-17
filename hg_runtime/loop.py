"""
RTC runtime loop — Agent #0 (RTC_RUNTIME_LOOP_SPEC.md).

Tick order is law:

    0  PANIC check (short-circuits everything)
    1  bus.poll (blocks when idle; no tick on silence)
    2  world_state.apply(events)
    3  arousal read (modulation only)
    4  CRR cycle check (may consume the whole iteration)
    4a YSR yawn check (soft posture reset; never consumes iteration)
    4b MSC meditation check (quiet observation; never consumes iteration)
    5  memory retrieve (provenance recorded)
    6  cognition propose (conditional — only if the batch warrants it)
    7  decision pipeline (SOAR/HAL/GPP)
    8  kernel execute (sole gate; OEA dispatch happens INSIDE the kernel)
    9  (no loop-level OEA call exists — INV-A28)
    10 memory store (evented write-back)
    11 TICK_COMPLETED (state hash + full refs)

The loop holds no OEA handle. Bus write failure is the one fatal: the spine
must not lie. Everything else degrades into recorded events.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from hg_runtime import world_state as ws
from hg_runtime.bus import BusError, BusWriteError, EventBus
from hg_runtime.cognition.streaming import COGNITION_DECISION_PROPOSAL_TYPES
from hg_runtime.contract import ContractViolation, readonly_view, validate_drafts

RUNTIME_VERSION = "rtc-0.1.0"
DEFAULT_IDLE_BLOCK_S = 5.0
DEFAULT_TICK_BUDGET_S = 60.0
DEFAULT_SNAPSHOT_EVERY_TICKS = 50
POISON_QUARANTINE_AFTER = 3

STAGES = [
    "panic_check",
    "poll",
    "world_state",
    "arousal",
    "recovery_check",
    "yawn_check",
    "meditation_check",
    "memory_retrieve",
    "cognition",
    "decision",
    "execute",
    "memory_store",
    "tick_record",
]


def _jsonable(value: Any) -> Any:
    """Convert immutable views/tuples back to JSON-compatible containers."""
    if isinstance(value, Mapping):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def rtc_enabled() -> bool:
    """HG_RTC_ENABLED=0 (default): no loop; legacy cron/DAG untouched."""
    return os.environ.get("HG_RTC_ENABLED", "0").strip() == "1"


class RuntimeDisabled(Exception):
    pass


class PanicFlag:
    """
    File-based emergency flag — persistent across restart by design (DEP:
    PANIC survives reboot). Real-in-shape stub for Phase 0; the operator
    surface for set/clear lands with PLT.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def active(self) -> bool:
        return self.path.exists()

    def enter(self, reason: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"reason": reason}), encoding="utf-8")
        os.replace(tmp, self.path)

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()


class RuntimeLoop:
    """
    One loop, one tick at a time. Handlers are injected against the contracts
    in hg_runtime.contract; Phase 0 wires the stubs from
    hg_runtime.handlers.stubs, later phases swap in real subsystems without
    touching this file.
    """

    def __init__(
        self,
        bus: EventBus,
        *,
        cognition,
        decision,
        kernel,
        memory,
        arousal,
        recovery,
        yawn=None,
        meditation=None,
        runtime_dir: Path,
        governance_trace=None,
        idle_block_s: float = DEFAULT_IDLE_BLOCK_S,
        tick_budget_s: float = DEFAULT_TICK_BUDGET_S,
        snapshot_every_ticks: int = DEFAULT_SNAPSHOT_EVERY_TICKS,
        monotonic: Callable[[], float] = time.monotonic,
        stage_hook: Optional[Callable[[str], None]] = None,
        require_enabled: bool = True,
        phase1_lifecycle: bool = False,
        panic: Optional[PanicFlag] = None,
    ) -> None:
        if require_enabled and not rtc_enabled():
            raise RuntimeDisabled("HG_RTC_ENABLED != 1 — RTC loop refuses to start")
        self.bus = bus
        self.cognition = cognition
        self.decision = decision
        self.kernel = kernel
        self.memory = memory
        self.arousal = arousal
        self.recovery = recovery
        if yawn is None:
            from hg_runtime.yawn.handler import StubYSRHandler

            yawn = StubYSRHandler()
        self.yawn = yawn
        if meditation is None:
            from hg_runtime.msc.handler import StubMSCHandler

            meditation = StubMSCHandler()
        self.meditation = meditation
        self.governance_trace = governance_trace
        self.runtime_dir = Path(runtime_dir)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.phase1_lifecycle = phase1_lifecycle
        self.panic = panic if panic is not None else PanicFlag(self.runtime_dir / "PANIC")
        self.snapshot_dir = self.runtime_dir / "snapshots"
        self.status_path = self.runtime_dir / "status.json"
        self.idle_block_s = idle_block_s
        self.tick_budget_s = tick_budget_s
        self.snapshot_every_ticks = snapshot_every_ticks
        self._monotonic = monotonic
        self._stage_hook = stage_hook
        self._panic_announced = False
        self._stop_requested_emitted = False
        self._stopped_emitted = False
        self._poison_counts: Dict[str, int] = {}  # event_id -> consecutive failures
        self._retry_batch: List[Mapping[str, Any]] = []
        self.state = ws.initial_state()
        self.alive = False
        self._started = False

    # -- plumbing -------------------------------------------------------------

    def _stage(self, name: str) -> None:
        if self._stage_hook is not None:
            self._stage_hook(name)
        self._write_status(name)

    def _write_status(self, stage: str) -> None:
        record = {
            "stage": stage,
            "ticks": self.state["self"]["ticks"],
            "last_seq": self.state["meta"]["last_seq"],
            "panic": self.panic.active(),
            "pid": os.getpid(),
        }
        tmp = self.status_path.with_suffix(".json.tmp")
        try:
            tmp.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
            os.replace(tmp, self.status_path)
        except OSError:
            pass  # status is observability, never load-bearing

    def _emit(self, type: str, payload: Dict[str, Any], source: str = "loop",
              causal_parents: Sequence[str] = (), severity: Optional[int] = None) -> Mapping[str, Any]:
        """Emit AND fold into world state — keeps live state == replay reduction."""
        event = self.bus.emit(type, payload, source, causal_parents, severity)
        self.state = ws.apply(self.state, event)
        return event

    def _emit_drafts(self, drafts: List[Dict[str, Any]], handler_id: str) -> List[Mapping[str, Any]]:
        out = []
        for d in drafts:
            event = self.bus.emit_draft(d, source=f"handler:{handler_id}")
            self.state = ws.apply(self.state, event)
            out.append(event)
        return out

    def _run_handler(
        self,
        handler_id: str,
        events: Sequence[Mapping[str, Any]],
        fn: Callable[[], Any],
    ):
        """
        Poison-event containment: a handler exception becomes HANDLER_FAILED;
        the triggering events are retried next tick until the quarantine
        threshold, then parked. The loop never dies on one bad event.
        """
        try:
            return fn(), True
        except BusWriteError:
            raise  # the one fatal — never contained
        except Exception as exc:  # noqa: BLE001 — containment is the contract
            error = f"{exc.__class__.__name__}: {exc}"
            refs = [e["event_id"] for e in events]
            self._emit("HANDLER_FAILED", {"handler_id": handler_id, "error": error[:2000],
                                          "event_refs": refs})
            for e in events:
                eid = e["event_id"]
                count = self._poison_counts.get(eid, 0) + 1
                self._poison_counts[eid] = count
                if count >= POISON_QUARANTINE_AFTER:
                    self.bus.quarantine(dict(e), handler_id, error)
                elif e["type"] in ("CHAT_MESSAGE", "API_REQUEST", "WEBHOOK_IN",
                                   "TIMER_EVENT", "FILE_WATCH"):
                    self._retry_batch.append(e)
            return None, False

    # -- lifecycle ------------------------------------------------------------

    def start(self) -> None:
        if self._started:
            return
        self._emit("RUNTIME_STARTED", {
            "runtime_version": RUNTIME_VERSION,
            "registry_hash": self.bus.registry.registry_hash,
            "registry_version": self.bus.registry.version,
        })
        self._started = True
        self.alive = True

    def stop(self, reason: str = "requested") -> None:
        if not self._started:
            return
        if self.alive:
            if self.phase1_lifecycle and not self._stop_requested_emitted:
                self._emit("RUNTIME_STOP_REQUESTED", {"reason": reason})
                self._stop_requested_emitted = True
            self._emit("RUNTIME_STOPPING", {"reason": reason})
        self.alive = False
        ws.write_snapshot(self.state, self.snapshot_dir)
        if self.phase1_lifecycle and not self._stopped_emitted:
            self._emit("RUNTIME_STOPPED", {"reason": reason})
            self._stopped_emitted = True
        self._write_status("stopped")

    # -- the tick ---------------------------------------------------------------

    def run_once(self, poll_timeout: Optional[float] = None) -> str:
        """
        One loop iteration. Returns one of:
        "panic" | "idle" | "recovery" | "tick" — for tests and the supervisor.
        """
        if not self._started:
            self.start()
        tick_t0 = self._monotonic()

        # 0 — PANIC before everything (INV-A3/A5)
        self._stage("panic_check")
        if self.panic.active():
            if self.phase1_lifecycle:
                self._emit(
                    "RUNTIME_PANIC_BLOCKED",
                    {"flag": str(self.panic.path), "stage": "panic_check"},
                )
            if not self._panic_announced:
                self.kernel.block_all()
                self.recovery.enter_safe_state()
                self.cognition.halt()
                self._emit("PANIC_ENTERED", {"flag": str(self.panic.path)})
                self._panic_announced = True
            return "panic"
        if self._panic_announced:
            self.kernel.unblock()
            self._emit("PANIC_CLEARED", {})
            self._panic_announced = False

        # 1 — poll (blocks when idle; no tick on silence)
        self._stage("poll")
        events: List[Mapping[str, Any]] = list(self._retry_batch)
        self._retry_batch = []
        events = [e for e in events if not self.bus.is_quarantined(e["event_id"])]
        timeout = self.idle_block_s if poll_timeout is None else poll_timeout
        events.extend(self.bus.poll(timeout=0.0 if events else timeout))
        if not events:
            return "idle"

        if self.phase1_lifecycle:
            self._emit(
                "RUNTIME_TICK_STARTED",
                {
                    "tick_index": int(self.state["self"]["ticks"]) + 1,
                    "event_refs": [event["event_id"] for event in events],
                },
            )

        # 2 — world state (poll-emitted events fold here; handler emissions fold at _emit)
        self._stage("world_state")
        for e in events:
            self.state = ws.apply(self.state, e)
        view = readonly_view(self.state)

        # 3 — arousal (AEP processor may emit restrict-only drafts; carries no authority)
        self._stage("arousal")
        aep_state: Mapping[str, Any] = {"max_severity": 0, "dimensions": {}}
        process_tick = getattr(self.arousal, "process_tick", None)
        if callable(process_tick):
            prior_aep = [
                event
                for event in self.bus.read_all()
                if str(event.get("type", "")).startswith("AEP_")
            ]
            polled_ids = {event["event_id"] for event in events}
            recorded_signal_ids = {
                str(event.get("payload", {}).get("signal_id"))
                for event in prior_aep
                if event.get("type") == "AEP_SIGNAL_RECORDED"
            }
            for event in prior_aep:
                if event.get("type") != "AEP_SIGNAL_EMITTED":
                    continue
                if event["event_id"] in polled_ids:
                    continue
                signal_id = str(event.get("payload", {}).get("signal_id") or event["event_id"])
                if signal_id in recorded_signal_ids:
                    continue
                self.state = ws.apply(self.state, event)
            tick_result, ok = self._run_handler(
                self.arousal.handler_id,
                events,
                lambda: process_tick(events, view, prior_aep),
            )
            if ok and isinstance(tick_result, tuple) and len(tick_result) == 2:
                drafts, state = tick_result
                if drafts:
                    self._emit_drafts(drafts, self.arousal.handler_id)
                if isinstance(state, Mapping):
                    aep_state = state
            elif ok and tick_result is not None and not isinstance(tick_result, tuple):
                aep_state = tick_result
        else:
            result, ok = self._run_handler(
                self.arousal.handler_id,
                events,
                lambda: self.arousal.read(events, view),
            )
            if ok and result is not None:
                aep_state = result

        # 4 — CRR cycle check (may consume the iteration)
        self._stage("recovery_check")
        should_cycle, ok = self._run_handler(
            self.recovery.handler_id, events,
            lambda: self.recovery.should_enter_cycle(view, aep_state))
        if ok and should_cycle:
            bind_runtime = getattr(self.recovery, "bind_runtime", None)
            if callable(bind_runtime):
                bind_runtime(self.bus, self.state)
            record_head = getattr(self.recovery, "record_event_log_head", None)
            if callable(record_head):
                record_head(self.bus.head_hash, self.bus.next_seq - 1)
            drafts, ok2 = self._run_handler(self.recovery.handler_id, events,
                                            lambda: validate_drafts(
                                                self.recovery.execute_cycle(),
                                                self.recovery.handler_id))
            if ok2 and drafts:
                self._emit_drafts(drafts, self.recovery.handler_id)
            self._finish_tick(tick_t0, events, [], [], recovered=True)
            return "recovery"

        # 4a — YSR soft-reset (never consumes the iteration)
        self._stage("yawn_check")
        panic_active = self.panic.active() or bool(view.get("environment", {}).get("panic"))
        bind_ysr = getattr(self.yawn, "bind_runtime", None)
        if callable(bind_ysr):
            bind_ysr(self.bus, self.state)
        should_yawn, ok_ysr = self._run_handler(
            self.yawn.handler_id,
            events,
            lambda: self.yawn.should_yawn(
                view,
                aep_state,
                panic_active=panic_active,
            ),
        )
        if ok_ysr and should_yawn:
            drafts, ok_ysr2 = self._run_handler(
                self.yawn.handler_id,
                events,
                lambda: validate_drafts(
                    self.yawn.execute_yawn(
                        view,
                        aep_state,
                        panic_active=panic_active,
                    ),
                    self.yawn.handler_id,
                ),
            )
            if ok_ysr2 and drafts:
                self._emit_drafts(drafts, self.yawn.handler_id)

        # 4b — MSC quiet observation (never consumes the iteration)
        self._stage("meditation_check")
        bind_msc = getattr(self.meditation, "bind_runtime", None)
        if callable(bind_msc):
            bind_msc(self.bus, self.state)
        should_meditate, ok_msc = self._run_handler(
            self.meditation.handler_id,
            events,
            lambda: self.meditation.should_enter_cycle(
                view,
                aep_state,
                panic_active=panic_active,
            ),
        )
        if ok_msc and should_meditate:
            drafts, ok_msc2 = self._run_handler(
                self.meditation.handler_id,
                events,
                lambda: validate_drafts(
                    self.meditation.execute_cycle(
                        view,
                        aep_state,
                        panic_active=panic_active,
                    ),
                    self.meditation.handler_id,
                ),
            )
            if ok_msc2 and drafts:
                self._emit_drafts(drafts, self.meditation.handler_id)

        # 5 — memory retrieve (provenance is part of the record)
        self._stage("memory_retrieve")
        retrieval, ok = self._run_handler(self.memory.handler_id, events,
                                         lambda: self.memory.retrieve(view, events))
        memory_ctx = retrieval if isinstance(retrieval, Mapping) else {"context": {}, "provenance": None}
        retrieve_drafts = memory_ctx.get("drafts") if isinstance(memory_ctx, Mapping) else None
        if ok and retrieve_drafts:
            self._emit_drafts(list(retrieve_drafts), self.memory.handler_id)
        elif ok and memory_ctx.get("provenance") is not None:
            self._emit(
                "MEMORY_RETRIEVED",
                {
                    "provenance": _jsonable(memory_ctx.get("provenance")),
                    "event_refs": [event["event_id"] for event in events],
                },
                source=f"handler:{self.memory.handler_id}",
                causal_parents=[event["event_id"] for event in events],
            )

        # 6 — cognition (conditional: only if the batch warrants an LLM pass)
        self._stage("cognition")
        proposals: List[Mapping[str, Any]] = []
        eligible = [e for e in events if self.bus.registry.cognition_eligible(e["type"])]
        if eligible:
            context = {
                "events": [dict(e) for e in eligible],
                "world_state": view,
                "memory": memory_ctx.get("context", {}),
                "arousal": aep_state,
            }
            drafts, ok = self._run_handler(
                self.cognition.handler_id, eligible,
                lambda: validate_drafts(self.cognition.propose(context),
                                        self.cognition.handler_id))
            if ok and drafts:
                emitted = self._emit_drafts(drafts, self.cognition.handler_id)
                proposals = [
                    event for event in emitted
                    if event["type"] in COGNITION_DECISION_PROPOSAL_TYPES
                ]
            elif not ok:
                proposals = [self._emit("PROPOSAL_FAILED",
                                        {"reason": "cognition handler failed",
                                         "event_refs": [e["event_id"] for e in eligible]},
                                        source=f"handler:{self.cognition.handler_id}")]
                proposals = []  # a failure record is not a proposal

        # 7 — decision pipeline (SOAR/HAL/GPP)
        self._stage("decision")
        decisions: List[Mapping[str, Any]] = []
        drafts, ok = self._run_handler(
            self.decision.handler_id, events,
            lambda: validate_drafts(
                self.decision.evaluate(events, proposals, view, aep_state),
                self.decision.handler_id))
        if ok and drafts:
            decisions = self._emit_drafts(drafts, self.decision.handler_id)
        self._record_governance_traces(decisions, events)

        # 8 — kernel execute (sole gate; OEA dispatch happens INSIDE — INV-A28)
        self._stage("execute")
        results: List[Mapping[str, Any]] = []
        committed = [d for d in decisions if d["type"] == "DECISION_EVENT"]
        if committed:
            drafts, ok = self._run_handler(
                self.kernel.handler_id, committed,
                lambda: validate_drafts(self.kernel.execute(committed, view),
                                        self.kernel.handler_id))
            if ok and drafts:
                results = self._emit_drafts(drafts, self.kernel.handler_id)

        # 10 — memory store (write-back is evented)
        self._stage("memory_store")
        drafts, ok = self._run_handler(
            self.memory.handler_id, events,
            lambda: validate_drafts(self.memory.store(events, proposals, results),
                                    self.memory.handler_id))
        if ok and drafts:
            self._emit_drafts(drafts, self.memory.handler_id)
        elif not ok:
            # Tick completes — events are already durable in the bus; memory is derived.
            self._emit("MEMORY_WRITE_FAILED", {"event_refs": [e["event_id"] for e in events]})

        # 11 — tick record
        self._finish_tick(tick_t0, events, proposals, results, recovered=False)
        for e in events:
            self._poison_counts.pop(e["event_id"], None)  # tick survived: counts reset
        return "tick"

    def _finish_tick(self, tick_t0: float, events, proposals, results, recovered: bool) -> None:
        self._stage("tick_record")
        elapsed = self._monotonic() - tick_t0
        if elapsed > self.tick_budget_s:
            self._emit("TICK_SLOW", {"elapsed_s": round(elapsed, 3),
                                     "budget_s": self.tick_budget_s})
        # State hash BEFORE the TICK_COMPLETED event itself — replay compares at
        # the TICK_COMPLETED boundary, then applies it (RTC_WORLD_STATE_SPEC §4).
        tick_hash = ws.state_hash(self.state)
        tick_payload = {
            "state_hash": tick_hash,
            "recovered": recovered,
            "event_refs": [e["event_id"] for e in events],
            "proposal_refs": [p["event_id"] for p in proposals],
            "result_refs": [r["event_id"] for r in results],
            "elapsed_s": round(elapsed, 3),
        }
        completion_type = "RUNTIME_TICK_COMPLETED" if self.phase1_lifecycle else "TICK_COMPLETED"
        self._emit(completion_type, tick_payload)
        ticks = self.state["self"]["ticks"]
        if self.snapshot_every_ticks and ticks % self.snapshot_every_ticks == 0:
            ws.write_snapshot(self.state, self.snapshot_dir)

    def _record_governance_traces(self, decisions, events) -> None:
        if self.governance_trace is None:
            return
        trigger_refs = [event["event_id"] for event in events]
        for decision in decisions:
            payload = _jsonable(decision.get("payload", {}))
            decision_value = "allow" if decision["type"] == "DECISION_EVENT" else "deny"
            trace_event_name = "outbound_validated" if decision_value == "allow" else "publish_blocked"
            record = self.governance_trace.emit(
                run_id=f"rtc-{trigger_refs[0] if trigger_refs else decision['event_id']}",
                workflow_id="rtc-phase0",
                layer="governance",
                component="rtc_decision_pipeline",
                event=trace_event_name,
                decision=decision_value,
                reason_code=str(payload.get("reason") or payload.get("verdict") or "phase0_trace"),
                summary=f"RTC recorded GPP Phase 0 trace for {decision['type']}",
                actor={"type": "agent", "id": "agent0"},
                subject={"type": "rtc_decision", "decision_event_id": decision["event_id"]},
                inputs={"trigger_refs": trigger_refs, "decision": payload},
                outputs={"decision_event_id": decision["event_id"]},
                external_calls=0,
                metadata={
                    "phase": "gpp_phase0_trace_only",
                    "decision_event_id": decision["event_id"],
                    "trigger_event_refs": trigger_refs,
                },
            )
            if record is None:
                continue
            self._emit(
                "GOVERNANCE_TRACE_RECORDED",
                {
                    "schema": record["schema"],
                    "schema_version": record["schema_version"],
                    "trace_path": str(self.governance_trace.path),
                    "trace_seq": record["seq"],
                    "trace_event_hash": record["event_hash"],
                    "decision_event_id": decision["event_id"],
                    "enforcement": "none_phase0_trace_only",
                },
                source="loop",
                causal_parents=[decision["event_id"]],
            )

    def run_forever(self) -> int:
        """
        Blocking loop. Returns process exit code: 0 on clean stop, 1 on the
        one fatal (bus write failure — supervisor restarts, replay recovers).
        """
        self.start()
        try:
            while self.alive:
                outcome = self.run_once()
                if outcome == "panic":
                    time.sleep(min(self.idle_block_s, 1.0))
        except BusWriteError:
            self._write_status("fatal_bus_write")
            return 1
        except KeyboardInterrupt:
            self.stop(reason="signal")
            return 0
        self.stop(reason="alive=False")
        return 0


__all__ = ["RuntimeLoop", "PanicFlag", "RuntimeDisabled", "rtc_enabled", "STAGES",
           "RUNTIME_VERSION", "POISON_QUARANTINE_AFTER"]
