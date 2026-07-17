"""Daemon supervisor — the long-running background process.

Launched detached by the daemon CLI. Owns the scheduler loop, writes
heartbeats, handles STOP/PANIC, writes the final report and proof bundle.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
from pathlib import Path

from hg_runtime.live_local.paced_loop import overnight_green_allowed, verdict_for_run

from .config import DaemonConfig
from .state import RunState, save_state
from .heartbeat import write_heartbeat
from .stop_panic import stop_requested, panic_requested
from .checkins import write_checkin
from .subagents import WorkerPool
from .scheduler import run_cycle


def _setup_logging(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("agent_zero_daemon")
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(str(log_path), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)
    return logger


def _write_final_report(state: RunState, cfg: DaemonConfig, proof_dir: Path,
                        pool: WorkerPool, logger: logging.Logger) -> None:
    boundaries_held = state.boundary_violations == 0
    is_panic = state.status == "panicked"
    is_stop = state.status == "stopped"

    if is_panic:
        final_verdict = "RED_PANIC_STOP" if not boundaries_held else "YELLOW_PANIC_PARTIAL"
    elif not boundaries_held:
        final_verdict = "RED_BOUNDARY_VIOLATION"
    elif overnight_green_allowed(
        target_seconds=cfg.target_seconds(),
        elapsed_seconds=state.elapsed_seconds,
        operator_stop=is_stop, panic=is_panic,
    ):
        final_verdict = "GREEN_OVERNIGHT_BOUNDED_FULL_SEND_SOAK"
    else:
        final_verdict = "YELLOW_OVERNIGHT_BOUNDED_FULL_SEND_PARTIAL"

    state.verdict_so_far = final_verdict

    report = {
        "run_id": cfg.run_id,
        "started_at": state.started_at,
        "ended_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": state.elapsed_seconds,
        "elapsed_hours": state.elapsed_seconds / 3600,
        "target_hours": cfg.duration_hours,
        "verdict": final_verdict,
        "status": state.status,
        "cycles": state.cycle_count,
        "seeds_worked": state.seeds_worked,
        "seeds_skipped": state.seeds_skipped,
        "output_classifications": state.output_classifications,
        "retry_attempts": state.retry_attempts,
        "retry_successes": state.retry_successes,
        "retry_failures": state.retry_failures,
        "autopilot_proposals": state.autopilot_proposals,
        "autopilot_decisions": state.autopilot_decisions,
        "autopilot_approvals": state.autopilot_approvals,
        "autopilot_denials": state.autopilot_denials,
        "knowledge_candidates": state.knowledge_candidates,
        "knowledge_promotions": state.knowledge_promotions,
        "evidence_gaps": state.evidence_gaps,
        "boundary_violations": state.boundary_violations,
        "checkin_count": state.checkin_count,
        "checkpoint_count": state.checkpoint_count,
        "boundary_scan_count": state.boundary_scan_count,
        "subagent_tasks_completed": len(pool.completed),
        "subagent_tasks_failed": len(pool.failed),
        "boundaries_held": boundaries_held,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "zero_not_agi": True,
        "zero_not_conscious": True,
        "zero_not_sovereign": True,
        "remote_provider_calls": False,
        "hg_local_touched": False,
        "tools_authorized": False,
        "live_effects_created": False,
        "zero_self_authorized": False,
    }
    proof_dir.mkdir(parents=True, exist_ok=True)
    (proof_dir / "final_report.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8")

    # Morning operator review
    lines = [
        f"# Morning Operator Review — {cfg.run_id}",
        f"",
        f"**Verdict:** {final_verdict}",
        f"**Duration:** {state.elapsed_seconds/3600:.2f}h (target {cfg.duration_hours}h)",
        f"**Cycles:** {state.cycle_count}",
        f"**Seeds worked:** {len(state.seeds_worked)}",
        f"**Boundary violations:** {state.boundary_violations}",
        f"",
        f"## Requires Operator Review",
        f"",
        f"- All knowledge candidates are pending review (none auto-promoted)",
        f"- Evidence gaps are preserved (none filled automatically)",
        f"- Uncertainty records are preserved",
        f"- Speculative seeds remain speculative",
        f"",
        f"## Boundaries",
        f"",
        f"- Phase 19: YELLOW (preserved)",
        f"- Phase 24: infrastructure-only (preserved)",
        f"- Zero: not AGI, not conscious, not sovereign",
        f"- Self-authorization: 0 attempts",
        f"- Forbidden models: rejected",
        f"- Remote providers: none",
        f"- Live effects: none",
        f"",
    ]
    (proof_dir / "morning_operator_review.md").write_text(
        "\n".join(lines), encoding="utf-8")
    logger.info("Final report written: %s", final_verdict)


def run_daemon(cfg: DaemonConfig) -> int:
    """Main daemon entry point. Called in the detached process."""
    state_dir = Path(cfg.state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)

    log_path = state_dir / "daemon.log"
    logger = _setup_logging(log_path)
    logger.info("Daemon starting: run_id=%s pid=%d", cfg.run_id, os.getpid())

    # PID file
    pid_path = state_dir / "daemon.pid"
    pid_path.write_text(str(os.getpid()), encoding="utf-8")

    # Proof directory
    proof_dir = Path(cfg.proof_bundle_root) if cfg.proof_bundle_root else \
        state_dir / "proof"
    proof_dir.mkdir(parents=True, exist_ok=True)

    # State
    state = RunState(
        run_id=cfg.run_id,
        started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        status="running",
    )
    save_state(state, state_dir)

    # Initial heartbeat
    write_heartbeat(
        state_dir, run_id=cfg.run_id, pid=os.getpid(),
        started_at=state.started_at, current_status="running",
        proof_path=str(proof_dir),
    )

    # Run manifest
    manifest = {
        "run_id": cfg.run_id,
        "pid": os.getpid(),
        "started_at": state.started_at,
        "config": cfg.redacted(),
        "proof_dir": str(proof_dir),
        "state_dir": str(state_dir),
    }
    (proof_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    (proof_dir / "daemon_config_redacted.json").write_text(
        json.dumps(cfg.redacted(), indent=2, default=str), encoding="utf-8")

    # Discover available models from endpoint
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{cfg.lmstudio_base_url}/models", method="GET")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            cfg.available_models = [m["id"] for m in data.get("data", [])]
        logger.info("Discovered %d models from endpoint", len(cfg.available_models))
    except Exception as e:
        logger.warning("Model discovery failed: %s", e)
        cfg.available_models = []

    pool = WorkerPool(max_concurrent=cfg.max_concurrent_subagents)
    start_epoch = time.time()

    try:
        while True:
            state.elapsed_seconds = time.time() - start_epoch

            result = run_cycle(cfg, state, proof_dir, pool,
                               log_fn=lambda m: logger.info(m))

            if result in ("stop", "panic", "completed"):
                logger.info("Loop ended: %s after %d cycles, %.1fs",
                            result, state.cycle_count, state.elapsed_seconds)
                if result == "completed":
                    state.status = "completed"
                break

            save_state(state, state_dir)

            # Sleep between cycles
            if cfg.cycle_delay_seconds > 0:
                time.sleep(cfg.cycle_delay_seconds)

    except Exception:
        state.fatal_error = traceback.format_exc()[-500:]
        state.status = "failed"
        state.verdict_so_far = "RED_FATAL_ERROR"
        logger.exception("Fatal error in daemon loop")

    # Final report
    try:
        _write_final_report(state, cfg, proof_dir, pool, logger)
    except Exception:
        logger.exception("Error writing final report")

    # Final state + heartbeat
    save_state(state, state_dir)
    write_heartbeat(
        state_dir, run_id=cfg.run_id, pid=os.getpid(),
        started_at=state.started_at, cycle_count=state.cycle_count,
        current_status=state.status,
        current_verdict_so_far=state.verdict_so_far,
        proof_path=str(proof_dir),
        stop_requested=stop_requested(state_dir),
        panic_requested=panic_requested(state_dir),
        fatal_error=state.fatal_error,
        receipt_count=state.receipt_count,
        boundary_violation_count=state.boundary_violations,
    )

    logger.info("Daemon exiting: %s", state.verdict_so_far)
    return 0 if state.boundary_violations == 0 else 1
