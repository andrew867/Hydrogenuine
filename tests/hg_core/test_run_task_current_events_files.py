import shutil
import uuid
from pathlib import Path

from hg_core.run_task import _ensure_current_events_files


def _make_workspace() -> Path:
    root = Path.cwd() / ".tmp_run_task_tests"
    root.mkdir(parents=True, exist_ok=True)
    ws = root / f"ws_{uuid.uuid4().hex}"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def test_ensure_current_events_files_creates_brief_and_legacy():
    workspace = _make_workspace()
    try:
        _ensure_current_events_files(workspace)

        current_events_dir = workspace / "knowledge" / "current_events"
        assert current_events_dir.exists()

        brief_files = list(current_events_dir.glob("brief-*.md"))
        legacy_files = [p for p in current_events_dir.glob("*.md") if not p.name.startswith("brief-")]
        assert len(brief_files) >= 2
        assert len(legacy_files) >= 2

        sample = brief_files[0].read_text(encoding="utf-8")
        assert "Current Events Brief" in sample
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
