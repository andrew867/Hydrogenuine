"""Master timeline link integrity (CT-17 DOC)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
GATE_SCRIPT_RE = re.compile(r"`([a-z0-9_]+_gate\.py)`", re.IGNORECASE)


@dataclass(frozen=True)
class TimelineFinding:
    line: int
    target: str
    detail: str

    def to_payload(self) -> dict[str, Any]:
        return {"line": self.line, "target": self.target, "detail": self.detail}


def check_master_timeline(workspace: Path, timeline_rel: str) -> dict[str, Any]:
    timeline_path = workspace / timeline_rel
    if not timeline_path.exists():
        return {
            "ok": False,
            "timeline": timeline_rel,
            "findings": [{"line": 0, "target": timeline_rel, "detail": "master timeline missing"}],
            "links_checked": 0,
            "gate_scripts_checked": 0,
        }

    text = timeline_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    base = timeline_path.parent
    findings: list[TimelineFinding] = []
    links_checked = 0
    gate_scripts_checked = 0

    for index, line in enumerate(lines, start=1):
        for _label, target in MARKDOWN_LINK_RE.findall(line):
            if target.startswith("http://") or target.startswith("https://"):
                continue
            if target.startswith("#"):
                continue
            links_checked += 1
            resolved = (base / target.split("#", 1)[0]).resolve()
            if not resolved.exists():
                findings.append(
                    TimelineFinding(
                        line=index,
                        target=target,
                        detail=f"broken markdown link: {target}",
                    )
                )
        for script in GATE_SCRIPT_RE.findall(line):
            gate_scripts_checked += 1
            script_path = workspace / "scripts" / "evals" / script
            # Master timeline lists planned gates; only flag scripts that exist partially
            # (broken path) — missing future gates are scheduling targets, not claims.
            if script_path.exists() and not script_path.is_file():
                findings.append(
                    TimelineFinding(
                        line=index,
                        target=script,
                        detail=f"gate script path is not a file: scripts/evals/{script}",
                    )
                )

    return {
        "ok": not findings,
        "timeline": timeline_rel,
        "findings": [f.to_payload() for f in findings],
        "links_checked": links_checked,
        "gate_scripts_checked": gate_scripts_checked,
    }


__all__ = ["check_master_timeline"]
