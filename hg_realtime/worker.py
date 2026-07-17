"""Realtime worker: timer thread + scheduler poll loop, bridge scheduler, meditation worker, reflection worker. Production uses RedisStreamsBus."""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from .bus.interface import EventBus
from .bus.memory_bus import InMemoryBus
from .integrations.dag_launcher import DagLauncher
from .integrations.policy_gate import PolicyGate
from .integrations.run_index import default_run_index_writer
from .leases.store import default_lease_store
from .scheduler.service import RealTimeScheduler, SchedulerConfig
from .scheduler.timer_source import start_timer_thread
from .scheduler.schedule_config import load_schedule

logger = logging.getLogger(__name__)


def scheduler_enabled() -> bool:
    raw = (os.getenv("HG_SCHEDULER_ENABLED", "").strip() or "1").lower()
    return raw not in {"0", "false", "no", "off"}


def runtime_bus_mode(redis_url: Optional[str] = None) -> str:
    resolved = (redis_url if redis_url is not None else (os.getenv("REDIS_URL", "").strip() or os.getenv("HG_REDIS_URL", "").strip()))
    return "redis_streams" if resolved else "in_memory"


def _make_bus(redis_url: Optional[str] = None) -> EventBus:
    if redis_url and redis_url.strip():
        from .bus.redis_streams_bus import RedisStreamsBus
        return RedisStreamsBus(redis_url=redis_url.strip())
    return InMemoryBus()


def main() -> int:
    # Apply env.vars from hg.json (HG_CONFIG) so OpenVINO, LLM keys, etc. are available
    try:
        from hg_core.setup_data import apply_hg_env_to_process
        apply_hg_env_to_process()
    except Exception:
        pass
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        from hg_core.gate.service import ensure_demo_backup_stub

        backup_dir = ensure_demo_backup_stub()
        if backup_dir:
            logger.info("created demo backup marker at %s", backup_dir)
    except Exception as exc:
        logger.debug("demo backup stub skipped: %s", exc)
    redis_url = os.getenv("REDIS_URL", "").strip() or os.getenv("HG_REDIS_URL", "").strip()
    bus = _make_bus(redis_url or None)
    bus_mode = runtime_bus_mode(redis_url or None)
    workspace: Optional[Path] = None
    try:
        from hg_lib.config import get_workspace_root
        workspace = get_workspace_root()
    except Exception:
        workspace = Path.cwd()

    run_index = default_run_index_writer()
    lease_store = default_lease_store()
    launcher = DagLauncher(
        workspace=workspace,
        run_index_writer=run_index,
        lease_store=lease_store,
        worker_id="realtime-worker-1",
        bus=bus,
    )
    policy = PolicyGate()
    cfg = SchedulerConfig()
    scheduler = RealTimeScheduler(bus=bus, launcher=launcher, policy=policy, run_index=run_index, cfg=cfg)

    # Cognition bridge: RUN_COMPLETED -> MEDITATION_REQUESTED -> meditation worker
    bridge_scheduler = None
    meditation_worker = None
    reflection_worker = None
    try:
        from hg_bridge.bridge_scheduler import CognitionBridgeScheduler
        from hg_bridge.config import load_bridge_config
        from hg_bridge.meditation_worker import MeditationWorker
        from hg_bridge.integrations import RunDirTraceStore, FilePersonaStore, ContextualSteeringSink
        from hg_cognition.integrations.memory_impls import GatewayArtifactStore
        from .reflection_worker import ReflectionWorker
        from .steering.sqlite_adapter import SqliteSteeringAdapter

        root = workspace or Path.cwd()
        memory = root / "memory"
        persona_dir = memory / "persona"
        artifacts_dir = memory / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        persona_dir.mkdir(parents=True, exist_ok=True)

        trace_store = RunDirTraceStore(run_index)
        persona_store = FilePersonaStore(persona_dir)
        artifact_store = GatewayArtifactStore()
        steering_adapter = SqliteSteeringAdapter()
        steering_sink = ContextualSteeringSink(steering_adapter)

        bridge_scheduler = CognitionBridgeScheduler(bus=bus, cfg=load_bridge_config(workspace))
        meditation_worker = MeditationWorker(
            bus=bus,
            trace_store=trace_store,
            persona_store=persona_store,
            artifact_store=artifact_store,
            steering_sink=steering_sink,
            worker_id="meditate-1",
        )
        reflection_worker = ReflectionWorker(
            workspace_root=root,
            bus=bus,
            worker_id="reflect-1",
        )
    except ImportError as e:
        logger.debug("cognition bridge not available: %s", e)

    timer_thread = None
    timer_stop = threading.Event()
    if scheduler_enabled():
        state = load_schedule(workspace)
        timer_thread, timer_stop = start_timer_thread(bus, state, workspace_root=workspace, daemon=True)
    else:
        logger.warning("realtime scheduler disabled by HG_SCHEDULER_ENABLED")
    worker_stop = threading.Event()

    def shutdown(_sig: Optional[int] = None, _frame: Optional[object] = None) -> None:
        worker_stop.set()
        timer_stop.set()
        if timer_thread is not None:
            timer_thread.join(timeout=5.0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info("realtime worker started (bus_mode=%s, redis=%s); timer thread running; scheduler loop in main", bus_mode, bool(redis_url))
    if bus_mode == "in_memory":
        logger.warning("realtime worker is using InMemoryBus fallback; configure REDIS_URL or HG_REDIS_URL for production-like operation")

    last_reconcile_ts = 0.0
    reconcile_interval_s = 900.0
    try:
        raw_interval = (os.getenv("HG_RUN_RECONCILE_INTERVAL_S") or "900").strip()
        reconcile_interval_s = max(60.0, float(raw_interval))
    except ValueError:
        pass
    def _run_reconcile(label: str) -> None:
        nonlocal last_reconcile_ts
        try:
            from operator_console.server.app.services.run_index_db import reconcile_runs_from_disk

            reconcile_result = reconcile_runs_from_disk(limit=2000)
            last_reconcile_ts = time.time()
            mismatches = int(reconcile_result.get("mismatches_before") or 0)
            repaired = int(reconcile_result.get("repaired_stale_running") or 0)
            if mismatches or repaired:
                logger.warning(
                    "run index reconcile %s: mismatches_before=%s repaired_stale_running=%s updated=%s",
                    label,
                    mismatches,
                    repaired,
                    reconcile_result.get("updated"),
                )
            else:
                logger.info("run index reconcile %s: ok", label)
        except Exception as exc:
            logger.debug("run index reconcile %s skipped: %s", label, exc)

    threading.Thread(target=_run_reconcile, args=("on startup",), daemon=True, name="run-index-reconcile").start()

    try:
        for key_name, label in (("FOURCLAW_API_KEY", "fourclaw"), ("MOLTBOOK_API_KEY", "moltbook")):
            if not (os.getenv(key_name) or "").strip():
                logger.warning("demo social: %s is not set (%s); live posts may fail", label, key_name)
    except Exception:
        pass

    try:
        while not worker_stop.is_set():
            if time.time() - last_reconcile_ts >= reconcile_interval_s:
                threading.Thread(
                    target=_run_reconcile,
                    args=("periodic",),
                    daemon=True,
                    name="run-index-reconcile-periodic",
                ).start()
                last_reconcile_ts = time.time()
            scheduler.tick_once()
            if bridge_scheduler is not None:
                bridge_scheduler.tick_once()
            if meditation_worker is not None:
                meditation_worker.tick_once()
            if reflection_worker is not None:
                reflection_worker.tick_once()
            worker_stop.wait(timeout=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
