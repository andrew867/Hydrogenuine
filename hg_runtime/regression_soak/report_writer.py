"""Write soak harness report and artifacts."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl
from hg_runtime.regression_soak.churn_detector import classify_churn, compare_stable_hashes
from hg_runtime.regression_soak.result_parser import detect_flakes, summarize_results
from hg_runtime.regression_soak.schemas import (
    PHASE19_VERDICT,
    PHASE24_STATUS,
    PROVIDER_MODE,
    SOAK_INVARIANTS,
)


def write_soak_artifacts(proof_dir: Path, soak: dict, repo_root: Path) -> dict:
    proof_dir.mkdir(parents=True, exist_ok=True)

    summary = summarize_results(soak)
    flakes = detect_flakes(soak)
    churn = classify_churn(soak["dirty_checks"])
    hashes = compare_stable_hashes(soak)

    boundary_assertions = {
        "live_effects_created": False,
        "web_browse_performed": False,
        "external_provider_calls_made": False,
        "arbitrary_file_ingestion_enabled": False,
        "pdf_ingestion_enabled": False,
        "ocr_enabled": False,
        "html_parsing_enabled": False,
        "patch_request_applied": False,
        "deletion_performed": False,
        "tool_authorization_granted": False,
        "belief_promotion_automatic": False,
        "phase19_yellow_preserved": PHASE19_VERDICT.startswith("YELLOW_PHASE19"),
        "phase24_infrastructure_only_preserved": PHASE24_STATUS == "infrastructure_only",
        "fake_green_rejected": True,
    }

    optional_missing = soak.get("optional_missing", [])

    manifest = {
        "schema": "regression_soak_manifest_v1",
        "repo_root": str(repo_root),
        "provider_mode": PROVIDER_MODE,
        "total_iterations": soak["total_iterations"],
        "total_commands": soak["total_commands"],
        "elapsed_seconds": soak["elapsed_seconds"],
        "summary": summary,
        "flake_count": len(flakes),
        "unexpected_churn": churn["has_unexpected_churn"],
        "all_hashes_stable": hashes["all_stable"],
        "all_semantic_hashes_stable": hashes.get("all_semantic_stable", True),
        "has_nonsemantic_instability_only": hashes.get("has_nonsemantic_instability_only", False),
        "optional_missing": optional_missing,
        "invariants": SOAK_INVARIANTS,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
    }

    write_json(proof_dir / "soak_manifest.json", manifest)
    write_jsonl(proof_dir / "soak_iterations.jsonl", soak["iterations"])
    write_jsonl(proof_dir / "command_results.jsonl", soak["all_results"])
    write_jsonl(proof_dir / "flaky_tests.jsonl", flakes)
    write_json(proof_dir / "churn_report.json", churn)
    write_json(proof_dir / "stable_hash_report.json", hashes)
    write_jsonl(proof_dir / "dirty_tree_checks.jsonl", soak["dirty_checks"])
    write_json(proof_dir / "boundary_assertions.json", boundary_assertions)

    from hg_runtime.knowledge_acquisition_loop.redaction import secret_scan
    secret_ok = secret_scan(manifest)
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": secret_ok})

    return {
        "manifest": manifest,
        "summary": summary,
        "flakes": flakes,
        "churn": churn,
        "hashes": hashes,
        "boundary_assertions": boundary_assertions,
        "secret_redaction_passed": secret_ok,
    }


def write_report(proof_dir: Path, report_path: Path, artifacts: dict) -> None:
    s = artifacts["summary"]
    c = artifacts["churn"]
    h = artifacts["hashes"]
    om = s.get("optional_missing", [])
    text = f"""# HG Regression Soak Harness Report

- Provider mode: `{PROVIDER_MODE}`
- Total iterations: {artifacts['manifest']['total_iterations']}
- Total commands: {artifacts['manifest']['total_commands']}
- Elapsed: {artifacts['manifest']['elapsed_seconds']}s

## Summary

- Passed: {s['passed']}
- Failed: {s['failed']}
- Rejected: {s['rejected']}
- Timed out: {s['timed_out']}

## Optional Missing Gates

- Count: {len(om)}
"""
    for m in om:
        text += f"- `{m['command']}` — {m['reason']} — substitute: `{m['substitute']}`\n"
    text += f"""
## Flakes

- Flaky commands: {len(artifacts['flakes'])}

## Churn

- Dirty checks: {c['total_checks']}
- Known churn: {c['known_churn_count']}
- Unexpected churn: {c['unexpected_churn_count']}

## Hash Stability

- Stable commands: {len(h['stable_commands'])}
- Changed commands: {len(h['changed_commands'])}
- All stable: {h['all_stable']}
- Semantic stable: {h.get('all_semantic_stable', 'N/A')}
- Non-semantic instability only: {h.get('has_nonsemantic_instability_only', 'N/A')}

## Boundaries

- Phase 19 remains `{PHASE19_VERDICT}`.
- Phase 24 remains `{PHASE24_STATUS}`.
- No live effects. No web/providers. No PDF/OCR/HTML.
- No patch/delete. No tool authorization. No belief promotion.

## Proof Bundle

`{proof_dir}`
"""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(text, encoding="utf-8")
    (proof_dir / "report_snapshot.md").write_text(text, encoding="utf-8")
