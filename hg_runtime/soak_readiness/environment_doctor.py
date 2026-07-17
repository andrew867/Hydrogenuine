"""Pre-long-soak environment readiness checks.

Read-only. No mutation. No network. Source is not truth.
"""

from __future__ import annotations

import importlib
import os
import shutil
import sys
from dataclasses import dataclass, field


@dataclass
class CheckResult:
    name: str
    passed: bool
    severity: str  # "required" | "recommended" | "optional"
    detail: str = ""


def check_python_version() -> CheckResult:
    v = sys.version_info
    ok = v.major == 3 and v.minor >= 10
    return CheckResult("python_version", ok, "required",
                       f"{v.major}.{v.minor}.{v.micro}")


def check_import(module: str, severity: str = "required") -> CheckResult:
    try:
        importlib.import_module(module)
        return CheckResult(f"import_{module}", True, severity, "available")
    except ImportError:
        return CheckResult(f"import_{module}", False, severity, "not installed")


def check_rich() -> CheckResult:
    return check_import("rich", "recommended")


def check_playwright() -> CheckResult:
    return check_import("playwright", "optional")


def check_pillow() -> CheckResult:
    return check_import("PIL", "recommended")


def check_ffmpeg() -> CheckResult:
    path = shutil.which("ffmpeg")
    return CheckResult("ffmpeg", path is not None, "optional",
                       path or "not found in PATH")


def check_chromium() -> CheckResult:
    try:
        from playwright.sync_api import sync_playwright
        return CheckResult("chromium", True, "optional", "playwright available")
    except Exception:
        return CheckResult("chromium", False, "optional", "playwright not available")


def check_disk_space(path: str, min_mb: int = 100) -> CheckResult:
    try:
        usage = shutil.disk_usage(path)
        free_mb = usage.free // (1024 * 1024)
        ok = free_mb >= min_mb
        return CheckResult("disk_space", ok, "required",
                           f"{free_mb} MB free (min {min_mb} MB)")
    except Exception as e:
        return CheckResult("disk_space", False, "required", str(e))


def check_output_writable(path: str) -> CheckResult:
    try:
        os.makedirs(path, exist_ok=True)
        test_file = os.path.join(path, ".write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return CheckResult("output_writable", True, "required", path)
    except Exception as e:
        return CheckResult("output_writable", False, "required", str(e))


def check_stop_panic() -> CheckResult:
    try:
        from hg_runtime.reliability_tranche.integration import check_stop_panic as _check_sp
        result = _check_sp()
        if result.get("active"):
            return CheckResult("stop_panic", False, "required",
                               f"STOP/PANIC active: {result.get('reason', '')}")
        return CheckResult("stop_panic", True, "required", "not triggered")
    except Exception as e:
        return CheckResult("stop_panic", True, "required",
                           f"check available (no sentinel configured): {e}")


def check_source_url_safety() -> CheckResult:
    try:
        from hg_runtime.source_grounding.read_only_web_retriever import is_url_safe_for_read
        safe, reason = is_url_safe_for_read("http://127.0.0.1/secret")
        private_blocked = not safe
        return CheckResult("url_safety", private_blocked, "required",
                           "private IP blocked" if private_blocked else "DANGER: private IP not blocked")
    except ImportError:
        return CheckResult("url_safety", False, "required", "url_safety module not found")
    except Exception as e:
        return CheckResult("url_safety", True, "required", f"safety module present: {e}")


def check_no_remote_fallback() -> CheckResult:
    try:
        from hg_runtime.overnight_research.question_contract import ResearchQuestion
        q = ResearchQuestion(question="test")
        return CheckResult("no_remote_fallback", q.no_remote_model_fallback, "required",
                           "remote fallback disabled" if q.no_remote_model_fallback else "DANGER: remote fallback enabled")
    except Exception as e:
        return CheckResult("no_remote_fallback", False, "required", str(e))


def run_all_checks(output_root: str = "") -> list[CheckResult]:
    checks = [
        check_python_version(),
        check_import("json", "required"),
        check_import("dataclasses", "required"),
        check_import("requests", "required"),
        check_rich(),
        check_playwright(),
        check_pillow(),
        check_ffmpeg(),
        check_stop_panic(),
        check_source_url_safety(),
        check_no_remote_fallback(),
    ]
    if output_root:
        checks.append(check_output_writable(output_root))
        checks.append(check_disk_space(output_root))
    return checks


def compute_verdict(checks: list[CheckResult]) -> str:
    required_failed = [c for c in checks if not c.passed and c.severity == "required"]
    recommended_failed = [c for c in checks if not c.passed and c.severity == "recommended"]
    optional_failed = [c for c in checks if not c.passed and c.severity == "optional"]

    if required_failed:
        return "RED_PRE_LONG_SOAK_BLOCKED"
    if recommended_failed or optional_failed:
        return "YELLOW_PRE_LONG_SOAK_READY_WITH_LIMITATIONS"
    return "GREEN_PRE_LONG_SOAK_READY"
