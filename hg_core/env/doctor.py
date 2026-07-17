"""Environment doctor — baseline checks with redacted output (CT-16 ENV)."""

from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.env.deps import check_python_version, check_required_modules, verify_lockfile
from hg_core.env.manifest import EnvManifest, load_manifest
from hg_core.env.redact import redact_report, snapshot_env


@dataclass(frozen=True)
class DoctorResult:
    ok: bool
    mode: str
    detail: str
    report: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "mode": self.mode,
            "detail": self.detail,
            "report": self.report,
        }


def _classify_os() -> str:
    system = platform.system().lower()
    release = platform.release().lower()
    if system == "windows":
        if "11" in release or "10" in release:
            return "windows-11" if "11" in release else "windows-10"
        return "windows"
    if system == "linux":
        return "ubuntu-22.04"
    return platform.platform()


def _offline_active(manifest: EnvManifest) -> bool:
    return os.environ.get(manifest.offline_env_flag, "").strip().lower() in {"1", "true", "yes", "on"}


def _optional_features(manifest: EnvManifest) -> dict[str, dict[str, str]]:
    features: dict[str, dict[str, str]] = {}
    for spec in manifest.optional_env_vars + manifest.gated_env_vars:
        present = bool(os.environ.get(spec.name, "").strip())
        features[spec.name] = {
            "feature": spec.feature,
            "tier": spec.tier,
            "present": "yes" if present else "no",
            "required_for_baseline": "no",
        }
    return features


def _missing_required_env(manifest: EnvManifest) -> list[str]:
    missing: list[str] = []
    for spec in manifest.required_env_vars:
        if not os.environ.get(spec.name, "").strip():
            missing.append(spec.name)
    return missing


def run_env_doctor(
    workspace: Path,
    *,
    mode: str = "baseline",
    manifest: EnvManifest | None = None,
    extra_required_modules: tuple[str, ...] = (),
) -> DoctorResult:
    manifest = manifest or load_manifest(workspace=workspace)
    mode = mode.strip().lower() or "baseline"
    offline = _offline_active(manifest)

    py_check = check_python_version(min_version=manifest.python_min, max_version=manifest.python_max)
    lock_check = verify_lockfile(
        workspace,
        relative_path=manifest.package_lock_path,
        expected_hash=manifest.package_lock_hash,
    )
    modules = manifest.required_modules + extra_required_modules
    module_check = check_required_modules(modules)
    missing_required_env = _missing_required_env(manifest)

    failures: list[str] = []
    if not py_check.ok:
        failures.append(py_check.detail)
    if not lock_check.ok:
        failures.append(lock_check.detail)
    if not module_check.ok:
        failures.append(module_check.detail)
    if missing_required_env:
        failures.append(f"required_env_missing:{','.join(missing_required_env)}")

    # baseline mode: optional live provider vars must not fail the doctor
    optional = _optional_features(manifest)
    live_missing = [
        name
        for name, meta in optional.items()
        if meta["tier"] == "live" and meta["present"] == "no"
    ]

    os_label = _classify_os()
    os_supported = os_label in manifest.os_dev or os_label in manifest.os_deploy or os_label.startswith("windows")

    env_names = tuple(spec.name for spec in manifest.all_env_vars())
    report = redact_report(
        {
            "schema": "env_doctor_report_v1",
            "mode": mode,
            "offline": offline,
            "manifest_hash": manifest.manifest_hash,
            "python": py_check.to_payload(),
            "lockfile": lock_check.to_payload(),
            "modules": module_check.to_payload(),
            "platform": {
                "os": os_label,
                "os_supported": os_supported,
                "platform": platform.platform(),
                "timezone_declared": manifest.timezone,
            },
            "optional_features": optional,
            "live_features_missing": live_missing,
            "env_snapshot": snapshot_env(env_names),
            "failures": failures,
        }
    )

    if mode == "baseline":
        ok = not failures
        detail = "baseline_ok" if ok else failures[0]
    else:
        ok = not failures
        detail = "ok" if ok else failures[0]

    return DoctorResult(ok=ok, mode=mode, detail=detail, report=report)


__all__ = ["DoctorResult", "run_env_doctor"]
