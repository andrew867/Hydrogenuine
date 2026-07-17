"""Command classification for workbench test-run modeling."""

from __future__ import annotations

from dataclasses import dataclass

FORBIDDEN_TOKENS = (
    "&&",
    "|",
    ";",
    ">",
    "<",
    "rm ",
    "del ",
    "rmdir ",
    "remove-item",
    "curl ",
    "wget ",
    "ssh ",
    "scp ",
    "pip install",
    "npm install",
    "pnpm install",
    "yarn add",
    "moltbook",
)


@dataclass(frozen=True)
class CommandClassification:
    allowed: bool
    reason: str


def classify_command(command: str) -> CommandClassification:
    lowered = command.strip().lower()
    if not lowered:
        return CommandClassification(False, "empty_command_rejected")
    if any(token in lowered for token in FORBIDDEN_TOKENS):
        if "install" in lowered:
            return CommandClassification(False, "package_install_command_rejected")
        return CommandClassification(False, "forbidden_command_rejected")
    if not lowered.startswith(("python -m pytest ", "pytest ")):
        return CommandClassification(False, "arbitrary_shell_command_rejected")
    return CommandClassification(True, "modeled_test_command_only")


__all__ = ["CommandClassification", "classify_command"]
