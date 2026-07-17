"""Run DTX pipeline for soak replay."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.document_text_exchange.dtx_dib_runner import run_dtx_dib_extraction
from hg_runtime.document_text_exchange.dtx_packet_evaluation import evaluate_document_packets
from hg_runtime.document_text_exchange.dtx_stable_hash import stable_pipeline_hash


def run_dtx_pipeline(root: Path) -> dict:
    bridge = run_dtx_dib_extraction(root)
    evaluation = evaluate_document_packets(bridge)
    return {
        "bridge_layer": bridge,
        "evaluation_layer": evaluation,
        "stable_hash": stable_pipeline_hash(bridge, evaluation),
        "dtx_manifest_ref": bridge["corpus_records"]["dtx_manifest"]["manifest_id"],
    }
