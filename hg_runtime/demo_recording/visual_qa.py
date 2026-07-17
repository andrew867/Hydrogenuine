"""Visual QA checks for the demo dashboard.

Inspects DOM state, console output, network log, and screenshot content
for issues that would make the dashboard unfit for public demo recording.
No mutation. No network. Dashboard display is not truth.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

UNSAFE_AFFIRMATIVE_TERMS = [
    "AGI", "artificial general intelligence", "conscious",
    "sentient", "sovereign AI", "truth engine", "proven true",
    "establishes truth", "proves that", "has been proven",
    "this proves", "scientifically proven",
    "consciousness", "sentience", "sovereignty",
]

NEGATION_MARKERS = [
    "not ", "no ", "cannot ", "does not ", "do not ", "never ",
    "is not ", "≠", "!=", "without ",
]


def _is_affirmative(line: str, term: str) -> bool:
    idx = line.lower().find(term.lower())
    if idx < 0:
        return False
    context_start = max(0, idx - 60)
    context = line[context_start:idx].lower()
    for neg in NEGATION_MARKERS:
        if neg in context:
            return False
    return True


def run_visual_qa(
    *,
    recording_dir: str,
    dashboard_dir: str,
    strict: bool = False,
) -> dict:
    """Run visual QA on captured dashboard screenshots and metadata."""
    issues = []

    def issue(severity: str, category: str, detail: str, file: str = ""):
        issues.append({
            "severity": severity,
            "category": category,
            "detail": detail,
            "file": file,
        })

    manifest_path = os.path.join(recording_dir, "recording_manifest.json")
    if not os.path.isfile(manifest_path):
        issue("HIGH", "missing_manifest", "recording_manifest.json not found")
        return _build_report(issues, recording_dir, dashboard_dir)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    screenshots = manifest.get("screenshots", [])
    if len(screenshots) < 10:
        issue("HIGH", "incomplete_capture", f"Only {len(screenshots)} screenshots, expected 10")

    ss_dir = os.path.join(recording_dir, "screenshots")
    for ss in screenshots:
        ss_path = os.path.join(ss_dir, ss["filename"]) if not os.path.isabs(ss.get("path", "")) else ss["path"]
        if not os.path.isfile(ss_path):
            issue("HIGH", "missing_screenshot", f"Screenshot missing: {ss['filename']}", ss["filename"])

    for err in manifest.get("console_log", []):
        if err.get("type") == "error":
            issue("MEDIUM", "console_error", f"Console error: {err.get('text', '')[:200]}")

    for err in manifest.get("page_errors", []):
        issue("MEDIUM", "page_error", f"Page error: {err.get('error', '')[:200]}")

    blocked = manifest.get("blocked_requests", [])
    if blocked:
        for b in blocked:
            issue("HIGH", "external_network", f"Blocked external request: {b.get('url', '')[:200]}")

    network_log = manifest.get("network_log", [])
    for req in network_log:
        if not req.get("is_local"):
            issue("HIGH", "external_network_unblocked", f"Non-local request not blocked: {req.get('url', '')[:200]}")

    _check_html_content(dashboard_dir, issues)

    _check_no_private_paths(dashboard_dir, issues)

    return _build_report(issues, recording_dir, dashboard_dir)


def _check_html_content(dashboard_dir: str, issues: list):
    index_path = os.path.join(dashboard_dir, "index.html")
    if not os.path.isfile(index_path):
        issues.append({"severity": "HIGH", "category": "missing_html", "detail": "index.html not found", "file": ""})
        return

    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    for bad in ["undefined", "[object Object]"]:
        if bad in html:
            for i, line in enumerate(html.split("\n"), 1):
                if bad in line:
                    if bad == "undefined" and ("undefined\"" in line or "'undefined'" in line or "undefined;" in line):
                        continue
                    issues.append({
                        "severity": "MEDIUM",
                        "category": "rendering_artifact",
                        "detail": f"Found '{bad}' in HTML at line {i}",
                        "file": "index.html",
                    })

    boundary_terms = ["Source is not truth", "Screenshot is not proof", "Model output is not truth"]
    for term in boundary_terms:
        if term not in html:
            issues.append({
                "severity": "HIGH",
                "category": "missing_boundary",
                "detail": f"Boundary statement missing: '{term}'",
                "file": "index.html",
            })

    for term in UNSAFE_AFFIRMATIVE_TERMS:
        for i, line in enumerate(html.split("\n"), 1):
            if _is_affirmative(line, term):
                issues.append({
                    "severity": "HIGH",
                    "category": "unsafe_public_claim",
                    "detail": f"Unsafe affirmative term '{term}' at line {i}: {line.strip()[:120]}",
                    "file": "index.html",
                })

    if "Promotions" not in html and "promotions" not in html:
        issues.append({
            "severity": "MEDIUM",
            "category": "missing_promotion_count",
            "detail": "Promotions count not visible in dashboard",
            "file": "index.html",
        })

    external_patterns = [
        r'https?://(?!127\.0\.0\.1|localhost)[^\s"\'<>]+',
    ]
    for pat in external_patterns:
        for i, line in enumerate(html.split("\n"), 1):
            for match in re.finditer(pat, line):
                url = match.group()
                if any(safe in url for safe in ["example.com", "#", "javascript:"]):
                    continue
                if "<td>" in line or "<a " in line or "href=" in line:
                    continue
                if "src=" in line or "link " in line:
                    issues.append({
                        "severity": "HIGH",
                        "category": "external_asset_reference",
                        "detail": f"External asset reference at line {i}: {url[:100]}",
                        "file": "index.html",
                    })


def _check_no_private_paths(dashboard_dir: str, issues: list):
    data_path = os.path.join(dashboard_dir, "dashboard_data.json")
    if not os.path.isfile(data_path):
        return

    with open(data_path, "r", encoding="utf-8") as f:
        text = f.read()

    private_patterns = [
        r'C:\\Users\\[a-zA-Z]+',
        r'/home/[a-zA-Z]+',
        r'/Users/[a-zA-Z]+',
        r'127\.0\.0\.1:\d{4,5}',
        r'localhost:\d{4,5}',
    ]
    for pat in private_patterns:
        for match in re.finditer(pat, text):
            issues.append({
                "severity": "MEDIUM",
                "category": "private_path_leak",
                "detail": f"Private path/endpoint in data: {match.group()[:80]}",
                "file": "dashboard_data.json",
            })


def _build_report(issues: list, recording_dir: str, dashboard_dir: str) -> dict:
    high = [i for i in issues if i["severity"] == "HIGH"]
    medium = [i for i in issues if i["severity"] == "MEDIUM"]
    low = [i for i in issues if i["severity"] == "LOW"]

    verdict = "PASS" if not high and not medium else "FAIL"

    report = {
        "verdict": verdict,
        "issues": issues,
        "high_count": len(high),
        "medium_count": len(medium),
        "low_count": len(low),
        "total_issues": len(issues),
        "recording_dir": recording_dir,
        "dashboard_dir": dashboard_dir,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "screenshot_is_proof": False,
        "dashboard_display_is_truth": False,
    }

    report_path = os.path.join(recording_dir, "visual_qa_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    md_lines = [
        "# Visual QA Report",
        "",
        f"Verdict: **{verdict}**",
        f"HIGH: {len(high)} | MEDIUM: {len(medium)} | LOW: {len(low)}",
        "",
    ]
    if high:
        md_lines.append("## HIGH Issues")
        for i in high:
            md_lines.append(f"- [{i['category']}] {i['detail']}")
        md_lines.append("")
    if medium:
        md_lines.append("## MEDIUM Issues")
        for i in medium:
            md_lines.append(f"- [{i['category']}] {i['detail']}")
        md_lines.append("")
    if low:
        md_lines.append("## LOW Issues")
        for i in low:
            md_lines.append(f"- [{i['category']}] {i['detail']}")
        md_lines.append("")

    md_lines.extend([
        "## Doctrine",
        "- Dashboard display is not truth.",
        "- Screenshot is not proof.",
        "- Source is not truth.",
        "- Model output is not truth.",
        "- A beautiful demo is not a production claim.",
    ])

    md_path = os.path.join(recording_dir, "visual_qa_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    return report
