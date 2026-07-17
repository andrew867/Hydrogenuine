"""TruthGateReport builder and bundle sealing (CT-04 OBT)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TruthGateReport:
    schema: str = "truth_gate_report_v1"
    head: str = "unknown"
    path_ids: list[str] = field(default_factory=list)
    fast_subset: bool = False
    allow_dirty: bool = False
    dirty_files: list[str] = field(default_factory=list)
    stages: list[dict[str, Any]] = field(default_factory=list)
    gate_results: list[dict[str, Any]] = field(default_factory=list)
    subsystem_classification: list[dict[str, Any]] = field(default_factory=list)
    skips: list[dict[str, str]] = field(default_factory=list)
    post_ct_excluded: list[dict[str, str]] = field(default_factory=list)
    strict_ct_mode: bool = False
    verdict: str = "red"
    bundle_hash: str = ""
    registry_hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "head": self.head,
            "path_ids": self.path_ids,
            "fast_subset": self.fast_subset,
            "allow_dirty": self.allow_dirty,
            "dirty_files": self.dirty_files,
            "stages": self.stages,
            "gate_results": self.gate_results,
            "subsystem_classification": self.subsystem_classification,
            "skips": self.skips,
            "post_ct_excluded": self.post_ct_excluded,
            "strict_ct_mode": self.strict_ct_mode,
            "verdict": self.verdict,
            "bundle_hash": self.bundle_hash,
            "registry_hash": self.registry_hash,
        }


def seal_bundle_hash(proof_dir: Path) -> str:
    """Hash all bundle files except manifest.json (written last)."""
    parts: list[str] = []
    for path in sorted(proof_dir.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        rel = path.relative_to(proof_dir).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        parts.append(f"{rel}:{digest}")
    combined = "\n".join(parts)
    return f"sha256:{hashlib.sha256(combined.encode('utf-8')).hexdigest()}"


def build_report(
    *,
    head: str,
    path_ids: list[str],
    stages: list[dict[str, Any]],
    gate_results: list[dict[str, Any]],
    subsystem_classification: list[dict[str, Any]],
    skips: list[dict[str, str]],
    fast_subset: bool,
    allow_dirty: bool,
    dirty_files: list[str],
    registry_hash: str,
    critical_failures: list[str],
    strict_ct_mode: bool = False,
    post_ct_excluded: list[dict[str, str]] | None = None,
) -> TruthGateReport:
    report = TruthGateReport(
        head=head,
        path_ids=path_ids,
        fast_subset=fast_subset,
        allow_dirty=allow_dirty,
        dirty_files=dirty_files,
        stages=stages,
        gate_results=gate_results,
        subsystem_classification=subsystem_classification,
        skips=skips,
        post_ct_excluded=post_ct_excluded or [],
        strict_ct_mode=strict_ct_mode,
        registry_hash=registry_hash,
    )
    if critical_failures:
        report.verdict = "red"
    elif fast_subset:
        report.verdict = "green_fast" if not critical_failures and not any(
            g.get("verdict") == "fail" for g in gate_results if g.get("critical")
        ) else "red"
    elif skips and not strict_ct_mode:
        report.verdict = "green_with_skips"
    elif skips and strict_ct_mode:
        report.verdict = "red"
    else:
        report.verdict = "green"
    return report


def write_report_files(proof_dir: Path, report: TruthGateReport) -> None:
    payload = report.to_payload()
    (proof_dir / "truth_gate_report.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    gate_summary = {
        "gate": "hg_full_truth_v1",
        "pack": "CT-04",
        "ok": report.verdict in {"green", "green_with_skips", "green_fast"},
        "verdict": report.verdict,
        "stages": report.stages,
        "gate_results": report.gate_results,
        "skips": report.skips,
        "head": report.head,
    }
    (proof_dir / "gate_result.json").write_text(json.dumps(gate_summary, indent=2, sort_keys=True), encoding="utf-8")
    (proof_dir / "artifacts" / "gate_summary.json").write_text(
        json.dumps(gate_summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )


__all__ = ["TruthGateReport", "build_report", "seal_bundle_hash", "write_report_files"]
