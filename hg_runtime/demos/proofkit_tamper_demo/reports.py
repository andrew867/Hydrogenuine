"""Human-readable and public-handoff outputs for the proofkit tamper demo."""
from __future__ import annotations

import html
import json
from pathlib import Path

from .harness import sha256_file

CLAIM_BOUNDARY = """# Claim Boundary — Proofkit Tamper Demo

**Core principle: tamper-evident, not tamper-proof.**

## What this demo proves
- The tested proofkit validators detect the tested tamper patterns (stale receipt hash,
  post-sealing checksum mismatch, missing manifest-listed artifact, fixture marker in a
  live-tier bundle, manifest/gate verdict contradiction).
- The source bundle was not mutated (tree hash identical before and after).
- Every baseline and tamper result is file-backed and repeatable from the recorded
  commands.

## What this demo does NOT prove
- It does not make bundles impossible to alter — controlled tamper cases show detection,
  not prevention.
- It does not prove model correctness. Proof records what happened.
- It does not prove external anchoring. External anchoring is not claimed.
- It does not prove full cross-receipt hash chaining; only per-receipt hashes,
  bundle checksums, and manifest consistency are tested here.
- It does not prove production certification, third-party audit, or customer deployment.
- A GREEN verdict means the named checks reran successfully — not that it is safe to act.
"""


def write_reports(out: Path, result: dict) -> None:
    (out / "claim_boundary_report.md").write_text(CLAIM_BOUNDARY, encoding="utf-8")
    (out / "summary_report.md").write_text(_summary_md(result), encoding="utf-8")
    (out / "demo_report.html").write_text(_report_html(result), encoding="utf-8")
    (out / "proof_index.json").write_text(json.dumps(_proof_index(result), indent=1),
                                          encoding="utf-8")
    (out / "website_handoff.md").write_text(_handoff_md(result), encoding="utf-8")


