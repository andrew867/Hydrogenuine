"""Runbook documentation lint (CT-15 RUN)."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.operator_runbook.manifest import OperatorRunbookManifest, load_manifest

_CODE_FENCE_RE = re.compile(r"```(?:bash|sh|shell)?\n(.*?)```", re.DOTALL)
_NEGATION_HINTS = ("never", "must not", "do not", "don't", "not ", "no ", "forbidden", "refuses")


def _affirmative_forbidden_phrase(text: str, phrase: str) -> bool:
    lower = text.lower()
    needle = phrase.lower()
    start = 0
    while True:
        idx = lower.find(needle, start)
        if idx < 0:
            return False
        window = lower[max(0, idx - 48) : idx + len(needle) + 48]
        if not any(hint in window for hint in _NEGATION_HINTS):
            return True
        start = idx + len(needle)


@dataclass(frozen=True)
class LintResult:
    ok: bool
    issues: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {"ok": self.ok, "issues": list(self.issues)}


def _extract_commands(doc_text: str) -> list[str]:
    commands: list[str] = []
    for block in _CODE_FENCE_RE.findall(doc_text):
        pending = ""
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if pending:
                pending = f"{pending.rstrip(chr(92)).strip()} {line}"
            else:
                pending = line
            if pending.endswith("\\"):
                continue
            commands.append(pending.replace("\\", "").strip())
            pending = ""
        if pending:
            commands.append(pending.replace("\\", "").strip())
    return commands


def lint_runbook_docs(workspace: Path, manifest: OperatorRunbookManifest | None = None) -> LintResult:
    manifest = manifest or load_manifest(workspace=workspace)
    issues: list[str] = []

    runbook_path = workspace / manifest.runbook_doc
    policy_path = workspace / manifest.break_glass_policy_doc
    for label, path in (("runbook", runbook_path), ("policy", policy_path)):
        if not path.exists():
            issues.append(f"missing_{label}_doc:{path}")
            continue
        text = path.read_text(encoding="utf-8")
        if label == "runbook":
            for section in manifest.required_runbook_sections:
                if section not in text:
                    issues.append(f"missing_section:{section}")
            for procedure in manifest.procedures:
                if procedure.script not in text:
                    issues.append(f"missing_script_ref:{procedure.script}")
        if label == "runbook":
            for phrase in manifest.forbidden_bypass_phrases:
                if _affirmative_forbidden_phrase(text, phrase):
                    issues.append(f"forbidden_phrase:{phrase}")

    for procedure in manifest.procedures:
        script_path = workspace / procedure.script
        if not script_path.exists():
            issues.append(f"missing_script:{procedure.script}")

    if runbook_path.exists():
        commands = _extract_commands(runbook_path.read_text(encoding="utf-8"))
        smoke_cache: dict[str, int] = {}
        for cmd in commands:
            if cmd.startswith("python "):
                argv = cmd.split()
                script = workspace / argv[1]
                if not script.exists():
                    issues.append(f"unsupported_command:{cmd}")
                    continue
                if "scripts/audit/" in argv[1].replace("\\", "/"):
                    continue
                cache_key = argv[1].replace("\\", "/")
                if cache_key in smoke_cache:
                    if smoke_cache[cache_key] != 0:
                        issues.append(f"help_failed:{cmd}")
                    continue
                result = subprocess.run(
                    [sys.executable, str(script), "--help"],
                    cwd=workspace,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=15,
                )
                smoke_cache[cache_key] = result.returncode
                if result.returncode != 0:
                    issues.append(f"help_failed:{cmd}")

    return LintResult(ok=not issues, issues=tuple(issues))


__all__ = ["LintResult", "lint_runbook_docs"]
