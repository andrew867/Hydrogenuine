"""Deterministic gate-integrity checks for CT-A (no silent skips, no fake green)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.ct_crosspack.harness import run_all_crosspack_checks
from hg_core.gate_integrity.obt import (
    TS_RE,
    find_obt_default_skip_bundle,
    find_obt_strict_green_bundle,
    load_truth_report,
)
from hg_core.proof.command_log import (
    validate_command_log,
    validate_ct_gate_bundles,
    validate_ct_gate_scripts,
)
from hg_core.truth.registry import load_registry
from hg_core.truth.report import build_report


@dataclass(frozen=True)
class IntegrityCheck:
    check_id: str
    ok: bool
    detail: str
    critical: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "ok": self.ok,
            "detail": self.detail,
            "critical": self.critical,
        }


def validate_truth_report_integrity(report: dict[str, Any]) -> list[IntegrityCheck]:
    """Fail closed when verdicts disagree with skip/critical evidence."""
    checks: list[IntegrityCheck] = []
    verdict = str(report.get("verdict", "red"))
    skips = list(report.get("skips") or [])
    critical = list(report.get("critical_failures") or [])
    strict_ct = bool(report.get("strict_ct_mode"))

    if verdict == "green" and skips:
        checks.append(
            IntegrityCheck(
                "no_green_with_skips",
                False,
                f"verdict green but {len(skips)} skips recorded",
            )
        )
    else:
        checks.append(IntegrityCheck("no_green_with_skips", True, f"verdict={verdict}, skips={len(skips)}"))

    if strict_ct and skips:
        checks.append(
            IntegrityCheck(
                "strict_ct_zero_skips",
                False,
                f"strict CT mode recorded {len(skips)} skips",
            )
        )
    else:
        checks.append(
            IntegrityCheck(
                "strict_ct_zero_skips",
                True,
                "strict CT has zero skips" if strict_ct else "not strict CT mode",
            )
        )

    if verdict == "green" and critical:
        checks.append(
            IntegrityCheck(
                "no_green_with_critical_failures",
                False,
                f"critical_failures={critical}",
            )
        )
    else:
        checks.append(
            IntegrityCheck(
                "no_green_with_critical_failures",
                True,
                f"critical_failures={len(critical)}",
            )
        )

    deferred = [
        g
        for g in report.get("gate_results") or []
        if str(g.get("verdict", "")).startswith("skipped")
    ]
    if deferred and not skips and not strict_ct:
        checks.append(
            IntegrityCheck(
                "deferred_gates_enumerated",
                False,
                f"{len(deferred)} skipped gates without skip list",
            )
        )
    else:
        checks.append(
            IntegrityCheck(
                "deferred_gates_enumerated",
                True,
                f"deferred={len(deferred)}, skips={len(skips)}",
            )
        )

    return checks


def _latest_timestamp_bundle(pack_dir: Path) -> Path | None:
    bundles = _sorted_bundles(pack_dir)
    return bundles[-1] if bundles else None


def _find_gate_ok_bundle(pack_dir: Path) -> Path | None:
    """Latest bundle with non-empty valid command_log (skip in-progress empty logs)."""
    for bundle in reversed(_sorted_bundles(pack_dir)):
        log_path = bundle / "command_log.jsonl"
        if not log_path.is_file() or log_path.stat().st_size == 0:
            continue
        ok, _ = validate_command_log(log_path)
        if ok:
            return bundle
        gate_result = bundle / "gate_result.json"
        if gate_result.is_file():
            try:
                payload = json.loads(gate_result.read_text(encoding="utf-8"))
                if isinstance(payload, dict) and payload.get("ok"):
                    return bundle
            except json.JSONDecodeError:
                continue
    return None


def _sorted_bundles(pack_dir: Path) -> list[Path]:
    if not pack_dir.is_dir():
        return []
    return sorted(p for p in pack_dir.iterdir() if p.is_dir() and TS_RE.match(p.name))


def _load_latest_obt_report(workspace: Path) -> dict[str, Any] | None:
    bundle = _latest_timestamp_bundle(workspace / "docs" / "proofs" / "connective_tissue" / "pack04")
    if bundle is None:
        return None
    return load_truth_report(bundle)


def run_ct_gate_integrity_checks(workspace: Path) -> dict[str, Any]:
    """Run structural CT-A integrity checks without invoking full OBT."""
    checks: list[IntegrityCheck] = []

    registry = load_registry(workspace / "config" / "truth_gate_registry.yaml")
    orphans = registry.orphan_scripts(workspace / "scripts" / "evals")
    checks.append(
        IntegrityCheck(
            "eval_scripts_no_orphans",
            not orphans,
            f"orphans={orphans}" if orphans else "registry complete",
        )
    )

    ct_required = [g for g in registry.gates if g.is_ct_required()]
    checks.append(
        IntegrityCheck(
            "ct_required_gates_registered",
            len(ct_required) >= 19,
            f"count={len(ct_required)}",
        )
    )

    final_audit = registry.gate_by_id("ct_v1_final_audit")
    if final_audit is None:
        checks.append(IntegrityCheck("final_audit_self_hosting", False, "ct_v1_final_audit missing"))
    else:
        self_hosts = not final_audit.should_run(fast=False, include_all=False, strict_ct=True)
        checks.append(
            IntegrityCheck(
                "final_audit_self_hosting",
                self_hosts,
                "excluded from OBT strict invocation",
            )
        )

    crosspack = run_all_crosspack_checks(workspace)
    checks.append(
        IntegrityCheck(
            "ct_x1_x5_harness",
            bool(crosspack.get("ok")),
            f"checks={len(crosspack.get('checks', []))}",
        )
    )

    script_scan = validate_ct_gate_scripts(workspace)
    checks.append(
        IntegrityCheck(
            "ct_gate_scripts_command_log",
            bool(script_scan.get("ok")),
            str(script_scan.get("missing", [])),
        )
    )

    bundle_scan = validate_ct_gate_bundles(
        workspace,
        packs=tuple(f"pack{n:02d}" for n in range(1, 18)),
    )
    fresh_ok = all(
        r["ok"]
        for r in bundle_scan.get("results", [])
        if r.get("bundle") and "command_log_" not in str(r.get("bundle", ""))
    )
    checks.append(
        IntegrityCheck(
            "ct_pack_bundles_command_log",
            fresh_ok,
            f"packs_checked={bundle_scan.get('packs_checked', 0)}",
            critical=False,
        )
    )

    for label, rel in (("ct_x", "docs/proofs/connective_tissue/CT-X"), ("ct_a", "docs/proofs/connective_tissue/CT-A")):
        bundle = _find_gate_ok_bundle(workspace / rel)
        if bundle is None:
            checks.append(IntegrityCheck(f"{label}_bundle_command_log", False, "no bundle", critical=False))
            continue
        log_ok, findings = validate_command_log(bundle / "command_log.jsonl")
        checks.append(
            IntegrityCheck(
                f"{label}_bundle_command_log",
                log_ok,
                findings[0].detail if findings else bundle.name,
                critical=True,
            )
        )

    pack04 = workspace / "docs" / "proofs" / "connective_tissue" / "pack04"
    strict_bundle = find_obt_strict_green_bundle(pack04)
    if strict_bundle is None:
        checks.append(
            IntegrityCheck("obt_strict_ct_green_bundle", False, "no strict CT green bundle on disk")
        )
    else:
        strict_report = load_truth_report(strict_bundle)
        assert strict_report is not None
        checks.append(
            IntegrityCheck(
                "obt_strict_ct_green_bundle",
                strict_report.get("verdict") == "green" and not strict_report.get("skips"),
                f"bundle={strict_bundle.name}, skips={len(strict_report.get('skips') or [])}",
            )
        )
        log_ok, findings = validate_command_log(strict_bundle / "command_log.jsonl")
        checks.append(
            IntegrityCheck(
                "obt_strict_command_log",
                log_ok,
                findings[0].detail if findings else strict_bundle.name,
            )
        )
        checks.extend(validate_truth_report_integrity(strict_report))

    default_bundle = find_obt_default_skip_bundle(pack04)
    if default_bundle is None:
        checks.append(
            IntegrityCheck(
                "default_mode_skips_enumerated",
                True,
                "no default-mode skip bundle on disk (optional evidence)",
                critical=False,
            )
        )
    else:
        default_report = load_truth_report(default_bundle)
        assert default_report is not None
        default_checks = validate_truth_report_integrity(default_report)
        checks.append(
            IntegrityCheck(
                "default_mode_skips_enumerated",
                all(c.ok for c in default_checks),
                f"bundle={default_bundle.name}, verdict={default_report.get('verdict')}",
            )
        )

    obt_bundle = strict_bundle or _latest_timestamp_bundle(pack04)

    synthetic_strict = build_report(
        head="synthetic",
        path_ids=["connective_tissue/pack04"],
        stages=[],
        gate_results=[],
        subsystem_classification=[],
        skips=[{"gate_id": "demo", "reason": "deferred_default_mode"}],
        fast_subset=False,
        allow_dirty=False,
        dirty_files=[],
        registry_hash="sha256:" + "0" * 64,
        critical_failures=[],
        strict_ct_mode=True,
    )
    checks.append(
        IntegrityCheck(
            "synthetic_strict_skips_fail_closed",
            synthetic_strict.verdict == "red",
            f"verdict={synthetic_strict.verdict}",
        )
    )

    synthetic_default = build_report(
        head="synthetic",
        path_ids=["connective_tissue/pack04"],
        stages=[],
        gate_results=[],
        subsystem_classification=[],
        skips=[{"gate_id": "demo", "reason": "deferred_default_mode"}],
        fast_subset=False,
        allow_dirty=False,
        dirty_files=[],
        registry_hash="sha256:" + "0" * 64,
        critical_failures=[],
        strict_ct_mode=False,
    )
    checks.append(
        IntegrityCheck(
            "synthetic_default_skips_not_plain_green",
            synthetic_default.verdict == "green_with_skips",
            f"verdict={synthetic_default.verdict}",
        )
    )

    obt_report = load_truth_report(obt_bundle) if obt_bundle else None
    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
        "crosspack": crosspack,
        "obt_strict_bundle": str(strict_bundle.relative_to(workspace)).replace("\\", "/") if strict_bundle else None,
        "obt_default_bundle": str(default_bundle.relative_to(workspace)).replace("\\", "/") if default_bundle else None,
        "obt_report_verdict": obt_report.get("verdict") if obt_report else None,
        "command_log_bundle_scan": bundle_scan,
    }


__all__ = [
    "IntegrityCheck",
    "run_ct_gate_integrity_checks",
    "validate_truth_report_integrity",
]