def seal_bundle(out: Path) -> None:
    """checksums then manifest, written last (CT sealing order)."""
    files = sorted(p for p in out.rglob("*") if p.is_file()
                   and p.name not in {"checksums.sha256", "manifest.json"})
    lines = [f"{sha256_file(p)}  {p.relative_to(out).as_posix()}" for p in files]
    (out / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "1",
        "bundle": "proofkit_tamper_demo",
        "claim": "tamper-evident, not tamper-proof",
        "file_hashes": {p.relative_to(out).as_posix(): sha256_file(p)
                        for p in files + [out / "checksums.sha256"]},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")


def _summary_md(r: dict) -> str:
    lines = [
        "# Proofkit Tamper Demo",
        "",
        "This demo starts with a valid proof bundle, then creates controlled tampered",
        "copies and shows the proofkit validators rejecting them.",
        "",
        "## What was validated",
        f"- Source bundle: `{r['source_bundle']}` (Governed Research Soak — Operator UI Live,",
        "  the current public GREEN proof bundle). The source was copied; every mutation",
        "  happened only in copies.",
        f"- Copy scope: {r['copied_files_per_case']} files per variant; media excluded ({r['copy_scope_note']}).",
        "",
        "## Baseline result",
        f"- Baseline copy validates: **{'GREEN' if r['baseline_ok'] else 'FAILED'}**",
        f"  - receipt hashes: {r['baseline_results']['receipt_hash_checker']['verdict']}",
        f"  - fixture scan: {r['baseline_results']['fixture_leak_detector']['verdict']}",
        f"  - checksums: {r['baseline_results']['checksums']['verdict']}",
        f"  - manifest files: {r['baseline_results']['manifest_files']['verdict']}",
        "",
        "## Tamper cases (every RED below is expected and controlled)",
        "",
        "| Case | Mutation | Validator | Expected | Actual | Matched |",
        "|---|---|---|---|---|---|",
    ]
    for c in r["case_results"]:
        lines.append(
            f"| {c['case_id']} | {', '.join(c['mutated_files'])} | {c['validator_used']} "
            f"| {c['expected_verdict']} | {c['actual_verdict']} "
            f"| {'yes' if c['expected_failure_matched'] else 'NO'} |")
    lines += [
        "",
        "## What this proves",
        "- The validators can detect the tested tamper patterns.",
        f"- The source bundle was not mutated (tree hash `{r['source_bundle_hash_before'][:16]}…`",
        "  identical before and after).",
        "- The baseline and tamper results are file-backed (see `tool_outputs/`).",
        "- The demo is repeatable (reproduction command below).",
        "",
        "## What this does not prove",
        "- It does not make bundles impossible to alter (tamper-evident, not tamper-proof).",
        "- It does not prove model correctness.",
        "- It does not prove external anchoring (not claimed).",
        "- It does not prove full cross-receipt hash chaining (per-receipt hashes, bundle",
        "  checksums, and manifest consistency only).",
        "- It does not prove production certification.",
        "",
        "## Reproduction command",
        "```bash",
        "cd workspace",
        "python -m hg_runtime.demos.proofkit_tamper_demo \\",
        "  --source-bundle docs/proofs/governed_research_soak/operator_ui_live \\",
        "  --output ../docs/proofs/proofkit_tamper_demo --public-safe",
        "```",
        "",
        "## Claim boundaries",
        "See `claim_boundary_report.md`. Core line: **tamper-evident, not tamper-proof**;",
        "proof records what happened; it does not prove model correctness.",
    ]
    return "\n".join(lines) + "\n"


def _proof_index(r: dict) -> dict:
    return {
        "title": "Proofkit Tamper Demo",
        "verdict": "pending_gate",  # gate overwrites via its own result file
        "source_bundle": r["source_bundle"],
        "source_bundle_unchanged": r["source_bundle_unchanged"],
        "baseline_result": {
            "baseline_ok": r["baseline_ok"],
            "receipt_hashes": r["baseline_results"]["receipt_hash_checker"]["verdict"],
            "fixture_scan": r["baseline_results"]["fixture_leak_detector"]["verdict"],
            "checksums": r["baseline_results"]["checksums"]["verdict"],
        },
        "tamper_cases": [
            {"case_id": c["case_id"], "expected": c["expected_verdict"],
             "actual": c["actual_verdict"], "matched": c["expected_failure_matched"]}
            for c in r["case_results"]],
        "validators_used": sorted({c["validator_used"] for c in r["case_results"]}),
        "public_safe_metrics": {
            "tamper_cases_total": r["tamper_cases_total"],
            "tamper_cases_matched": r["tamper_cases_matched"],
            "files_per_variant": r["copied_files_per_case"],
        },
        "summary_report_path": "summary_report.md",
        "demo_report_path": "demo_report.html",
        "claim_boundary_report_path": "claim_boundary_report.md",
        "gate_result_path": "proofkit_tamper_gate_result.json",
        "checksums_path": "checksums.sha256",
    }


def _handoff_md(r: dict) -> str:
    ts = r["timestamp"]
    return f"""# Website Handoff — Proofkit Tamper Demo

**Status:** PUBLIC-READY INTERNAL PROOF (do not integrate during the V3 freeze;
this doc is the handoff for the next review window).

## Suggested card

**Title:** Proofkit Tamper Demo
**Description:** A valid proof bundle is copied, validated, then deliberately tampered
in controlled ways. The proofkit validators reject the modified copies and write
file-backed RED results for hash mismatches, missing artifacts, and fixture leaks.
**Boundary:** This proves the tested tamper checks ran. It does not prove model
correctness, production certification, external anchoring, or tamper-proof storage.
**CTA:** View tamper walkthrough
**Route suggestion:** `/demos/proofkit-tamper/`

## File-backed metrics (only these numbers may appear on the page)

- Baseline: {'GREEN' if r['baseline_ok'] else 'FAILED'} (receipt hashes, fixture scan, checksums, manifest files)
- Tamper cases: {r['tamper_cases_matched']}/{r['tamper_cases_total']} rejected for the expected reason
- Source bundle unchanged: {str(r['source_bundle_unchanged']).lower()} (tree-hash verified)
- Source: the public GRS Operator UI Live bundle

## Asset copy list (from `docs/proofs/proofkit_tamper_demo/{ts}/`)

- `proof_index.json` (all displayed numbers trace here)
- `summary_report.md`, `claim_boundary_report.md`, `demo_report.html`
- `tamper_case_results.json`, `baseline_validation_result.json`
- `tool_outputs/` (raw validator stdout per case)
- `proofkit_tamper_gate_result.json`, `checksums.sha256`, `manifest.json`

## Suggested screenshot/video plan

1. Baseline GREEN card (validators passing on the copy).
2. One tampered receipt diff (the changed field vs the stale hash).
3. The RED validator output for each case (5 shots).
4. Optional 45–60 s human-paced capture walking case 1 end to end.

## Claim boundary text for the page

Tamper-evident, not tamper-proof. Controlled tamper cases; tested validator coverage;
source bundle unchanged; proof records what happened; it does not prove model
correctness; external anchoring not claimed.
"""


def _report_html(r: dict) -> str:
    def card(title: str, verdict: str, body: str, red: bool) -> str:
        color = "#c0392b" if red else "#1e8449"
        note = ("Expected, controlled failure — this RED is the demo working."
                if red else
                "verdict: GREEN_ baseline — proof bundle checks reran; not permission, not safe-to-act. See No Fake GREEN.")
        return (f'<div style="border:1px solid #333;border-left:6px solid {color};'
                f'margin:12px 0;padding:12px;background:#111;color:#ddd">'
                f'<h3 style="margin:0 0 6px">{html.escape(title)}</h3>'
                f'<code style="color:{color}">{html.escape(verdict)}</code>'
                f'<p>{html.escape(body)}</p>'
                f'<p style="font-size:12px;color:#888">{note}</p></div>')

    cards = [card("Baseline copy — all integrity checks pass",
                  "GREEN baseline (receipt hashes / fixture scan / checksums / manifest files)"
                  if r["baseline_ok"] else "BASELINE FAILED",
                  f"Source: {r['source_bundle']} — copied, source untouched "
                  f"(tree hash verified identical). Proof reference: gate_result.json + proof_index.json in this bundle.",
                  red=not r["baseline_ok"])]
    for c in r["case_results"]:
        cards.append(card(
            f"Tamper case: {c['case_id']}",
            c["actual_verdict"],
            f"{c['description']} Mutated: {', '.join(c['mutated_files'])}. "
            f"Validator: {c['validator_used']}. {c['public_explanation']} "
            f"Raw output: {c['stdout_path']}",
            red=True))
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Proofkit Tamper Demo</title></head>
<body style="font-family:system-ui;max-width:860px;margin:24px auto;background:#0a0a0a;color:#ddd">
<h1>Proofkit Tamper Demo</h1>
<p>This demo starts with a valid proof bundle, then creates controlled tampered copies
and shows the proofkit validators rejecting them. <strong>Tamper-evident, not
tamper-proof.</strong> Proof records what happened; it does not prove model correctness.</p>
{''.join(cards)}
<h2>Claim boundary</h2>
<p>See claim_boundary_report.md. This demo does not prove model correctness, external
anchoring, full cross-receipt hash chaining, production certification, or tamper-proof
storage. Every number on this page traces to proof_index.json.</p>
</body></html>
"""
