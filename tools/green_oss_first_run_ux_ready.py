"""Readiness gate for the public Hydrogenuine Community first-run path."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    "INSTALL.md",
    "CONFIGURATION.md",
    "TROUBLESHOOTING.md",
    "docs/community/quickstart.md",
    "docs/community/multi_chat.md",
    "docs/reports/oss_first_run_ux/ISSUE_REPRODUCTION.md",
    "docs/reports/oss_first_run_ux/FIX_PLAN.md",
    "docs/reports/oss_first_run_ux/IMPLEMENTATION_REPORT.md",
    "docs/reports/oss_first_run_ux/TEST_REPORT.md",
    "docs/reports/oss_first_run_ux/PUBLIC_DOCS_REVIEW.md",
    "hg_cli/cli.py",
    "hg_cli/config.py",
    "tests/test_oss_first_run_cli.py",
    "tests/test_oss_first_run_gateway.py",
]
PUBLIC_DOCS = [
    "README.md",
    "INSTALL.md",
    "CONFIGURATION.md",
    "TROUBLESHOOTING.md",
    "docs/community/quickstart.md",
    "docs/community/multi_chat.md",
]
TESTS = [
    "tests/test_oss_first_run_cli.py",
    "tests/test_oss_first_run_gateway.py",
    "tests/test_community_backend_acceptance.py",
    "tests/test_community_redteam.py",
    "tests/test_public_packaging_docs.py",
    "tests/test_gateway_runtime_config.py",
    "tests/test_gateway_runtime_safety.py",
    "tests/test_gateway_llm_fallback.py",
    "tests/test_llm_defaults.py",
]


def check(condition: bool, label: str, failures: list[str]) -> None:
    print(f"{'PASS' if condition else 'FAIL'} {label}")
    if not condition:
        failures.append(label)


def run() -> int:
    failures: list[str] = []
    check(all((ROOT / path).exists() for path in REQUIRED), "required first-run files and reports exist", failures)

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    check('hg = "hg_cli.cli:main"' in pyproject, "unified hg command is packaged", failures)
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    check("HG_GATEWAY_AUTH_MODE=local-no-key" in env_example, "native no-key mode is explicit", failures)
    check("HG_GATEWAY_API_KEY=" not in env_example, "native demo config requires no gateway key", failures)
    check("HG_GATEWAY_STORE=sqlite" in env_example, "native chat store is persistent", failures)

    app_js = (ROOT / "community_ui" / "app.js").read_text(encoding="utf-8")
    check("saved local access token does not match" in app_js, "UI distinguishes local transport access from provider keys", failures)
    check('el("api-status").textContent = error.message.includes' in app_js, "UI does not collapse every auth error into API offline", failures)

    docs_text = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in PUBLIC_DOCS)
    check("Artificial Governed Intelligence" in docs_text, "public terminology uses Artificial Governed Intelligence", failures)
    check("Artificial General Intelligence" not in docs_text, "public docs do not use Artificial General Intelligence wording", failures)
    unsafe_claim_lines = []
    for path in PUBLIC_DOCS:
        for number, line in enumerate((ROOT / path).read_text(encoding="utf-8").splitlines(), 1):
            lower = line.lower()
            if any(phrase in lower for phrase in ("production-ready", "enterprise-ready", "compliance guaranteed", "formally verified")):
                if not any(boundary in lower for boundary in ("not ", "no ", "does not", "is not")):
                    unsafe_claim_lines.append(f"{path}:{number}")
    check(not unsafe_claim_lines, "public docs contain no unbounded readiness or compliance claims", failures)

    secret_targets = ["hg_cli/config.py", "hg_cli/cli.py", ".env.example", "README.md", "CONFIGURATION.md"]
    secret_text = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in secret_targets)
    check(re.search(r"sk-[A-Za-z0-9_-]{20,}", secret_text) is None, "first-run surface contains no secret-shaped values", failures)

    basetemp = ROOT / ".pytest-tmp-oss-first-run-gate"
    command = [sys.executable, "-m", "pytest", *TESTS, "-q", "--basetemp", str(basetemp)]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if completed.stdout:
        print(completed.stdout.rstrip())
    if completed.stderr:
        print(completed.stderr.rstrip())
    check(completed.returncode == 0, "expanded first-run, gateway, provider, acceptance, red-team, and docs tests pass", failures)

    if failures:
        print("RED_OSS_FIRST_RUN_UX_NOT_READY")
        for failure in failures:
            print(f"BLOCKER {failure}")
        return 1
    print("GREEN_OSS_FIRST_RUN_UX_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
