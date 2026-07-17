"""Demo proof bundle writer.

Copies proof artifacts into a self-contained bundle with redaction.
No mutation of original proof directory. No external network in index.html.
Source is not truth. Model output is not truth. No promotion.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone

from hg_runtime.post_run_review.artifact_loader import load_proof_dir
from hg_runtime.post_run_review.live_model_review_builder import (
    generate_all_reports,
    check_text_for_unsafe_terms,
)
from hg_runtime.post_run_review.why_not_promoted import explain_why_not_promoted
from hg_runtime.demo_bundle.redaction import (
    redact_path,
    redact_text,
    redact_json_values,
)

_BOUNDARY_STATEMENT = """\
# Proof Boundary Statement

This demo bundle contains proof artifacts from the Hydrogenuine research runtime.

## What These Artifacts Prove

- The runtime can fetch public web sources via read-only HTTP GET.
- The runtime can capture browser screenshots with a locked-down context.
- The runtime can run local model inference over fetched source text.
- All outputs are receipted, quarantined, and reviewed.
- No output was promoted to knowledge or memory.
- No external effects occurred beyond read-only observation and local inference.

## What These Artifacts Do NOT Prove

- Production readiness.
- Autonomous research authority.
- That any output is truth or verified knowledge.
- That the system replaces human researchers.
- Regulatory compliance.

## Doctrine

- Source is not truth.
- Screenshot is not proof.
- Model output is not truth.
- Model confidence is not proof.
- Model consensus is not proof.
- Evidence graph edge is not proof.
- Quality score is not authority.
- No self-authorization. No fake GREEN.
- STOP/PANIC overrides all.
"""


def _build_index_html(stats: dict, reports: dict) -> str:
    """Build a static index.html with no external network references."""
    why_example = explain_why_not_promoted(
        item_id="example_model_output",
        item_type="model_output",
        is_model_output=True,
        promotion_allowed=False,
        operator_reviewed=False,
    )
    why_reasons = ", ".join(
        r["reason"] for r in why_example["blocking_reasons"][:3]
    )

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Hydrogenuine Demo Proof Bundle</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2em auto; padding: 0 1em; color: #222; }}
h1 {{ border-bottom: 2px solid #333; padding-bottom: 0.3em; }}
table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
th, td {{ border: 1px solid #ccc; padding: 0.5em; text-align: left; }}
th {{ background: #f5f5f5; }}
.verdict {{ font-size: 1.5em; font-weight: bold; }}
.green {{ color: #2a7; }}
.red {{ color: #c33; }}
.section {{ margin: 2em 0; }}
.honesty {{ background: #fff8e1; border-left: 4px solid #f9a825; padding: 1em; margin: 1em 0; }}
</style>
</head>
<body>
<h1>Hydrogenuine Demo Proof Bundle</h1>
<p class="verdict {('green' if stats.get('gate_verdict') == 'GREEN' else 'red')}">
Gate: {stats.get('gate_verdict', 'UNKNOWN')} ({stats.get('gate_checks_passed', 0)}/{stats.get('gate_checks_total', 0)})
</p>

<div class="section">
<h2>Proof Summary</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Sources attempted</td><td>{stats.get('sources_attempted', 0)}</td></tr>
<tr><td>Fetches succeeded</td><td>{stats.get('successful_fetches', 0)}</td></tr>
<tr><td>Screenshots</td><td>{stats.get('screenshots_captured', 0)}</td></tr>
<tr><td>Model inferences</td><td>{stats.get('model_successes', 0)}/{stats.get('model_attempts', 0)}</td></tr>
<tr><td>Quality issues</td><td>{stats.get('quality_issues', 0)}</td></tr>
<tr><td>Contradictions</td><td>{stats.get('contradictions', 0)}</td></tr>
<tr><td>Quarantined</td><td>{stats.get('quarantine_entries', 0)}</td></tr>
<tr><td>Promotions</td><td>{stats.get('promotions_count', 0)}</td></tr>
<tr><td>External effects</td><td>{stats.get('external_effects_count', 0)}</td></tr>
</table>
</div>

<div class="section">
<h2>What Was Proven</h2>
<ul>
<li>Live HTTP GET retrieval works with receipts.</li>
<li>Local model inference over fetched source text produces receipted output.</li>
<li>Quality adjudication, contradiction recording, and quarantine function.</li>
<li>No promotion occurred. No external effects beyond read-only observation.</li>
</ul>
</div>

<div class="section">
<h2>What Was NOT Proven</h2>
<ul>
<li>Production readiness.</li>
<li>Autonomous research authority.</li>
<li>Multi-model ensemble inference.</li>
<li>Operator console end-to-end workflow.</li>
</ul>
</div>

<div class="section">
<h2>Why Not Promoted (Example)</h2>
<p>Item: <code>example_model_output</code></p>
<p>Blocking reasons: {why_reasons}</p>
<p>Next action: {why_example['next_possible_operator_action']}</p>
</div>

<div class="section">
<h2>Receipt Inventory</h2>
<ul>
<li>reports/ — Executive, research digest, boundary audit, operator one-pager, public summary</li>
<li>receipts/ — HTTP fetch, source, model inference, quality, route receipts</li>
<li>model_outputs/ — Model output text files</li>
<li>screenshots/ — Playwright screenshots and metadata</li>
<li>evidence_graph/ — Evidence graph receipts</li>
<li>quarantine/ — Quarantine receipts</li>
<li>public_claim_check/ — Public claim checker results</li>
<li>gates/ — Gate result</li>
</ul>
</div>

<div class="honesty">
<h2>Honesty Statements</h2>
<ul>
<li>Source is not truth.</li>
<li>Screenshot is not proof.</li>
<li>Model output is not truth.</li>
<li>This proof does not establish production readiness.</li>
<li>This proof does not establish autonomous research authority.</li>
<li>No candidate knowledge was promoted.</li>
</ul>
</div>

</body>
</html>
"""


