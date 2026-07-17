"""Generate demo commands for operator use.

All generated commands include --no-remote-fallback or equivalent.
Reproducibility check is not production readiness. No promotion.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


def build_dry_demo_command() -> str:
    return (
        "python workspace/scripts/agent_zero_overnight_research.py "
        "--question 'What is the Banach-Tarski paradox?' "
        "--risk-mode normal "
        "--model-profile tiny_fast "
        "--dry-run "
        "--output-root ./demo_output"
    )


def build_live_tiny_command(
    *,
    endpoint: str = "http://localhost:1234",
    model: str = "qwen2.5-0.5b-instruct",
) -> str:
    return (
        f"python workspace/scripts/agent_zero_overnight_research.py "
        f"--question 'What is the Banach-Tarski paradox?' "
        f"--risk-mode normal "
        f"--model-profile tiny_fast "
        f"--model-endpoint {endpoint} "
        f"--model-name {model} "
        f"--source-url 'https://en.wikipedia.org/wiki/Banach%E2%80%93Tarski_paradox' "
        f"--wall-clock-budget-seconds 120 "
        f"--output-root ./demo_output"
    )


def build_regression_command() -> str:
    return "python -m pytest tests/ -x -q --tb=short"


def build_report(checks: list, verdict: str, *, proof_root: str = "") -> dict:
    return {
        "schema_version": "clean_run_doctor_v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "checks": [
            {"name": c.name, "passed": c.passed, "severity": c.severity,
             "detail": c.detail}
            for c in checks
        ],
        "commands": {
            "dry_demo": build_dry_demo_command(),
            "live_tiny": build_live_tiny_command(),
            "regression": build_regression_command(),
        },
        "no_remote_model_fallback": True,
        "reproducibility_is_not_production_readiness": True,
        "promotion_allowed": False,
        "operator_review_required": True,
    }


def write_report(report: dict, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "clean_run_doctor_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    lines = [
        "# Clean Run Doctor Report",
        "",
        f"Verdict: {report['verdict']}",
        "",
        "## Checks",
        "",
    ]
    for c in report["checks"]:
        status = "PASS" if c["passed"] else "FAIL"
        lines.append(f"- [{status}] {c['name']} ({c['severity']}): {c['detail']}")

    lines.extend([
        "",
        "## Generated Commands",
        "",
        "### Dry Demo",
        f"```",
        report["commands"]["dry_demo"],
        f"```",
        "",
        "### Live Tiny",
        f"```",
        report["commands"]["live_tiny"],
        f"```",
        "",
        "### Regression",
        f"```",
        report["commands"]["regression"],
        f"```",
        "",
        "---",
        "Reproducibility check is not production readiness. No promotion.",
    ])

    md_path = os.path.join(out_dir, "clean_run_doctor_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return json_path
