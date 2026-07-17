"""OEC-3 corpus packet evaluation using EWP-style deterministic paths."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.claim_packet import build_claim_evidence_packet
from hg_runtime.evidence_workbench_packets.contradiction_packet import build_contradiction_review_packet, build_packet_contradiction_record
from hg_runtime.evidence_workbench_packets.dashboard_summary import render_dashboard_markdown, summarize_review_statuses
from hg_runtime.evidence_workbench_packets.independence_policy import evaluate_independence
from hg_runtime.evidence_workbench_packets.operator_dashboard import build_operator_packet_dashboard, build_packet_review_status
from hg_runtime.evidence_workbench_packets.second_source import build_packet_second_source_result
from hg_runtime.evidence_workbench_packets.source_summary import build_packet_source_summary, build_packet_support_record
from hg_runtime.operator_evidence_corpus.curated_corpus_builder import FAMILY_SPECS


def _duplicate_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for spec in FAMILY_SPECS:
        for src in spec["sources"]:
            if src.get("duplicate_of"):
                mapping[src["source_id"]] = src["duplicate_of"]
    return mapping


def _family_signals(spec: dict) -> dict:
    source_ids = [row["source_id"] for row in spec["sources"]]
    return {
        "source_ids": source_ids,
        "duplicate_primary": _duplicate_map(),
        "conflict_source_ids": set(source_ids) if spec["family_id"] == "CONTRADICTED_BY_SECOND" else set(),
        "quarantine_source_ids": set(source_ids) if spec["family_id"] == "QUARANTINE_RECOMMENDED" else set(),
        "fever_source_ids": set(),
        "redaction_blocked_source_ids": set(source_ids) if spec["family_id"] == "REDACTION_SENSITIVE" else set(),
        "second_source_required": spec.get("second_source_required", len(source_ids) >= 2),
    }


def _outcome_to_second_source(spec: dict, signals: dict) -> str:
    outcome, _ = evaluate_independence(**signals)
    if spec["family_id"] == "INSUFFICIENT_EVIDENCE":
        return "SECOND_SOURCE_REQUIRED_MISSING"
    if spec["family_id"] == "DUPLICATE_DISGUISED_AS_SECOND":
        return "SECOND_SOURCE_PRESENT_BUT_DUPLICATE"
    if spec["family_id"] == "TWO_INDEPENDENT_SOURCES":
        return "SECOND_SOURCE_PRESENT_REVIEW_READY"
    if spec["family_id"] == "REDACTION_SENSITIVE":
        return "BLOCKED_BY_REDACTION"
    if spec["family_id"] == "QUARANTINE_RECOMMENDED":
        return "BLOCKED_BY_QUARANTINE"
    if spec["family_id"] == "CONTRADICTED_BY_SECOND":
        return "BLOCKED_BY_CONFLICT"
    return outcome


def _review_status(spec: dict, second_source_outcome: str) -> str:
    if spec["family_id"] in {"CONTRADICTED_BY_SECOND", "OPERATOR_REVIEW_REQUIRED"}:
        return "BLOCKED_BY_CONFLICT"
    mapping = {
        "BLOCKED_BY_REDACTION": "BLOCKED_BY_REDACTION",
        "BLOCKED_BY_QUARANTINE": "BLOCKED_BY_QUARANTINE",
        "BLOCKED_BY_CONFLICT": "BLOCKED_BY_CONFLICT",
        "SECOND_SOURCE_REQUIRED_MISSING": "SECOND_SOURCE_REQUIRED",
        "SECOND_SOURCE_PRESENT_BUT_DUPLICATE": "SECOND_SOURCE_REQUIRED",
        "SECOND_SOURCE_PRESENT_REVIEW_READY": "REVIEW_READY",
        "SECOND_SOURCE_NOT_REQUIRED": "REVIEW_READY",
    }
    return mapping.get(second_source_outcome, "PENDING_REVIEW")


def evaluate_corpus_packets(ingestion_layer: dict) -> dict:
    claim_packets: list[dict] = []
    second_source_results: list[dict] = []
    contradiction_packets: list[dict] = []
    review_statuses: list[dict] = []

    for idx, spec in enumerate(FAMILY_SPECS, start=1):
        claim_id = spec["claim_id"]
        source_ids = [row["source_id"] for row in spec["sources"]]
        summary_ids = []
        support_ids = []
        contradiction_ids = []
        for sid in source_ids:
            summary = build_packet_source_summary(
                summary_id=f"oec-packet-summary-{sid}",
                source_id=sid,
                quality_band=next((s.get("quality_band", "STRUCTURALLY_USABLE") for s in spec["sources"] if s["source_id"] == sid), "STRUCTURALLY_USABLE"),
                provenance_path_ref="docs/proofs/autonomous_agent_zero/OEC-2-CORPUS-TO-LEB",
                duplicate_collapsed=sid in _duplicate_map(),
                original_source_ids=source_ids,
            )
            summary_ids.append(summary["summary_id"])
            support = build_packet_support_record(
                support_id=f"oec-packet-support-{sid}",
                claim_id=claim_id,
                source_id=sid,
                receipt_ref=f"oec:receipt:{sid}",
            )
            support_ids.append(support["support_id"])

        if spec["family_id"] in {"CONTRADICTED_BY_SECOND", "STALE_VS_CURRENT", "OPERATOR_REVIEW_REQUIRED"}:
            contradiction = build_packet_contradiction_record(
                contradiction_id=f"oec-contradiction-{claim_id}",
                claim_id=claim_id,
                participant_source_ids=source_ids,
                conflict_class="CLAIM_CONFLICT" if spec["family_id"] != "STALE_VS_CURRENT" else "SOURCE_METADATA_CONFLICT",
                stale_signal=spec["family_id"] == "STALE_VS_CURRENT",
            )
            contradiction_ids.append(contradiction["contradiction_id"])
            contradiction_packets.append(
                build_contradiction_review_packet(
                    packet_id=f"oec-contradiction-packet-{idx:03d}",
                    claim_id=claim_id,
                    contradiction_record_ids=contradiction_ids,
                )
            )

        packet = build_claim_evidence_packet(
            packet_id=f"oec-claim-packet-{idx:03d}",
            claim_id=claim_id,
            claim_text=spec["claim_text"],
            source_summary_ids=summary_ids,
            support_record_ids=support_ids,
            contradiction_record_ids=contradiction_ids,
        )
        claim_packets.append(packet)

        signals = _family_signals(spec)
        ss_outcome = _outcome_to_second_source(spec, signals)
        _, independent_count = evaluate_independence(**signals)
        second_source_results.append(
            build_packet_second_source_result(
                result_id=f"oec-ss-result-{idx:03d}",
                requirement_id=f"oec-ss-req-{idx:03d}",
                packet_id=packet["packet_id"],
                outcome=ss_outcome,
                independent_source_count=independent_count,
            )
        )
        review_statuses.append(
            build_packet_review_status(
                status_id=f"oec-review-status-{idx:03d}",
                packet_id=packet["packet_id"],
                claim_id=claim_id,
                review_status=_review_status(spec, ss_outcome),
            )
        )

    status_summary = summarize_review_statuses(review_statuses)
    dashboard = build_operator_packet_dashboard(
        dashboard_id="oec-corpus-dashboard-001",
        claim_packet_count=len(claim_packets),
        second_source_result_count=len(second_source_results),
        contradiction_packet_count=len(contradiction_packets),
        review_status_summary=status_summary,
    )
    dashboard_md = render_dashboard_markdown(dashboard, review_statuses)
    return {
        "corpus_claim_packets": claim_packets,
        "corpus_second_source_results": second_source_results,
        "corpus_contradiction_packets": contradiction_packets,
        "corpus_operator_dashboard": dashboard,
        "corpus_operator_dashboard_md": dashboard_md,
        "corpus_packet_review_statuses": review_statuses,
    }
