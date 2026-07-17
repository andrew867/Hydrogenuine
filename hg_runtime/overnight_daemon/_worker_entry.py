"""Worker entry point — launched as a detached subprocess by daemon.py.

Receives the state directory path, loads config, runs the supervisor loop.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.overnight_daemon.config import DaemonConfig
from hg_runtime.overnight_daemon.supervisor import run_daemon


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: _worker_entry.py <state_dir>", file=sys.stderr)
        return 1

    state_dir = Path(sys.argv[1])
    config_path = state_dir / "daemon_config.json"
    if not config_path.exists():
        print(f"No config at {config_path}", file=sys.stderr)
        return 1

    d = json.loads(config_path.read_text(encoding="utf-8"))
    cfg = DaemonConfig()
    for k, v in d.items():
        if hasattr(cfg, k) and v != "REDACTED":
            setattr(cfg, k, v)
    cfg.state_dir = str(state_dir)

    return run_daemon(cfg)


if __name__ == "__main__":
    raise SystemExit(main())
