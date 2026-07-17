from pathlib import Path
import shutil
import uuid

from hg_core.optional_files import load_skip_posts


def _make_workspace() -> Path:
    root = Path.cwd() / ".tmp_optional_files_tests"
    root.mkdir(parents=True, exist_ok=True)
    ws = root / f"ws_{uuid.uuid4().hex}"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def test_load_skip_posts_creates_default_file():
    ws = _make_workspace()
    try:
        out = load_skip_posts(ws, "automation-moltbook-engage")
        assert out == {"post_ids": []}
        p = ws / "memory" / "automation" / "automation-moltbook-engage" / "skip_posts.json"
        assert p.exists()
    finally:
        shutil.rmtree(ws, ignore_errors=True)
