"""Build packet source summaries from SQP quality and provenance metadata."""

from __future__ import annotations

from hg_runtime.evidence_workbench_packets.source_summary import build_packet_source_summary


def build_source_summaries(
    *,
    claim_id: str,
    source_ids: list[str],
    quality_by_source: dict[str, str],
    provenance_graph_ref: str,
    duplicate_collapsed: bool,
) -> list[dict]:
    summaries: list[dict] = []
    for sid in source_ids:
        summaries.append(
            build_packet_source_summary(
                summary_id=f"ewp1-summary-{claim_id}-{sid}",
                source_id=sid,
                quality_band=quality_by_source.get(sid, "UNRATED"),
                provenance_path_ref=provenance_graph_ref,
                duplicate_collapsed=duplicate_collapsed and sid != source_ids[0],
                original_source_ids=source_ids if duplicate_collapsed else [sid],
            )
        )
    return summaries
