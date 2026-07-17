"""No side-effect modules in extended dry autonomy."""

from __future__ import annotations

from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
PKG = WORKSPACE / "hg_runtime" / "extended_dry_autonomy"

FORBIDDEN = [
    "live_publisher.py",
    "live_sender.py",
    "live_reply.py",
    "live_comment.py",
]


def test_no_live_write_modules():
    for name in FORBIDDEN:
        assert not (PKG / name).is_file()


def test_no_pass_stubs_in_package():
    for py in PKG.glob("*.py"):
        text = py.read_text(encoding="utf-8")
        lines = [ln.strip() for ln in text.splitlines()]
        assert not any(ln == "pass" for ln in lines if not ln.startswith("#"))


def test_no_daemon_cron_service_files():
    root = WORKSPACE / "hg_runtime"
    assert not (root / "live_autonomy").is_dir()
    assert not (root / "bounded_soak" / "overnight_agent.py").is_file()
