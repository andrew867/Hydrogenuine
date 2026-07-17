"""RTC demo runner — finite Phase 0 ticks or Phase 1 bounded persistent mode."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import List, Optional

from hg_runtime.config import RuntimeConfig
from hg_runtime.controller import PersistentLoopController
from hg_runtime.bus import EventBus
from hg_runtime.handlers import (
    StubArousalReader,
    StubCognitionHandler,
    StubDecisionHandler,
    StubKernelHandler,
    StubMemoryHandler,
    StubRecoveryHandler,
)
from hg_runtime.loop import RuntimeLoop
from hg_runtime.replay import replay
from hg_core.governance.trace_emitter import TraceEmitter


def build_loop(
    runtime_dir: Path,
    *,
    require_enabled: bool = False,
    governance_trace=None,
    phase1_lifecycle: bool = False,
) -> RuntimeLoop:
    bus = EventBus(runtime_dir)
    if governance_trace is None and os.environ.get("HG_GOV_TRACE_ENABLED", "0").strip() == "1":
        governance_trace = TraceEmitter(runtime_dir / "governance_trace.jsonl")
    return RuntimeLoop(
        bus,
        cognition=StubCognitionHandler(),
        decision=StubDecisionHandler(),
        kernel=StubKernelHandler(),
        memory=StubMemoryHandler(),
        arousal=StubArousalReader(),
        recovery=StubRecoveryHandler(),
        runtime_dir=runtime_dir,
        governance_trace=governance_trace,
        idle_block_s=0.01,
        snapshot_every_ticks=0,
        require_enabled=require_enabled,
        phase1_lifecycle=phase1_lifecycle,
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run an RTC vertical-slice demo.")
    parser.add_argument("--runtime-dir", type=Path, default=Path("memory/runtime"))
    parser.add_argument("--ticks", type=int, default=1)
    parser.add_argument("--session-id", default="demo")
    parser.add_argument(
        "--persistent",
        action="store_true",
        help="Use Phase 1 persistent controller with lifecycle health events.",
    )
    parser.add_argument(
        "--tick-interval-s",
        type=float,
        default=0.0,
        help="Sleep between productive ticks in persistent mode.",
    )
    parser.add_argument(
        "--governance-trace",
        action="store_true",
        help="Emit GPP Phase 0 trace records and RTC trace-reference events.",
    )
    args = parser.parse_args(argv)

    if args.ticks < 1:
        parser.error("--ticks must be >= 1")

    os.environ.setdefault("HG_RTC_ENABLED", "1")
    governance_trace = (
        TraceEmitter(args.runtime_dir / "governance_trace.jsonl", enabled=True)
        if args.governance_trace
        else None
    )

    path_id = "phase1_integrated" if args.persistent else "demo_phase0"

    if args.persistent:
        config = RuntimeConfig(
            runtime_dir=args.runtime_dir,
            max_ticks=args.ticks,
            tick_interval_s=args.tick_interval_s,
            governance_trace=governance_trace,
            require_enabled=False,
            phase1_lifecycle=True,
            idle_block_s=0.01,
            snapshot_every_ticks=0,
        )
        controller = PersistentLoopController(config)
        controller.loop.start()
        for index in range(args.ticks):
            controller.bus.submit(
                "CHAT_MESSAGE",
                {
                    "session_id": args.session_id,
                    "role": "user",
                    "content": f"rtc persistent demo tick {index + 1}",
                },
                source="plt.chat",
            )
            controller.run_once(poll_timeout=0.01)
        controller.loop.stop(reason="demo_complete")
        runtime_dir = args.runtime_dir
        exit_code = 0
    else:
        loop = build_loop(args.runtime_dir, require_enabled=False, governance_trace=governance_trace)
        loop.start()
        for index in range(args.ticks):
            loop.bus.submit(
                "CHAT_MESSAGE",
                {
                    "session_id": args.session_id,
                    "role": "user",
                    "content": f"rtc phase0 demo tick {index + 1}",
                },
                source="plt.chat",
            )
            loop.run_once(poll_timeout=0.01)
        loop.stop(reason="demo_complete")
        runtime_dir = args.runtime_dir
        exit_code = 0

    result = replay(runtime_dir)
    summary = {
        "ok": result.ok,
        "ticks": result.ticks,
        "events": result.events,
        "state_hash": result.state_hash,
        "path_id": path_id,
        "event_log": str(runtime_dir.resolve()),
        "persistent": args.persistent,
    }
    if governance_trace is not None:
        trace_result = governance_trace.validate_chain()
        summary["governance_trace"] = str(governance_trace.path.resolve())
        summary["governance_trace_ok"] = trace_result.ok
    print(json.dumps(summary, indent=2, sort_keys=True))
    ok = result.ok and summary.get("governance_trace_ok", True) and exit_code == 0
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
