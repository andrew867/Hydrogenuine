"""Container entrypoint: wizard, demos, tests — all local, all simulated."""

import os
import subprocess
import sys

HOME = os.environ.get("HG_LEASE_HOME", "/data")

COMMANDS = {
    "wizard": [sys.executable, "-m", "hg_lease.setup_wizard", "--home", HOME],
    "diagnostics": [sys.executable, "-m", "hg_lease.setup_wizard", "--home", HOME, "--diagnostics"],
    "window-demo": [sys.executable, "-m", "hg_lease.demos.window_demo"],
    "instrument-demo": [sys.executable, "-m", "hg_lease.demos.instrument_demo"],
    "test": [sys.executable, "-m", "pytest", "tests/lease", "-q",
             "-p", "no:cacheprovider"],
}


def run(name: str) -> int:
    print(f"==> {name}", flush=True)
    return subprocess.call(COMMANDS[name])


def main() -> int:
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    if target == "all":
        for name in ("wizard", "window-demo", "instrument-demo", "test"):
            code = run(name)
            if code != 0:
                return code
        return 0
    if target not in COMMANDS:
        print(f"unknown command {target!r}; choose from {sorted(COMMANDS)} or 'all'")
        return 2
    return run(target)


if __name__ == "__main__":
    raise SystemExit(main())
