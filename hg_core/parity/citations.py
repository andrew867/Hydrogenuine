"""Claim citation lint — demo hash must not prove integrated behavior (CT-03 PAR)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from hg_core.parity.manifest import PathParityManifest, load_manifest
from hg_core.parity.paths import RUNTIME_PATH_LABELS

HASH_RE = re.compile(r"sha256:[0-9a-f]{64}")
INTEGRATED_CLAIM_RE = re.compile(
    r"\b(phase1_integrated|integrated\s+(?:HAL|SOAR|path|behavior|handler)|"
    r"proves?\s+integrated|HAL/SOAR|GPP\s+permit\s+binding)\b",
    re.IGNORECASE,
)
DEMO_PATH_RE = re.compile(
    r"(?:demo_phase0|\.tmp_\S*demo\S*|rtc\s+phase0\s+demo)",
    re.IGNORECASE,
)
PATH_LABEL_RE = re.compile(
    r"\bpath_id\s*[:=]\s*[`']?(demo_phase0|phase1_integrated|dep_appliance|opt_in_\w+)[`']?",
    re.IGNORECASE,
)
LIMITATION_RE = re.compile(
    r"\b(limitation|not\s+proven|does\s+not\s+prove|stub|absent_in_demo)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CitationFinding:
    file: str
    line: int
    reason_code: str
    detail: str

    def to_payload(self) -> dict[str, str]:
        return {
            "file": self.file,
            "line": str(self.line),
            "reason_code": self.reason_code,
            "detail": self.detail,
        }


def _line_context(lines: list[str], index: int, *, window: int = 2) -> str:
    start = max(0, index - window)
    end = min(len(lines), index + window + 1)
    return "\n".join(lines[start:end])


def _hash_sources(workspace: Path) -> dict[str, str]:
    """Map state_hash -> runtime_path_id from proof bundles."""
    mapping: dict[str, str] = {}
    proofs = workspace / "docs" / "proofs"
    if not proofs.exists():
        return mapping
    for manifest_path in proofs.rglob("manifest.json"):
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        runtime_path = data.get("runtime_path_id")
        gate_result = manifest_path.parent / "gate_result.json"
        if gate_result.exists():
            try:
                gate = json.loads(gate_result.read_text(encoding="utf-8"))
                state_hash = gate.get("state_hash")
                if state_hash and runtime_path:
                    mapping[state_hash] = runtime_path
            except (json.JSONDecodeError, OSError):
                pass
    return mapping


def lint_markdown_file(
    path: Path,
    *,
    manifest: PathParityManifest,
    hash_sources: dict[str, str],
    workspace: Path,
) -> list[CitationFinding]:
    findings: list[CitationFinding] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return [
            CitationFinding(
                file=str(path.relative_to(workspace)),
                line=0,
                reason_code="missing_evidence",
                detail="could not read report file",
            )
        ]
    except UnicodeDecodeError as exc:
        # Fail closed: an undecodable report is a lint finding, never a crash.
        return [
            CitationFinding(
                file=str(path.relative_to(workspace)),
                line=0,
                reason_code="missing_evidence",
                detail=f"report is not valid UTF-8 (byte offset {exc.start}); repair encoding",
            )
        ]
    lines = text.splitlines()
    absent = manifest.absent_in_demo()

    for index, line in enumerate(lines, start=1):
        context = _line_context(lines, index - 1)
        hashes = HASH_RE.findall(line)
        if not hashes:
            continue

        has_path_label = bool(PATH_LABEL_RE.search(context))
        has_limitation = bool(LIMITATION_RE.search(context))
        is_demo_context = bool(DEMO_PATH_RE.search(context))
        integrated_claim = bool(INTEGRATED_CLAIM_RE.search(context))

        for digest in hashes:
            source_path = hash_sources.get(digest)
            demo_sourced = source_path == "demo_phase0" or is_demo_context

            if integrated_claim and demo_sourced and not has_path_label and not has_limitation:
                findings.append(
                    CitationFinding(
                        file=str(path.relative_to(workspace)),
                        line=index,
                        reason_code="demo_hash_as_integrated_claim",
                        detail=f"{digest} cited with integrated claim without path_id label",
                    )
                )

            for subsystem in absent:
                if demo_sourced and subsystem in context and not has_limitation:
                    if re.search(rf"\b{subsystem}\b.*{re.escape(digest)}|{re.escape(digest)}.*\b{subsystem}\b", context, re.I):
                        findings.append(
                            CitationFinding(
                                file=str(path.relative_to(workspace)),
                                line=index,
                                reason_code="absent_in_demo_subsystem_claim",
                                detail=f"{subsystem} cited from demo-sourced hash {digest}",
                            )
                        )
    return findings


def lint_reports(
    workspace: Path,
    *,
    report_globs: Iterable[str] = ("docs/reports/**/*.md",),
    manifest: PathParityManifest | None = None,
) -> dict[str, Any]:
    manifest = manifest or load_manifest(workspace / "config" / "path_parity_manifest_v1.json")
    hash_sources = _hash_sources(workspace)
    findings: list[CitationFinding] = []

    for pattern in report_globs:
        for path in workspace.glob(pattern):
            if "archive" in path.parts:
                continue
            findings.extend(
                lint_markdown_file(path, manifest=manifest, hash_sources=hash_sources, workspace=workspace)
            )

    critical = [f for f in findings if f.reason_code == "demo_hash_as_integrated_claim"]
    return {
        "ok": len(findings) == 0,
        "findings": [f.to_payload() for f in findings],
        "critical_count": len(critical),
        "hash_sources": hash_sources,
        "runtime_path_labels": sorted(RUNTIME_PATH_LABELS),
    }


__all__ = ["CitationFinding", "lint_markdown_file", "lint_reports"]
