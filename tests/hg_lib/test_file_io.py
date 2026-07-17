from pathlib import Path
import shutil
import uuid

from hg_lib.file_io import read_json, read_text, write_json, write_text


def _make_workspace() -> Path:
    root = Path.cwd() / ".tmp_file_io_tests"
    root.mkdir(parents=True, exist_ok=True)
    ws = root / f"ws_{uuid.uuid4().hex}"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def test_read_text_create_if_missing():
    ws = _make_workspace()
    try:
        p = ws / "a" / "b" / "note.txt"
        out = read_text(p, default="hello", create_if_missing=True)
        assert out == "hello"
        assert p.exists()
        assert p.read_text(encoding="utf-8") == "hello"
    finally:
        shutil.rmtree(ws, ignore_errors=True)


def test_read_json_create_if_missing():
    ws = _make_workspace()
    try:
        p = ws / "x" / "state.json"
        out = read_json(p, default={"ok": True}, create_if_missing=True)
        assert out == {"ok": True}
        assert p.exists()
    finally:
        shutil.rmtree(ws, ignore_errors=True)


def test_write_helpers_create_parent():
    ws = _make_workspace()
    try:
        t = ws / "nested" / "f.txt"
        j = ws / "nested" / "f.json"
        write_text(t, "abc")
        write_json(j, {"x": 1})
        assert t.exists()
        assert j.exists()
        assert read_json(j, default={}) == {"x": 1}
    finally:
        shutil.rmtree(ws, ignore_errors=True)
