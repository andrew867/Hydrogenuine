"""AIS-1 record health fixture bundles (deterministic)."""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.agent_immune_system.schemas import PHASE19_VERDICT, PHASE24_STATUS

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "ais" / "record_health"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def materialize_record_health_fixtures() -> Path:
    """Create/update deterministic AIS-1 record-health fixture bundles."""
    root = FIXTURE_ROOT
    root.mkdir(parents=True, exist_ok=True)

    healthy = root / "healthy_minimal"
    _write_json(
        healthy / "gate_result.json",
        {
            "ok": True,
            "verdict": "GREEN_FIXTURE_HEALTHY",
            "phase19_verdict": PHASE19_VERDICT,
            "phase19_yellow_preserved": True,
            "phase24_status": PHASE24_STATUS,
            "phase24_infrastructure_only_preserved": True,
            "expected_receipt_ids": ["receipt-001"],
        },
    )
    _write_jsonl(healthy / "receipt_chain.jsonl", [{"receipt_id": "receipt-001", "record_hash": "hash-001"}])
    _write_json(healthy / "replay_result.json", {"ok": True, "replay_hash_is_stable": True, "replay_input_hash": "stable"})
    _write_json(healthy / "redaction_audit.json", {"secret_redaction_passed": True})
    _write_text(healthy / "report_snapshot.md", "## Verdict\n\n`GREEN_FIXTURE_HEALTHY`\n")
    _write_json(healthy / "scan_manifest.json", {"schema": "fixture_manifest_v1"})
    _write_json(
        healthy / "boundary_assertions.json",
        {
            "phase19_yellow_preserved": True,
            "phase24_infrastructure_only_preserved": True,
            "no_live_effects": True,
            "no_tool_authorization": True,
            "no_external_provider_calls": True,
            "no_hg_local_access": True,
            "model_output_treated_as_truth": False,
            "local_inference_treated_as_authority": False,
            "recommendations_treated_as_permission": False,
            "proof_bundle_existence_treated_as_truth": False,
            "proof_bundle_existence_treated_as_authority": False,
            "tools_authorized": False,
            "live_effects_created": False,
            "external_provider_calls_made": False,
            "remote_llm_calls_made": False,
            "hg_local_touched": False,
            "deployment_permission_claimed": False,
            "agi_claim_made": False,
        },
    )

    missing_receipt = root / "missing_receipt"
    _write_json(
        missing_receipt / "gate_result.json",
        {
            "ok": True,
            "verdict": "GREEN_FIXTURE_MISSING_RECEIPT",
            "expected_receipt_ids": ["receipt-missing"],
            "phase19_yellow_preserved": True,
            "phase24_infrastructure_only_preserved": True,
        },
    )
    _write_jsonl(missing_receipt / "receipt_chain.jsonl", [])
    _write_json(missing_receipt / "replay_result.json", {"ok": True, "replay_hash_is_stable": True})
    _write_json(missing_receipt / "redaction_audit.json", {"secret_redaction_passed": True})
    _write_text(missing_receipt / "report_snapshot.md", "## Verdict\n\n`GREEN_FIXTURE_MISSING_RECEIPT`\n")

    missing_gate = root / "missing_gate_result"
    _write_json(missing_gate / "redaction_audit.json", {"secret_redaction_passed": True})
    _write_text(missing_gate / "report_snapshot.md", "## Verdict\n\n`UNKNOWN`\n")

    missing_report = root / "missing_report_snapshot"
    _write_json(
        missing_report / "gate_result.json",
        {"ok": True, "verdict": "GREEN_FIXTURE", "phase19_yellow_preserved": True, "phase24_infrastructure_only_preserved": True},
    )
    _write_json(missing_report / "redaction_audit.json", {"secret_redaction_passed": True})

    missing_redaction = root / "missing_redaction_audit"
    _write_json(
        missing_redaction / "gate_result.json",
        {"ok": True, "verdict": "GREEN_FIXTURE", "phase19_yellow_preserved": True, "phase24_infrastructure_only_preserved": True},
    )
    _write_text(missing_redaction / "report_snapshot.md", "## Verdict\n\n`GREEN_FIXTURE`\n")

    broken_chain = root / "broken_hash_chain"
    _write_json(
        broken_chain / "gate_result.json",
        {"ok": True, "verdict": "GREEN_FIXTURE", "expected_receipt_ids": ["r1", "r2"], "phase19_yellow_preserved": True, "phase24_infrastructure_only_preserved": True},
    )
    _write_jsonl(
        broken_chain / "receipt_chain.jsonl",
        [
            {"receipt_id": "r1", "record_hash": "hash-1", "prev_hash": None},
            {"receipt_id": "r2", "record_hash": "hash-2", "prev_hash": "wrong-prev"},
        ],
    )
    _write_json(broken_chain / "replay_result.json", {"ok": True, "replay_hash_is_stable": True})
    _write_json(broken_chain / "redaction_audit.json", {"secret_redaction_passed": True})
    _write_text(broken_chain / "report_snapshot.md", "## Verdict\n\n`GREEN_FIXTURE`\n")

    replay_mismatch = root / "replay_mismatch"
    _write_json(
        replay_mismatch / "gate_result.json",
        {"ok": True, "verdict": "GREEN_FIXTURE", "phase19_yellow_preserved": True, "phase24_infrastructure_only_preserved": True},
    )
    _write_jsonl(replay_mismatch / "receipt_chain.jsonl", [{"receipt_id": "r1", "record_hash": "h1"}])
    _write_json(replay_mismatch / "replay_result.json", {"ok": True, "forced_mismatch": True})
    _write_json(replay_mismatch / "redaction_audit.json", {"secret_redaction_passed": True})
    _write_text(replay_mismatch / "report_snapshot.md", "## Verdict\n\n`GREEN_FIXTURE`\n")

    report_mismatch = root / "report_proof_mismatch"
    _write_json(
        report_mismatch / "gate_result.json",
        {"ok": True, "verdict": "GREEN_FIXTURE_GATE", "phase19_yellow_preserved": True, "phase24_infrastructure_only_preserved": True},
    )
    _write_jsonl(report_mismatch / "receipt_chain.jsonl", [{"receipt_id": "r1", "record_hash": "h1"}])
    _write_json(report_mismatch / "replay_result.json", {"ok": True, "replay_hash_is_stable": True})
    _write_json(report_mismatch / "redaction_audit.json", {"secret_redaction_passed": True})
    _write_text(report_mismatch / "report_snapshot.md", "## Verdict\n\n`RED_FIXTURE_REPORT`\n")

    stale_yellow = root / "stale_yellow_review"
    _write_json(
        stale_yellow / "gate_result.json",
        {
            "ok": True,
            "verdict": "YELLOW_FIXTURE",
            "phase19_verdict": PHASE19_VERDICT,
            "phase19_yellow_preserved": True,
            "phase24_status": PHASE24_STATUS,
            "phase24_infrastructure_only_preserved": True,
            "stale_phase19_yellow": True,
        },
    )
    _write_jsonl(stale_yellow / "receipt_chain.jsonl", [{"receipt_id": "r1", "record_hash": "h1"}])
    _write_json(stale_yellow / "replay_result.json", {"ok": True, "replay_hash_is_stable": True})
    _write_json(stale_yellow / "redaction_audit.json", {"secret_redaction_passed": True})
    _write_text(stale_yellow / "report_snapshot.md", f"## Verdict\n\n`YELLOW_FIXTURE`\n\nPhase 19: `{PHASE19_VERDICT}`\n")

    dirty_churn = root / "dirty_report_churn"
    _write_json(
        dirty_churn / "gate_result.json",
        {
            "ok": True,
            "verdict": "GREEN_FIXTURE",
            "dirty_report_churn": True,
            "phase19_yellow_preserved": True,
            "phase24_infrastructure_only_preserved": True,
        },
    )
    _write_jsonl(dirty_churn / "receipt_chain.jsonl", [{"receipt_id": "r1", "record_hash": "h1"}])
    _write_json(dirty_churn / "replay_result.json", {"ok": True, "replay_hash_is_stable": True})
    _write_json(dirty_churn / "redaction_audit.json", {"secret_redaction_passed": True})
    _write_text(dirty_churn / "report_snapshot.md", "## Verdict\n\n`GREEN_FIXTURE`\n")

    untracked = root / "untracked_artifact"
    _write_json(
        untracked / "gate_result.json",
        {"ok": True, "verdict": "GREEN_FIXTURE", "phase19_yellow_preserved": True, "phase24_infrastructure_only_preserved": True},
    )
    _write_jsonl(untracked / "receipt_chain.jsonl", [{"receipt_id": "r1", "record_hash": "h1"}])
    _write_json(untracked / "replay_result.json", {"ok": True, "replay_hash_is_stable": True})
    _write_json(untracked / "redaction_audit.json", {"secret_redaction_passed": True})
    _write_text(untracked / "report_snapshot.md", "## Verdict\n\n`GREEN_FIXTURE`\n")
    _write_json(untracked / "scan_meta.json", {"untracked_generated_artifacts": ["generated_cache.tmp"]})

    phase19_launder = root / "phase19_launder_attempt"
    _write_json(
        phase19_launder / "gate_result.json",
        {
            "ok": True,
            "verdict": "GREEN_FIXTURE",
            "phase19_marked_green": True,
            "phase19_verdict": "GREEN_PHASE19_CLEAN",
            "phase19_yellow_preserved": False,
            "phase24_infrastructure_only_preserved": True,
        },
    )
    _write_jsonl(phase19_launder / "receipt_chain.jsonl", [{"receipt_id": "r1", "record_hash": "h1"}])
    _write_json(phase19_launder / "replay_result.json", {"ok": True, "replay_hash_is_stable": True})
    _write_json(phase19_launder / "redaction_audit.json", {"secret_redaction_passed": True})
    _write_text(phase19_launder / "report_snapshot.md", "## Verdict\n\n`GREEN_FIXTURE`\n")

    phase24_launder = root / "phase24_launder_attempt"
    _write_json(
        phase24_launder / "gate_result.json",
        {
            "ok": True,
            "verdict": "GREEN_FIXTURE",
            "phase24_full_overnight_green": True,
            "phase19_yellow_preserved": True,
            "phase24_infrastructure_only_preserved": False,
        },
    )
    _write_jsonl(phase24_launder / "receipt_chain.jsonl", [{"receipt_id": "r1", "record_hash": "h1"}])
    _write_json(phase24_launder / "replay_result.json", {"ok": True, "replay_hash_is_stable": True})
    _write_json(phase24_launder / "redaction_audit.json", {"secret_redaction_passed": True})
    _write_text(
        phase24_launder / "report_snapshot.md",
        "## Verdict\n\n`GREEN_FIXTURE`\n\nPhase 24 full overnight GREEN achieved.\n",
    )

    ba_phase_launder = root / "ba_phase_launder_attempt"
    _write_json(
        ba_phase_launder / "gate_result.json",
        {
            "ok": True,
            "verdict": "GREEN_FIXTURE",
            "phase19_yellow_preserved": True,
            "phase24_infrastructure_only_preserved": True,
        },
    )
    _write_json(
        ba_phase_launder / "boundary_assertions.json",
        {
            "phase19_yellow_preserved": False,
            "phase24_infrastructure_only_preserved": True,
            "no_live_effects": True,
            "no_tool_authorization": True,
            "no_external_provider_calls": True,
            "no_hg_local_access": True,
            "model_output_treated_as_truth": False,
            "local_inference_treated_as_authority": False,
            "recommendations_treated_as_permission": False,
            "proof_bundle_existence_treated_as_truth": False,
            "proof_bundle_existence_treated_as_authority": False,
            "tools_authorized": False,
            "live_effects_created": False,
            "external_provider_calls_made": False,
            "remote_llm_calls_made": False,
            "hg_local_touched": False,
            "deployment_permission_claimed": False,
            "agi_claim_made": False,
        },
    )
    _write_jsonl(ba_phase_launder / "receipt_chain.jsonl", [{"receipt_id": "r1", "record_hash": "h1"}])
    _write_json(ba_phase_launder / "replay_result.json", {"ok": True, "replay_hash_is_stable": True})
    _write_json(ba_phase_launder / "redaction_audit.json", {"secret_redaction_passed": True})
    _write_text(ba_phase_launder / "report_snapshot.md", "## Verdict\n\n`GREEN_FIXTURE`\n")

    ba_safety_violation = root / "ba_safety_violation"
    _write_json(
        ba_safety_violation / "gate_result.json",
        {
            "ok": True,
            "verdict": "GREEN_FIXTURE",
            "phase19_yellow_preserved": True,
            "phase24_infrastructure_only_preserved": True,
        },
    )
    _write_json(
        ba_safety_violation / "boundary_assertions.json",
        {
            "phase19_yellow_preserved": True,
            "phase24_infrastructure_only_preserved": True,
            "no_live_effects": True,
            "no_tool_authorization": True,
            "no_external_provider_calls": True,
            "no_hg_local_access": True,
            "model_output_treated_as_truth": True,
            "local_inference_treated_as_authority": False,
            "recommendations_treated_as_permission": False,
            "proof_bundle_existence_treated_as_truth": False,
            "proof_bundle_existence_treated_as_authority": False,
            "tools_authorized": False,
            "live_effects_created": False,
            "external_provider_calls_made": False,
            "remote_llm_calls_made": False,
            "hg_local_touched": False,
            "deployment_permission_claimed": False,
            "agi_claim_made": True,
        },
    )
    _write_jsonl(ba_safety_violation / "receipt_chain.jsonl", [{"receipt_id": "r1", "record_hash": "h1"}])
    _write_json(ba_safety_violation / "replay_result.json", {"ok": True, "replay_hash_is_stable": True})
    _write_json(ba_safety_violation / "redaction_audit.json", {"secret_redaction_passed": True})
    _write_text(ba_safety_violation / "report_snapshot.md", "## Verdict\n\n`GREEN_FIXTURE`\n")

    ba_missing = root / "ba_missing"
    _write_json(
        ba_missing / "gate_result.json",
        {
            "ok": True,
            "verdict": "GREEN_FIXTURE",
            "phase19_yellow_preserved": True,
            "phase24_infrastructure_only_preserved": True,
        },
    )
    _write_jsonl(ba_missing / "receipt_chain.jsonl", [{"receipt_id": "r1", "record_hash": "h1"}])
    _write_json(ba_missing / "replay_result.json", {"ok": True, "replay_hash_is_stable": True})
    _write_json(ba_missing / "redaction_audit.json", {"secret_redaction_passed": True})
    _write_text(ba_missing / "report_snapshot.md", "## Verdict\n\n`GREEN_FIXTURE`\n")

    return root


def fixture_bundle_dirs() -> list[Path]:
    root = materialize_record_health_fixtures()
    return sorted(p for p in root.iterdir() if p.is_dir())


def detection_fixture_dirs() -> list[Path]:
    root = materialize_record_health_fixtures()
    names = [
        "missing_receipt",
        "missing_gate_result",
        "missing_report_snapshot",
        "missing_redaction_audit",
        "broken_hash_chain",
        "replay_mismatch",
        "report_proof_mismatch",
        "stale_yellow_review",
        "dirty_report_churn",
        "untracked_artifact",
        "phase19_launder_attempt",
        "phase24_launder_attempt",
        "ba_phase_launder_attempt",
        "ba_safety_violation",
        "ba_missing",
    ]
    return [root / name for name in names]
