"""
Pack 5: hg-ledger CLI — verify chain, keygen (dev/demo only).
Usage: hg-ledger verify [workspace_root]
       hg-ledger keygen  (only when HG_ENV=dev or HG_LEDGER_KEYGEN_ALLOWED=1)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .ledger_verify import verify_chain
from . import crypto


def _workspace_root(args: list[str]) -> Path:
    if args and args[0]:
        return Path(args[0]).resolve()
    try:
        from hg_lib.config import get_workspace_root
        return Path(get_workspace_root())
    except ImportError:
        return Path.cwd()


def cmd_verify(workspace: Path) -> int:
    report = verify_chain(workspace)
    if report.get("ok"):
        print("Ledger verify OK. Checked %d events." % report.get("checked", 0))
        return 0
    print("Ledger verify FAILED.", file=sys.stderr)
    for err in report.get("errors", [])[:20]:
        print("  ", err, file=sys.stderr)
    return 1


def cmd_keygen() -> int:
    if os.environ.get("HG_ENV", "").strip().lower() not in ("dev", "demo"):
        if os.environ.get("HG_LEDGER_KEYGEN_ALLOWED", "").strip().lower() not in ("1", "true", "yes"):
            print("hg-ledger keygen is only allowed in dev/demo (set HG_ENV=dev or HG_LEDGER_KEYGEN_ALLOWED=1).", file=sys.stderr)
            return 1
    try:
        sk, pk = crypto.generate_keypair()
        print("SECRET_KEY (hex):", sk)
        print("PUBLIC_KEY (hex):", pk)
        print("Store secret key securely; use for signing in dev/demo only. Rotate for production.")
        return 0
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 1


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print("Usage: hg-ledger verify [workspace_root]")
        print("       hg-ledger keygen   (dev/demo only)")
        return 0 if argv and argv[0] in ("-h", "--help") else 2
    sub = argv[0].lower()
    if sub == "verify":
        workspace = _workspace_root(argv[1:])
        return cmd_verify(workspace)
    if sub == "keygen":
        return cmd_keygen()
    print("Unknown subcommand: %s" % sub, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