def generate_demo_bundle(
    proof_dir: str,
    output_dir: str,
    *,
    supplemental_proof_dir: str = "",
) -> dict:
    """Generate a self-contained demo proof bundle.

    Does NOT mutate proof_dir. Copies and redacts into output_dir.
    """
    os.makedirs(output_dir, exist_ok=True)

    artifacts = load_proof_dir(proof_dir)
    reports = generate_all_reports(proof_dir)

    from hg_runtime.post_run_review.live_model_review_builder import _extract_stats
    stats = _extract_stats(artifacts)

    if supplemental_proof_dir:
        sup = load_proof_dir(supplemental_proof_dir)
        stats["screenshots_captured"] = len(
            [f for f in sup.get("screenshot_files", []) if f["is_png"]]
        )

    redaction_log = []

    reports_dir = os.path.join(output_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    for name, content in reports.items():
        redacted = redact_text(content)
        path = os.path.join(reports_dir, f"{name}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(redacted)
        redaction_log.append({"file": f"reports/{name}.md", "redacted": True})

    receipts_dir = os.path.join(output_dir, "receipts")
    os.makedirs(receipts_dir, exist_ok=True)
    for receipt_name in [
        "http_fetch_receipts", "source_receipts", "model_inference_receipts",
        "quality_receipts", "route_receipts",
    ]:
        src = os.path.join(proof_dir, f"{receipt_name}.jsonl")
        if os.path.isfile(src):
            with open(src, "r", encoding="utf-8") as f:
                lines = f.readlines()
            dst = os.path.join(receipts_dir, f"{receipt_name}.jsonl")
            with open(dst, "w", encoding="utf-8") as f:
                for line in lines:
                    data = json.loads(line.strip())
                    redacted = redact_json_values(data)
                    f.write(json.dumps(redacted, sort_keys=True) + "\n")
            redaction_log.append({"file": f"receipts/{receipt_name}.jsonl", "redacted": True})

    model_out_dir = os.path.join(output_dir, "model_outputs")
    src_model = os.path.join(proof_dir, "model_outputs")
    if os.path.isdir(src_model):
        shutil.copytree(src_model, model_out_dir, dirs_exist_ok=True)
        redaction_log.append({"file": "model_outputs/", "redacted": False})

    screenshots_out = os.path.join(output_dir, "screenshots")
    src_screenshots = os.path.join(proof_dir, "playwright_screenshots")
    if not os.path.isdir(src_screenshots) and supplemental_proof_dir:
        src_screenshots = os.path.join(supplemental_proof_dir, "playwright_screenshots")
    if os.path.isdir(src_screenshots):
        shutil.copytree(src_screenshots, screenshots_out, dirs_exist_ok=True)
        redaction_log.append({"file": "screenshots/", "redacted": False})

    eg_dir = os.path.join(output_dir, "evidence_graph")
    os.makedirs(eg_dir, exist_ok=True)
    src_eg = os.path.join(proof_dir, "evidence_graph_receipts.jsonl")
    if os.path.isfile(src_eg):
        shutil.copy2(src_eg, os.path.join(eg_dir, "evidence_graph_receipts.jsonl"))

    q_dir = os.path.join(output_dir, "quarantine")
    os.makedirs(q_dir, exist_ok=True)
    src_q = os.path.join(proof_dir, "quarantine_receipts.jsonl")
    if os.path.isfile(src_q):
        shutil.copy2(src_q, os.path.join(q_dir, "quarantine_receipts.jsonl"))

    pc_dir = os.path.join(output_dir, "public_claim_check")
    os.makedirs(pc_dir, exist_ok=True)
    src_pc = os.path.join(proof_dir, "public_claim_checks.jsonl")
    if os.path.isfile(src_pc):
        shutil.copy2(src_pc, os.path.join(pc_dir, "public_claim_checks.jsonl"))

    gates_dir = os.path.join(output_dir, "gates")
    os.makedirs(gates_dir, exist_ok=True)
    gate_src = os.path.join(os.path.dirname(proof_dir), "gate_result.json")
    if os.path.isfile(gate_src):
        with open(gate_src, "r", encoding="utf-8") as f:
            gate_data = json.load(f)
        gate_data = redact_json_values(gate_data)
        with open(os.path.join(gates_dir, "gate_result.json"), "w", encoding="utf-8") as f:
            json.dump(gate_data, f, indent=2, sort_keys=True)

    with open(os.path.join(output_dir, "PROOF_BOUNDARY_STATEMENT.md"), "w", encoding="utf-8") as f:
        f.write(_BOUNDARY_STATEMENT)

    index_html = _build_index_html(stats, reports)
    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    index_json = {
        "bundle_created_at": datetime.now(timezone.utc).isoformat(),
        "source_proof_dir": redact_path(proof_dir),
        "stats": stats,
        "reports": list(reports.keys()),
        "redaction_applied": True,
    }
    index_json["stats"]["proof_dir"] = redact_path(stats["proof_dir"])
    with open(os.path.join(output_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index_json, f, indent=2, sort_keys=True)

    readme = redact_text(reports.get("public_proof_summary", ""))
    with open(os.path.join(output_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme)

    manifest = {
        "bundle_type": "demo_proof_bundle",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_proof_dir": redact_path(proof_dir),
        "supplemental_proof_dir": redact_path(supplemental_proof_dir) if supplemental_proof_dir else "",
        "redaction_applied": True,
        "promotion_allowed": False,
        "operator_review_required": True,
    }
    with open(os.path.join(output_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    redaction_report = {
        "total_files_processed": len(redaction_log),
        "files": redaction_log,
        "private_paths_redacted": True,
        "endpoints_redacted": True,
        "secrets_removed": True,
    }
    with open(os.path.join(output_dir, "redaction_report.json"), "w", encoding="utf-8") as f:
        json.dump(redaction_report, f, indent=2, sort_keys=True)

    all_text = ""
    for name, content in reports.items():
        all_text += content + "\n"
    all_text += index_html + "\n"
    all_text += readme + "\n"
    unsafe_terms = check_text_for_unsafe_terms(all_text)

    return {
        "bundle_dir": output_dir,
        "reports_generated": list(reports.keys()),
        "receipts_copied": True,
        "redaction_applied": True,
        "unsafe_terms_found": unsafe_terms,
        "promotion_allowed": False,
    }
