"""Daemon launcher — detaches the supervisor and returns immediately."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from .config import DaemonConfig
from .heartbeat import read_heartbeat, heartbeat_path
from .state import load_state, state_path
from .stop_panic import (
    write_stop, write_panic, write_request_checkin, write_request_finalize,
    stop_path, panic_path,
)
from .run_registry import (
    generate_run_id, state_dir_for_run, proof_dir_for_launch, proof_dir_for_soak,
)
from .checkin_resolve import resolve_checkin_from_heartbeat_or_proof, checkin_completeness


def start(cfg: DaemonConfig) -> dict:
    """Launch the daemon detached. Returns immediately with run info."""
    run_id = cfg.run_id or generate_run_id()
    cfg.run_id = run_id
    sdir = state_dir_for_run(run_id)
    sdir.mkdir(parents=True, exist_ok=True)
    cfg.state_dir = str(sdir)

    proof_soak = proof_dir_for_soak()
    proof_soak.mkdir(parents=True, exist_ok=True)
    cfg.proof_bundle_root = str(proof_soak)

    # Write config for the worker to load (full config, not redacted)
    from dataclasses import asdict
    config_path = sdir / "daemon_config.json"
    config_path.write_text(json.dumps(asdict(cfg), indent=2), encoding="utf-8")

    # Control directory
    (sdir / "control").mkdir(parents=True, exist_ok=True)

    # Launch the supervisor as a detached process
    worker_script = Path(__file__).parent / "_worker_entry.py"
    cmd = [sys.executable, str(worker_script), str(sdir)]

    kwargs = {}
    if sys.platform == "win32":
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        kwargs["creationflags"] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    log_path = sdir / "daemon.log"
    log_fd = open(log_path, "a", encoding="utf-8")
    proc = subprocess.Popen(
        cmd, stdout=log_fd, stderr=log_fd, stdin=subprocess.DEVNULL,
        **kwargs,
    )

    # Write PID
    (sdir / "daemon.pid").write_text(str(proc.pid), encoding="utf-8")

    # Wait for heartbeat (up to 30s)
    deadline = time.time() + 30
    alive = False
    while time.time() < deadline:
        hb = read_heartbeat(sdir)
        if hb is not None:
            alive = True
            break
        time.sleep(1)

    monitor_commands = [
        f"python scripts/agent_zero_overnight_daemon.py status --run-id {run_id}",
        f"python scripts/agent_zero_overnight_daemon.py tail --run-id {run_id}",
        f"python scripts/agent_zero_overnight_daemon.py checkin --run-id {run_id}",
        f"python scripts/agent_zero_overnight_daemon.py stop --run-id {run_id}",
        f"python scripts/agent_zero_overnight_daemon.py panic --run-id {run_id}",
        f"python scripts/agent_zero_overnight_daemon.py finalize --run-id {run_id}",
    ]

    return {
        "run_id": run_id,
        "pid": proc.pid,
        "alive": alive,
        "state_dir": str(sdir),
        "proof_dir": str(proof_soak),
        "log_path": str(log_path),
        "stop_file": str(stop_path(sdir)),
        "panic_file": str(panic_path(sdir)),
        "heartbeat_path": str(heartbeat_path(sdir)),
        "monitor_commands": monitor_commands,
    }


def status(run_id: str) -> dict:
    sdir = state_dir_for_run(run_id)
    hb = read_heartbeat(sdir)
    st = load_state(sdir)
    pid_path = sdir / "daemon.pid"
    pid = int(pid_path.read_text().strip()) if pid_path.exists() else None

    alive = False
    if pid:
        try:
            if sys.platform == "win32":
                import ctypes
                kernel32 = ctypes.windll.kernel32
                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                if handle:
                    kernel32.CloseHandle(handle)
                    alive = True
            else:
                os.kill(pid, 0)
                alive = True
        except (OSError, ProcessLookupError):
            pass

    proof_path = hb.get("proof_path", "") if hb else ""
    resolved_checkin = resolve_checkin_from_heartbeat_or_proof(hb, proof_path)

    return {
        "run_id": run_id,
        "pid": pid,
        "alive": alive,
        "heartbeat": hb,
        "last_checkin_path": resolved_checkin,
        "state": {
            "status": st.status if st else "unknown",
            "cycle_count": st.cycle_count if st else 0,
            "elapsed_seconds": st.elapsed_seconds if st else 0,
            "verdict_so_far": st.verdict_so_far if st else "unknown",
            "seeds_worked": st.seeds_worked if st else [],
            "output_classifications": st.output_classifications if st else {},
        } if st else None,
    }


def tail(run_id: str, lines: int = 50) -> str:
    sdir = state_dir_for_run(run_id)
    log_path = sdir / "daemon.log"
    if not log_path.exists():
        return f"No log file at {log_path}"
    text = log_path.read_text(encoding="utf-8")
    all_lines = text.splitlines()
    return "\n".join(all_lines[-lines:])


def request_checkin(run_id: str, wait: bool = False, wait_timeout: float = 30.0) -> dict:
    sdir = state_dir_for_run(run_id)
    hb = read_heartbeat(sdir)
    proof_path = hb.get("proof_path", "") if hb else ""

    before_checkin = resolve_checkin_from_heartbeat_or_proof(hb, proof_path)

    write_request_checkin(sdir)

    if not wait:
        return {
            "run_id": run_id,
            "requested": True,
            "waited": False,
            "last_checkin_path": before_checkin,
        }

    deadline = time.time() + wait_timeout
    while time.time() < deadline:
        hb = read_heartbeat(sdir)
        current = resolve_checkin_from_heartbeat_or_proof(hb, proof_path)
        if current and current != before_checkin:
            return {
                "run_id": run_id,
                "requested": True,
                "waited": True,
                "last_checkin_path": current,
            }
        time.sleep(1)

    current = resolve_checkin_from_heartbeat_or_proof(hb, proof_path)
    return {
        "run_id": run_id,
        "requested": True,
        "waited": True,
        "last_checkin_path": current or before_checkin,
        "wait_timeout": True,
    }


def stop(run_id: str) -> str:
    sdir = state_dir_for_run(run_id)
    write_stop(sdir)
    return f"STOP written for {run_id}"


def panic(run_id: str) -> str:
    sdir = state_dir_for_run(run_id)
    write_panic(sdir)
    return f"PANIC written for {run_id}"


def finalize(run_id: str) -> str:
    sdir = state_dir_for_run(run_id)
    write_request_finalize(sdir)
    return f"Finalize requested for {run_id}"


def resume(run_id: str, cfg: DaemonConfig | None = None) -> dict:
    sdir = state_dir_for_run(run_id)
    st = load_state(sdir)
    if st is None:
        return {"error": f"No state found for {run_id}"}
    if st.status == "running":
        return {"error": f"Run {run_id} is still running"}
    # Re-launch with same config
    if cfg is None:
        cfg = DaemonConfig()
    cfg.run_id = run_id
    cfg.state_dir = str(sdir)
    return start(cfg)
