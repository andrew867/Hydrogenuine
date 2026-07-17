"""CT proof bundle command_log.jsonl schema and validation."""

from __future__ import annotations

import hashlib
import json
import re

# re used by validate_ct_gate_bundles timestamp filter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = ("argv", "exit_code")
RECOMMENDED_FIELDS = ("cwd", "duration_s")
SECRET_PATTERNS = (
    re.compile(r"sk-[a-zA-Z0-9]{10,}"),
    re.compile(r"(?i)(api[_-]?key|token|password)\s*[:=]\s*\S+"),
)


@dataclass(frozen=True)
class CommandLogFinding:
    line: int
    check: str
    detail: str

    def to_payload(self) -> dict[str, str]:
        return {"line": str(self.line), "check": self.check, "detail": self.detail}


def _sha256_text(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def record_command(
    log_path: Path,
    *,
    argv: list[str],
    cwd: Path | str,
    exit_code: int,
    duration_s: float,
    stdout: str = "",
    stderr: str = "",
    timeout: bool = False,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "argv": argv,
        "cwd": str(cwd),
        "exit_code": exit_code,
        "duration_s": round(duration_s, 3),
        "stdout_digest": _sha256_text(stdout),
        "stderr_digest": _sha256_text(stderr),
    }
    if timeout:
        entry["timeout"] = True
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def validate_command_log(log_path: Path) -> tuple[bool, list[CommandLogFinding]]:
    findings: list[CommandLogFinding] = []
    if not log_path.exists():
        return False, [CommandLogFinding(0, "missing", "command_log.jsonl absent")]
    if log_path.stat().st_size == 0:
        return False, [CommandLogFinding(0, "empty", "command_log.jsonl is empty")]
    lines = log_path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            findings.append(CommandLogFinding(index, "parse", str(exc)))
            continue
        if not isinstance(entry, dict):
            findings.append(CommandLogFinding(index, "shape", "entry must be object"))
            continue
        missing = [f for f in REQUIRED_FIELDS if f not in entry]
        if missing:
            findings.append(CommandLogFinding(index, "schema", f"missing fields: {missing}"))
        raw = line.lower()
        for pattern in SECRET_PATTERNS:
            if pattern.search(raw):
                findings.append(CommandLogFinding(index, "secret_leak", "possible secret in command log line"))
                break
    return not findings, findings


def validate_ct_gate_scripts(workspace: Path) -> dict[str, Any]:
    from hg_core.truth.registry import load_registry

    registry = load_registry(workspace / "config" / "truth_gate_registry.yaml")
    missing: list[str] = []
    for gate in registry.gates:
        if gate.gate_id == "hg_full_truth":
            continue
        if not (gate.pack.startswith("CT-") or gate.pack == "CT-V1"):
            continue
        script = workspace / gate.script
        if not script.exists():
            missing.append(f"{gate.script} (missing file)")
            continue
        text = script.read_text(encoding="utf-8")
        if "command_log" not in text:
            missing.append(gate.script)
    return {"ok": not missing, "missing": missing}


def validate_ct_gate_bundles(workspace: Path, *, packs: tuple[str, ...] | None = None) -> dict[str, Any]:
    proofs_root = workspace / "docs" / "proofs" / "connective_tissue"
    ts_re = re.compile(r"^\d{8}T\d{6}Z$")
    pack_names = packs or tuple(
        p.name for p in sorted(proofs_root.iterdir()) if p.is_dir() and p.name.startswith("pack")
    )
    results: list[dict[str, Any]] = []
    for pack in pack_names:
        pack_dir = proofs_root / pack
        bundles = (
            sorted(p for p in pack_dir.iterdir() if p.is_dir() and ts_re.match(p.name))
            if pack_dir.exists()
            else []
        )
        if not bundles:
            results.append({"pack": pack, "ok": False, "detail": "no bundles"})
            continue
        latest = bundles[-1]
        log_path = latest / "command_log.jsonl"
        ok, findings = validate_command_log(log_path)
        results.append(
            {
                "pack": pack,
                "bundle": str(latest.relative_to(workspace)).replace("\\", "/"),
                "ok": ok,
                "findings": [f.to_payload() for f in findings],
            }
        )
    return {
        "ok": all(r["ok"] for r in results),
        "packs_checked": len(results),
        "results": results,
    }


__all__ = [
    "CommandLogFinding",
    "record_command",
    "validate_command_log",
    "validate_ct_gate_bundles",
    "validate_ct_gate_scripts",
]
