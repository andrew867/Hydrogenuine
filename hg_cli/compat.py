"""Compatibility entry points for pre-0.2 public commands."""

from __future__ import annotations

from hg_cli.cli import main


def setup_main() -> int:
    print("'hg-setup' now opens the Community first-run wizard. The preferred command is: hg init")
    return main(["init"])
