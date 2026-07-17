"""DTX stable hash helpers."""

from __future__ import annotations

from hg_runtime.document_text_exchange.schemas import record_hash


def stable_pipeline_hash(bridge_layer: dict, evaluation_layer: dict) -> str:
    return record_hash(
        {
            "receipts": [row["content_hash"] for row in bridge_layer["dtx_extraction_receipts"]],
            "bridges": [row["adapter_record_id"] for row in bridge_layer["dtx_leb_bridge_records"]],
            "packets": [row["support_record_ids"] for row in evaluation_layer["dtx_claim_packets"]],
            "second_source": [row["outcome"] for row in evaluation_layer["dtx_second_source_results"]],
            "contradiction": [row.get("claim_id") for row in evaluation_layer["dtx_contradiction_packets"]],
            "dashboard_count": evaluation_layer["dtx_operator_dashboard"]["claim_packet_count"],
        }
    )
