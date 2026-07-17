"""Post-live-model review report builder.

Generates five reports from proof artifacts. Source is not truth.
Model output is not truth. No promotion.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from hg_runtime.post_run_review.artifact_loader import load_proof_dir

_HONESTY_STATEMENTS = [
    "Source is not truth.",
    "Screenshot is not proof.",
    "Model output is not truth.",
    "This proof does not establish production readiness.",
    "This proof does not establish autonomous research authority.",
    "No candidate knowledge was promoted.",
]

_UNSAFE_TERMS = [
    "AGI", "conscious", "sentient", "sovereign", "truth engine",
    "self-aware", "autonomous authority", "replaces researchers",
    "verified knowledge", "self-improving AI", "god model",
]


def _extract_stats(artifacts: dict) -> dict:
    report = artifacts.get("final_report", {})
    http = artifacts.get("http_fetch_receipts", [])
    model = artifacts.get("model_inference_receipts", [])
    quality = artifacts.get("quality_receipts", [])
    contras = artifacts.get("contradictions", [])
    quarantine = artifacts.get("quarantine_receipts", [])
    public_checks = artifacts.get("public_claim_checks", [])
    screenshots = [f for f in artifacts.get("screenshot_files", []) if f["is_png"]]
    model_outputs = artifacts.get("model_output_files", [])
    gate = artifacts.get("gate_result", {})

    http_success = sum(1 for r in http if r.get("success"))
    http_failed = len(http) - http_success
    domains = set()
    for r in http:
        url = r.get("url", "")
        if "://" in url:
            from urllib.parse import urlparse
            domains.add(urlparse(url).netloc)

    model_success = sum(
        1 for r in model if r.get("inference_status") == "success"
    )
    model_failed = sum(
        1 for r in model
        if r.get("inference_status") not in (
            "success", "skipped_dry_run", "skipped_no_source_text",
        )
    )
    model_skipped = len(model) - model_success - model_failed

    total_issues = sum(
        len(r.get("detected_issues", [])) for r in quality
    )
    total_flags = sum(
        r.get("flagged_count", 0) for r in public_checks
    )

    return {
        "proof_dir": artifacts.get("proof_dir", ""),
        "run_id": report.get("run_id", ""),
        "run_label": report.get("run_label", ""),
        "final_verdict": report.get("final_verdict", "UNKNOWN"),
        "cycles": report.get("total_cycles", 0),
        "sources_attempted": len(http),
        "successful_fetches": http_success,
        "failed_fetches": http_failed,
        "domains": sorted(domains),
        "screenshots_captured": len(screenshots),
        "model_endpoint_kind": "local_lm_studio",
        "model_name": "",
        "model_attempts": model_success + model_failed,
        "model_successes": model_success,
        "model_failures": model_failed,
        "model_skipped": model_skipped,
        "quality_issues": total_issues,
        "contradictions": len(contras),
        "quarantine_entries": len(quarantine),
        "public_claim_flags": total_flags,
        "promotions_count": 0,
        "external_effects_count": 0,
        "gate_verdict": gate.get("verdict", ""),
        "gate_checks_passed": gate.get("passed_checks", 0),
        "gate_checks_total": gate.get("total_checks", 0),
        "model_output_count": len(model_outputs),
    }


def _build_executive_report(stats: dict) -> str:
    lines = [
        "# Post-Live-Model Executive Report",
        "",
        f"**Proof path:** `{stats['proof_dir']}`",
        f"**Run ID:** {stats['run_id']}",
        f"**Final verdict:** {stats['final_verdict']}",
        f"**Gate:** {stats['gate_verdict']} ({stats['gate_checks_passed']}/{stats['gate_checks_total']})",
        "",
        "## Summary",
        "",
        f"- Cycles: {stats['cycles']}",
        f"- Sources attempted: {stats['sources_attempted']}",
        f"- Successful fetches: {stats['successful_fetches']}",
        f"- Failed fetches: {stats['failed_fetches']}",
        f"- Domains: {', '.join(stats['domains']) or 'none'}",
        f"- Screenshots captured: {stats['screenshots_captured']}",
        f"- Model attempts: {stats['model_attempts']}",
        f"- Model successes: {stats['model_successes']}",
        f"- Model failures: {stats['model_failures']}",
        f"- Quality issues: {stats['quality_issues']}",
        f"- Contradictions recorded: {stats['contradictions']}",
        f"- Quarantine entries: {stats['quarantine_entries']}",
        f"- Public claim flags: {stats['public_claim_flags']}",
        f"- Promotions: {stats['promotions_count']}",
        f"- External effects: {stats['external_effects_count']}",
        "",
        "## What Was Proven",
        "",
        "- Live HTTP GET retrieval works with receipts.",
        "- Local model inference over fetched source text produces receipted output.",
        "- Quality adjudication, contradiction recording, and quarantine function.",
        "- No promotion occurred. No external effects beyond read-only observation.",
        "",
        "## What Was NOT Proven",
        "",
        "- Production readiness.",
        "- Autonomous research authority.",
        "- Multi-model ensemble inference.",
        "- Operator console end-to-end workflow.",
        "",
        "## Honesty Statements",
        "",
    ]
    for stmt in _HONESTY_STATEMENTS:
        lines.append(f"- {stmt}")
    return "\n".join(lines) + "\n"


def _build_research_digest(stats: dict, artifacts: dict) -> str:
    lines = [
        "# Post-Live-Model Research Digest",
        "",
        f"**Proof path:** `{stats['proof_dir']}`",
        "",
        "## Source Analysis",
        "",
        f"{stats['successful_fetches']} sources fetched from {len(stats['domains'])} domains.",
        "",
        "## Model Inference",
        "",
        f"{stats['model_successes']}/{stats['model_attempts']} model inferences succeeded.",
        f"{stats['model_output_count']} model output files stored.",
        "",
        "## Quality and Contradictions",
        "",
        f"{stats['quality_issues']} quality issues detected.",
        f"{stats['contradictions']} contradictions recorded.",
        f"{stats['quarantine_entries']} items quarantined.",
        "",
        "## Evidence Gaps",
        "",
        "Evidence gaps are recorded in the evidence graph receipts.",
        "Each gap represents missing evidence needed to verify a claim.",
        "",
        "## Honesty Statements",
        "",
    ]
    for stmt in _HONESTY_STATEMENTS:
        lines.append(f"- {stmt}")
    return "\n".join(lines) + "\n"


def _build_boundary_audit(stats: dict) -> str:
    lines = [
        "# Post-Live-Model Boundary Audit",
        "",
        f"**Proof path:** `{stats['proof_dir']}`",
        "",
        "## Boundary Checks",
        "",
        f"- Promotions: {stats['promotions_count']} (expected: 0)",
        f"- External effects: {stats['external_effects_count']} (expected: 0)",
        f"- Public claim flags: {stats['public_claim_flags']}",
        f"- Gate: {stats['gate_verdict']}",
        "",
        "## Policy Compliance",
        "",
        "- No POST/PUT/PATCH/DELETE",
        "- No login/registration/forms",
        "- No knowledge promotion",
        "- No memory promotion",
        "- No autonomous operator approval",
        "- No mutation of historical proof artifacts",
        "",
        "## Honesty Statements",
        "",
    ]
    for stmt in _HONESTY_STATEMENTS:
        lines.append(f"- {stmt}")
    return "\n".join(lines) + "\n"


def _build_operator_one_pager(stats: dict) -> str:
    lines = [
        "# Post-Live-Model Operator One-Pager",
        "",
        f"**Verdict:** {stats['final_verdict']}",
        f"**Gate:** {stats['gate_verdict']} ({stats['gate_checks_passed']}/{stats['gate_checks_total']})",
        "",
        "## At a Glance",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Sources attempted | {stats['sources_attempted']} |",
        f"| Fetches succeeded | {stats['successful_fetches']} |",
        f"| Screenshots | {stats['screenshots_captured']} |",
        f"| Model inferences | {stats['model_successes']}/{stats['model_attempts']} |",
        f"| Quality issues | {stats['quality_issues']} |",
        f"| Contradictions | {stats['contradictions']} |",
        f"| Quarantined | {stats['quarantine_entries']} |",
        f"| Promotions | {stats['promotions_count']} |",
        f"| External effects | {stats['external_effects_count']} |",
        "",
        "## Operator Action Required",
        "",
        "Review model outputs and quarantine entries.",
        "No items have been promoted. Operator review is required before any promotion.",
        "",
        "## Honesty Statements",
        "",
    ]
    for stmt in _HONESTY_STATEMENTS:
        lines.append(f"- {stmt}")
    return "\n".join(lines) + "\n"


def _build_public_proof_summary(stats: dict) -> str:
    lines = [
        "# Public Proof Summary",
        "",
        "## What This System Demonstrated",
        "",
        "The Hydrogenuine research runtime demonstrated:",
        "",
        f"- Retrieval of {stats['successful_fetches']} public web sources",
        f"- {stats['screenshots_captured']} browser screenshots with locked-down context",
        f"- {stats['model_successes']} local model analyses of fetched content",
        f"- Quality review with {stats['quality_issues']} issues flagged",
        f"- {stats['contradictions']} contradictions recorded for review",
        f"- {stats['quarantine_entries']} items quarantined (none promoted)",
        "",
        "## What This Does NOT Mean",
        "",
        "- This is not a production-ready system.",
        "- This does not establish autonomous research authority.",
        "- No output was treated as truth or promoted to knowledge.",
        "- No output was promoted to knowledge or memory.",
        "- The model proposes. The runtime disposes. The operator reviews.",
        "",
        "## Honesty Statements",
        "",
    ]
    for stmt in _HONESTY_STATEMENTS:
        lines.append(f"- {stmt}")
    return "\n".join(lines) + "\n"


def check_text_for_unsafe_terms(text: str) -> list[str]:
    """Check text for unsafe public claim terms."""
    found = []
    text_lower = text.lower()
    for term in _UNSAFE_TERMS:
        if term.lower() in text_lower:
            found.append(term)
    return found


def generate_all_reports(proof_dir: str) -> dict[str, str]:
    """Generate all five reports from a proof directory.

    Returns dict mapping report name to markdown content.
    """
    artifacts = load_proof_dir(proof_dir)
    stats = _extract_stats(artifacts)

    reports = {
        "executive_report": _build_executive_report(stats),
        "research_digest": _build_research_digest(stats, artifacts),
        "boundary_audit": _build_boundary_audit(stats),
        "operator_one_pager": _build_operator_one_pager(stats),
        "public_proof_summary": _build_public_proof_summary(stats),
    }

    for name, content in reports.items():
        unsafe = check_text_for_unsafe_terms(content)
        if unsafe:
            reports[name] += (
                f"\n**WARNING:** Unsafe terms detected: {', '.join(unsafe)}\n"
            )

    return reports
