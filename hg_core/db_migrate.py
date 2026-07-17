"""
Pack 6: DB migration CLI — upgrade gateway (and document operator).
Usage: python -m hg_core.db_migrate upgrade [gateway_db_path]
       python -m hg_core.db_migrate stamp  (adopt existing DB; no-op for gateway)
Gateway uses versioned _migrate in hg_gateway.db; this module triggers it.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _gateway_upgrade(db_path: str | None) -> int:
    if db_path is None:
        db_path = os.environ.get("HG_GATEWAY_DB_PATH", "./memory/gateway.sqlite3")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    from hg_gateway.db import get_connection
    with get_connection(db_path) as conn:
        cur = conn.execute("SELECT MAX(version) AS v FROM _schema_version")
        row = cur.fetchone()
        version = row[0] if row and row[0] is not None else 0
    print("Gateway DB at %s: schema version %s" % (db_path, version))
    return 0


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print("Usage: python -m hg_core.db_migrate upgrade [gateway_db_path]")
        print("       python -m hg_core.db_migrate stamp [gateway_db_path]")
        print("Runs gateway migrations (versioned _migrate). Set HG_GATEWAY_DB_PATH for path.")
        return 0 if argv and argv[0] in ("-h", "--help") else 2
    sub = argv[0].lower()
    path = argv[1] if len(argv) > 1 else None
    if sub == "upgrade":
        return _gateway_upgrade(path)
    if sub == "stamp":
        return _gateway_upgrade(path)
    print("Unknown subcommand: %s" % sub, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
