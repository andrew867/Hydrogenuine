"""RTC handler registry — Phase 0/1 stub wiring without bus bypass."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from hg_oea.stub import OEAStub
from hg_runtime.bus import EventBus
from hg_runtime.handlers.aep_arousal import Phase1AEPArousalHandler
from hg_runtime.handlers.decision_phase1 import Phase1DecisionHandler
from hg_runtime.handlers.stubs import (
    StubArousalReader,
    StubCognitionHandler,
    StubDecisionHandler,
    StubKernelHandler,
    StubMemoryHandler,
    StubRecoveryHandler,
)
from hg_runtime.msc.handler import Phase1MSCHandler, StubMSCHandler
from hg_runtime.yawn.handler import Phase1YSRHandler, StubYSRHandler
from hg_runtime.loop import PanicFlag, RuntimeLoop
from hg_ueak.stub import UEAKStub


def _streaming_enabled() -> bool:
    return os.environ.get("HG_RTC_COGNITION_STREAMING", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _aep_processor_enabled() -> bool:
    raw = os.environ.get("HG_RTC_AEP_PROCESSOR", "1").strip().lower()
    return raw not in ("0", "false", "no")


def _permit_bind_enabled() -> bool:
    raw = os.environ.get("HG_GPP_PERMIT_BIND", "1").strip().lower()
    return raw not in ("0", "false", "no")


def _build_cognition():
    if _streaming_enabled():
        from hg_runtime.cognition import StreamingCognitionHandler, build_provider, load_cognition_config

        return StreamingCognitionHandler(provider=build_provider(load_cognition_config()))
    return StubCognitionHandler()


def _hal_enabled() -> bool:
    return os.environ.get("HG_HAL_ENABLED", "1").strip().lower() not in ("0", "false", "no")


def _memory_mode() -> str:
    return os.environ.get("HG_RTC_MEMORY_MODE", "phase1").strip().lower()


def _build_memory(*, runtime_dir: Optional[Path] = None):
    if _memory_mode() in ("stub", "phase0", "stubs"):
        return StubMemoryHandler()
    from hg_runtime.memory import Phase1MemoryHandler

    return Phase1MemoryHandler(runtime_dir=runtime_dir or Path("memory/runtime"))


def _build_decision(*, runtime_dir: Optional[Path] = None):
    if not _hal_enabled() and not _permit_bind_enabled():
        return StubDecisionHandler()

    permit_binder = None
    if _permit_bind_enabled():
        from hg_core.governance.permit_binder import PermitBinder
        from hg_core.governance.trace_emitter import TraceEmitter

        trace_path = (runtime_dir or Path("memory/runtime")) / "governance_trace.jsonl"
        trace = TraceEmitter(trace_path, enabled=True)
        permit_binder = PermitBinder(trace_emitter=trace)

    if _hal_enabled():
        from hg_runtime.handlers.hal_decision import Phase1HALDecisionHandler

        return Phase1HALDecisionHandler(permit_binder=permit_binder)
    return Phase1DecisionHandler(permit_binder=permit_binder)


def _build_arousal():
    if _aep_processor_enabled():
        return Phase1AEPArousalHandler()
    return StubArousalReader()


def _msc_enabled() -> bool:
    return os.environ.get("HG_MSC_ENABLED", "0").strip().lower() in ("1", "true", "yes")


def _build_meditation(*, runtime_dir: Optional[Path] = None):
    if _msc_enabled():
        return Phase1MSCHandler(runtime_dir=runtime_dir)
    return StubMSCHandler()


def _ysr_enabled() -> bool:
    return os.environ.get("HG_YSR_ENABLED", "0").strip().lower() in ("1", "true", "yes")


def _build_yawn(*, runtime_dir: Optional[Path] = None):
    if _ysr_enabled():
        return Phase1YSRHandler(runtime_dir=runtime_dir)
    return StubYSRHandler()


@dataclass(frozen=True)
class HandlerRegistry:
    """Named handler slots for the RTC loop. Handlers return drafts; the loop owns the bus."""

    cognition: Any
    decision: Any
    ueak: UEAKStub
    oea: OEAStub
    kernel: StubKernelHandler
    memory: Any
    arousal: Any
    recovery: Any
    yawn: Any
    meditation: Any

    @classmethod
    def phase0_stubs(cls) -> HandlerRegistry:
        ueak = UEAKStub()
        oea = OEAStub()
        return cls(
            cognition=StubCognitionHandler(),
            decision=StubDecisionHandler(),
            ueak=ueak,
            oea=oea,
            kernel=StubKernelHandler(ueak=ueak, oea=oea),
            memory=StubMemoryHandler(),
            arousal=StubArousalReader(),
            recovery=StubRecoveryHandler(),
            yawn=StubYSRHandler(),
            meditation=StubMSCHandler(),
        )

    @classmethod
    def phase1_integrated(cls, *, runtime_dir: Optional[Path] = None) -> HandlerRegistry:
        """Phase 1 integrated handlers: streaming cognition (opt-in), AEP processor, GPP bind scaffold."""
        ueak = UEAKStub()
        oea = OEAStub()
        return cls(
            cognition=_build_cognition(),
            decision=_build_decision(runtime_dir=runtime_dir),
            ueak=ueak,
            oea=oea,
            kernel=StubKernelHandler(ueak=ueak, oea=oea),
            memory=_build_memory(runtime_dir=runtime_dir),
            arousal=_build_arousal(),
            recovery=StubRecoveryHandler(),
            yawn=_build_yawn(runtime_dir=runtime_dir),
            meditation=_build_meditation(runtime_dir=runtime_dir),
        )

    @classmethod
    def build_from_env(cls, *, runtime_dir: Optional[Path] = None) -> HandlerRegistry:
        mode = os.environ.get("HG_RTC_HANDLER_MODE", "phase1").strip().lower()
        if mode in ("phase0", "stubs", "stub"):
            return cls.phase0_stubs()
        return cls.phase1_integrated(runtime_dir=runtime_dir)

    def build_loop(
        self,
        bus: EventBus,
        *,
        runtime_dir: Path,
        panic: Optional[PanicFlag] = None,
        governance_trace=None,
        idle_block_s: float = 0.0,
        tick_budget_s: float = 60.0,
        snapshot_every_ticks: int = 0,
        require_enabled: bool = False,
        phase1_lifecycle: bool = True,
        stage_hook=None,
    ) -> RuntimeLoop:
        return RuntimeLoop(
            bus,
            cognition=self.cognition,
            decision=self.decision,
            kernel=self.kernel,
            memory=self.memory,
            arousal=self.arousal,
            recovery=self.recovery,
            yawn=self.yawn,
            meditation=self.meditation,
            runtime_dir=runtime_dir,
            governance_trace=governance_trace,
            idle_block_s=idle_block_s,
            tick_budget_s=tick_budget_s,
            snapshot_every_ticks=snapshot_every_ticks,
            require_enabled=require_enabled,
            phase1_lifecycle=phase1_lifecycle,
            panic=panic,
            stage_hook=stage_hook,
        )


__all__ = ["HandlerRegistry"]
