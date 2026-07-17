"""DTX-3 document packet evaluation."""

from __future__ import annotations

from hg_runtime.document_text_exchange.dtx_contradiction_eval import build_contradiction_artifacts
from hg_runtime.document_text_exchange.dtx_dashboard_eval import build_dashboard
from hg_runtime.document_text_exchange.dtx_second_source_eval import family_signals, outcome_to_second_source
from hg_runtime.document_text_exchange.document_corpus_builder import FAMILY_SPECS
from hg_runtime.document_text_exchange.schemas import assert_neutral, neutral_flags, record_hash
from hg_runtime.evidence_workbench_packets.claim_packet import build_claim_evidence_packet
from hg_runtime.evidence_workbench_packets.independence_policy import evaluate_independence
from hg_runtime.evidence_workbench_packets.operator_dashboard import build_packet_review_status
from hg_runtime.evidence_workbench_packets.second_source import build_packet_second_source_result
from hg_runtime.evidence_workbench_packets.source_summary import build_packet_source_summary, build_packet_support_record


def evaluate_document_packets(bridge_layer: dict) -> dict:
    claim_packets: list[dict] = []
    second_source_results: list[dict] = []
    contradiction_packets: list[dict] = []
    review_statuses: list[dict] = []

    for idx, spec in enumerate(FAMILY_SPECS, start=1):
        claim_id = spec["fixture_id"]
        doc_ids = [doc["doc_id"] for doc in spec["documents"]]
        summary_ids: list[str] = []
        support_ids: list[str] = []
        for doc in spec["documents"]:
            sid = doc["doc_id"]
            summary = build_packet_source_summary(
                summary_id=f"dtx-packet-summary-{sid}",
                source_id=sid,
                quality_band=doc.get("quality_band", "STRUCTURALLY_USABLE"),
                provenance_path_ref="docs/proofs/autonomous_agent_zero/DTX-2-DIB-TO-LEB-BRIDGE",
                duplicate_collapsed=sid in family_signals(spec)["duplicate_primary"],
                original_source_ids=doc_ids,
            )
            summary_ids.append(summary["summary_id"])
            support = build_packet_support_record(
                support_id=f"dtx-packet-support-{sid}",
                claim_id=claim_id,
                source_id=sid,
                receipt_ref=f"dtx:receipt:{sid}",
            )
            support_ids.append(support["support_id"])

        contradiction_ids, contradiction_packet = build_contradiction_artifacts(spec=spec, claim_id=claim_id)
        if contradiction_packet:
            contradiction_packets.append(contradiction_packet)

        packet = build_claim_evidence_packet(
            packet_id=f"dtx-claim-packet-{idx:03d}",
            claim_id=claim_id,
            claim_text=spec["claim_text"],
            source_summary_ids=summary_ids,
            support_record_ids=support_ids,
            contradiction_record_ids=contradiction_ids,
        )
        claim_packets.append(packet)

        signals = family_signals(spec)
        independence_outcome, independent_count = evaluate_independence(**signals)
        ss_outcome = outcome_to_second_source(spec, independence_outcome)
        second_source_results.append(
            build_packet_second_source_result(
                result_id=f"dtx-ss-result-{idx:03d}",
                requirement_id=f"dtx-ss-req-{idx:03d}",
                packet_id=packet["packet_id"],
                outcome=ss_outcome,
                independent_source_count=independent_count,
            )
        )
        if spec["family_id"] in {"CONTRADICTORY_TEXT", "STALE_TEXT"}:
            review_status = "BLOCKED_BY_CONFLICT"
        elif ss_outcome == "BLOCKED_BY_REDACTION":
            review_status = "BLOCKED_BY_REDACTION"
        elif ss_outcome in {"SECOND_SOURCE_PRESENT_BUT_DUPLICATE", "SECOND_SOURCE_REQUIRED_MISSING"}:
            review_status = "SECOND_SOURCE_REQUIRED"
        else:
            review_status = "REVIEW_READY"
        review_statuses.append(
            build_packet_review_status(
                status_id=f"dtx-review-status-{idx:03d}",
                packet_id=packet["packet_id"],
                claim_id=claim_id,
                review_status=review_status,
            )
        )

    dashboard, dashboard_md = build_dashboard(
        claim_packets=claim_packets,
        second_source_results=second_source_results,
        contradiction_packets=contradiction_packets,
        review_statuses=review_statuses,
    )
    manifest = {
        "manifest_id": "dtx-packet-evaluation-manifest-v1",
        "packet_count": len(claim_packets),
        "second_source_count": len(second_source_results),
        "contradiction_count": len(contradiction_packets),
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return {
        "dtx_claim_packets": claim_packets,
        "dtx_second_source_results": second_source_results,
        "dtx_contradiction_packets": contradiction_packets,
        "dtx_operator_dashboard": dashboard,
        "dtx_operator_dashboard_md": dashboard_md,
        "dtx_packet_review_statuses": review_statuses,
        "dtx_packet_evaluation_manifest": manifest,
    }
