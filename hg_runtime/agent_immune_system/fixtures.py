"""AIS-0 deterministic fixtures."""

from __future__ import annotations

from hg_runtime.agent_immune_system.fever import build_fever_report
from hg_runtime.agent_immune_system.finding import build_finding
from hg_runtime.agent_immune_system.health_signal import build_health_signal
from hg_runtime.agent_immune_system.immune_memory import build_immune_memory_record
from hg_runtime.agent_immune_system.quarantine import build_quarantine_record


def fixture_health_signal() -> dict:
    return build_health_signal(
        signal_id="hs-fixture-001",
        source_component="AISRecordAuditor",
        signal_type="missing_receipt",
        severity="RED",
        evidence_ref="fixtures/ais/missing_receipt_01",
    )


def fixture_fever_report() -> dict:
    return build_fever_report(
        report_id="fr-fixture-001",
        level="RED_FEVER",
        contributing_signals=["hs-fixture-001"],
        restrictions=["restrict_mode"],
        replay_input_hash="replay-fixture-hash",
    )


def fixture_record_health_finding() -> dict:
    return build_finding(
        record_type="record_health_finding_v1",
        finding_id="rh-fixture-001",
        finding_type="missing_receipt",
        severity="RED",
        safe_action="REQUEST_OPERATOR_REVIEW",
        blocks_green=True,
    )


def fixture_quarantine_record() -> dict:
    return build_quarantine_record(
        quarantine_id="q-fixture-001",
        artifact_type="proof_bundle",
        original_ref="docs/proofs/autonomous_agent_zero/SUSPECT/",
        content_hash="abc123",
        reason="report_proof_mismatch",
        review_task_id="irt-fixture-001",
    )


def fixture_immune_memory_record() -> dict:
    return build_immune_memory_record(
        memory_id="im-fixture-001",
        memory_type="incident",
        summary="Phase 19 debug dispatch pollution remains YELLOW",
        signature_id="phase19_debug_dispatch_pollution",
        phase_ref="Phase 19",
    )


def authority_grant_attempt_fixture() -> dict:
    return {
        "schema_version": "1",
        "record_type": "immune_review_task_v1",
        "task_id": "irt-auth-attempt",
        "permit_granted": True,
        "tool_authorization": True,
        "authority_granted": True,
    }


def automatic_patch_attempt_fixture() -> dict:
    return {
        "schema_version": "1",
        "record_type": "patch_hygiene_task_v1",
        "task_id": "ph-auto-attempt",
        "status": "APPLIED",
        "automatic_patching_allowed": True,
    }


def fever_unlock_attempt_fixture() -> dict:
    return {
        "schema_version": "1",
        "record_type": "fever_report_v1",
        "report_id": "fr-unlock-attempt",
        "level": "PANIC_FEVER",
        "unlock_actions": ["grant_live_permit"],
    }


def deletion_attempt_fixture() -> dict:
    return {
        "schema_version": "1",
        "record_type": "quarantine_record_v1",
        "quarantine_id": "q-delete-attempt",
        "deletion_performed": True,
        "quarantine_is_not_deletion": False,
    }
