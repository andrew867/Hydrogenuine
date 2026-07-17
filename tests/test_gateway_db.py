import shutil
import uuid
from pathlib import Path

from hg_gateway.db import get_connection


def test_get_connection_creates_nested_db_path():
    root = Path.cwd() / ".codex_tmp" / "testdata" / f"gateway_db_{uuid.uuid4().hex}"
    db_path = root / "nested" / "gateway.sqlite3"
    try:
        with get_connection(str(db_path)) as conn:
            row = conn.execute("select 1 as ok").fetchone()
            assert row["ok"] == 1
        assert db_path.exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)
