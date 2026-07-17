"""Clean-run dependency and environment doctor.

Checks whether a fresh checkout can run demos, tests, and overnight research.
Reproducibility check is not production readiness. No promotion.
"""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class DoctorCheck:
    name: str
    passed: bool
    severity: str  # "required" | "recommended" | "optional"
    detail: str = ""


def check_python_version() -> DoctorCheck:
    v = sys.version_info
    ok = v.major == 3 and v.minor >= 10
    return DoctorCheck("python_version", ok, "required",
                       f"{v.major}.{v.minor}.{v.micro}")


def check_import(module: str, severity: str = "required") -> DoctorCheck:
    try:
        importlib.import_module(module)
        return DoctorCheck(f"import_{module}", True, severity, "available")
    except ImportError:
        return DoctorCheck(f"import_{module}", False, severity, "not installed")


def check_binary(name: str, severity: str = "optional") -> DoctorCheck:
    path = shutil.which(name)
    return DoctorCheck(f"binary_{name}", path is not None, severity,
                       path or "not found in PATH")


def check_proof_root_writable(path: str) -> DoctorCheck:
    try:
        os.makedirs(path, exist_ok=True)
        test_file = os.path.join(path, ".write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return DoctorCheck("proof_root_writable", True, "required", path)
    except Exception as e:
        return DoctorCheck("proof_root_writable", False, "required", str(e))


def check_no_secrets_in_dir(path: str) -> DoctorCheck:
    secret_patterns = [".env", "credentials", "api_key", "secret", "token"]
    issues = []
    if os.path.isdir(path):
        for fname in os.listdir(path):
            lower = fname.lower()
            for pattern in secret_patterns:
                if pattern in lower and not fname.endswith(".example"):
                    issues.append(fname)
    if issues:
        return DoctorCheck("no_secrets", False, "required",
                           f"potential secrets: {issues[:3]}")
    return DoctorCheck("no_secrets", True, "required", "no obvious secrets found")


def check_git_state() -> DoctorCheck:
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL, timeout=5
        ).decode().strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"],
            stderr=subprocess.DEVNULL, timeout=5
        ).decode().strip()
        status = "clean" if not dirty else "dirty"
        return DoctorCheck("git_state", True, "recommended",
                           f"SHA={sha}, status={status}")
    except Exception:
        return DoctorCheck("git_state", False, "recommended", "git not available")


def check_local_endpoint(endpoint: str = "http://localhost:1234",
                         timeout: int = 3) -> DoctorCheck:
    try:
        import urllib.request
        req = urllib.request.Request(f"{endpoint}/v1/models", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return DoctorCheck("local_endpoint", True, "optional",
                               f"{endpoint} reachable (HTTP {resp.status})")
    except Exception as e:
        return DoctorCheck("local_endpoint", False, "optional",
                           f"{endpoint}: {str(e)[:80]}")


def run_all_checks(*, proof_root: str = "", check_endpoint: bool = False,
                   endpoint: str = "http://localhost:1234") -> list[DoctorCheck]:
    checks = [
        check_python_version(),
        check_import("json", "required"),
        check_import("dataclasses", "required"),
        check_import("requests", "required"),
        check_import("rich", "recommended"),
        check_import("PIL", "recommended"),
        check_import("playwright", "optional"),
        check_binary("ffmpeg", "optional"),
        check_binary("chromium", "optional"),
        check_git_state(),
    ]
    if proof_root:
        checks.append(check_proof_root_writable(proof_root))
        checks.append(check_no_secrets_in_dir(proof_root))
    if check_endpoint:
        checks.append(check_local_endpoint(endpoint))
    return checks


def compute_verdict(checks: list[DoctorCheck]) -> str:
    required_failed = [c for c in checks if not c.passed and c.severity == "required"]
    recommended_failed = [c for c in checks if not c.passed and c.severity == "recommended"]
    optional_failed = [c for c in checks if not c.passed and c.severity == "optional"]

    if required_failed:
        return "RED_CLEAN_RUN_BLOCKED"
    if recommended_failed or optional_failed:
        return "YELLOW_CLEAN_RUN_READY_WITH_LIMITATIONS"
    return "GREEN_CLEAN_RUN_READY"
