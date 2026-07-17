"""Generate pre-long-soak readiness report and suggested commands.

Read-only except writing readiness outputs. No promotion. No self-authorization.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from hg_runtime.soak_readiness.environment_doctor import (
    run_all_checks, compute_verdict, CheckResult,
)
from hg_runtime.soak_readiness.model_doctor import (
    run_model_checks, compute_model_verdict, ModelCheckResult,
)


def generate_readiness_report(
    *,
    output_root: str,
    model_endpoint: str = "http://127.0.0.1:1234/v1",
    model_name: str = "qwen2.5-0.5b-instruct",
    model_required: bool = False,
    dry_run: bool = False,
) -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = os.path.join(output_root, ts)
    os.makedirs(out_dir, exist_ok=True)

    env_checks = run_all_checks(output_root)
    env_verdict = compute_verdict(env_checks)

    if dry_run:
        model_checks = [
            ModelCheckResult("endpoint_reachable", True, "dry_run"),
            ModelCheckResult("model_available", True, "dry_run"),
        ]
        model_verdict = "GREEN"
    else:
        model_checks = run_model_checks(model_endpoint, model_name)
        model_verdict = compute_model_verdict(model_checks, model_required)

    all_env_pass = env_verdict == "GREEN_PRE_LONG_SOAK_READY"
    model_ok = model_verdict == "GREEN"

    if env_verdict.startswith("RED"):
        overall = "RED_PRE_LONG_SOAK_BLOCKED"
    elif model_verdict == "RED":
        overall = "RED_PRE_LONG_SOAK_BLOCKED"
    elif all_env_pass and model_ok:
        overall = "GREEN_PRE_LONG_SOAK_READY"
    else:
        overall = "YELLOW_PRE_LONG_SOAK_READY_WITH_LIMITATIONS"

    limitations = []
    for c in env_checks:
        if not c.passed:
            limitations.append(f"env:{c.name}: {c.detail}")
    for c in model_checks:
        if not c.passed:
            limitations.append(f"model:{c.name}: {c.detail}")

    result = {
        "readiness_gate": overall,
        "timestamp": ts,
        "environment_verdict": env_verdict,
        "model_verdict": model_verdict,
        "overall_verdict": overall,
        "environment_checks": [
            {"name": c.name, "passed": c.passed, "severity": c.severity, "detail": c.detail}
            for c in env_checks
        ],
        "model_checks": [
            {"name": c.name, "passed": c.passed, "detail": c.detail}
            for c in model_checks
        ],
        "limitations": limitations,
        "out_dir": out_dir,
        "operator_review_required": True,
        "promotion_allowed": False,
        "model_output_is_not_truth": True,
    }

    with open(os.path.join(out_dir, "readiness_report.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    _write_readiness_md(result, out_dir)
    _write_soak_commands(result, out_dir, model_endpoint, model_name)

    return result


def _write_readiness_md(result: dict, out_dir: str):
    lines = [
        "# Pre-Long-Soak Readiness Report",
        "",
        f"Verdict: {result['overall_verdict']}",
        f"Timestamp: {result['timestamp']}",
        "",
        "## Environment Checks",
        "",
    ]
    for c in result["environment_checks"]:
        status = "PASS" if c["passed"] else "FAIL"
        lines.append(f"- [{status}] {c['name']} ({c['severity']}): {c['detail']}")
    lines.extend(["", "## Model Checks", ""])
    for c in result["model_checks"]:
        status = "PASS" if c["passed"] else "FAIL"
        lines.append(f"- [{status}] {c['name']}: {c['detail']}")
    if result["limitations"]:
        lines.extend(["", "## Limitations", ""])
        for lim in result["limitations"]:
            lines.append(f"- {lim}")
    lines.extend([
        "", "---",
        "Source is not truth. Model output is not truth.",
        "Operator review required. No self-authorization.",
    ])
    with open(os.path.join(out_dir, "readiness_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _write_soak_commands(result: dict, out_dir: str,
                         endpoint: str, model_name: str):
    base = (
        f'python workspace/scripts/agent_zero_overnight_research.py '
        f'--question "CTMU self-reference and telic recursion" '
        f'--risk-mode high_risk_speculative '
        f'--model-endpoint {endpoint} '
        f'--model-name {model_name} '
        f'--model-profile normal_fast '
        f'--backlog-model-profile tiny_fast '
        f'--enable-source-chunking '
        f'--wall-clock-budget-seconds 1800 '
        f'--per-topic-wall-clock-seconds 300 '
        f'--live-http-get '
        f'--max-sources 6 '
        f'--max-model-calls 12 '
        f'--enable-backlog-drain '
        f'--backlog-file workspace/research_seeds/backlog_evening.json '
        f'--max-backlog-topics 5 '
        f'--max-total-sources 20 '
        f'--max-total-model-calls 40'
    )

    sh_cmd = f"#!/bin/bash\n# Pre-long-soak suggested command\n# Verdict: {result['overall_verdict']}\n\ncd \"$(dirname \"$0\")/../../../..\" || exit 1\n\n{base}\n"
    ps_cmd = f"# Pre-long-soak suggested command (PowerShell)\n# Verdict: {result['overall_verdict']}\n\n{base}\n"

    with open(os.path.join(out_dir, "suggested_long_soak_command.sh"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(sh_cmd)
    with open(os.path.join(out_dir, "suggested_long_soak_command.ps1"), "w",
              encoding="utf-8") as f:
        f.write(ps_cmd)
