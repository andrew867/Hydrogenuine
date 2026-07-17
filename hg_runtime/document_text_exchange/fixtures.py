"""Deterministic DTX-0 schema foundation fixtures."""

from __future__ import annotations

from hg_runtime.document_text_exchange.document_corpus import (
    build_dtx_document_fixture,
    build_dtx_expected_outcome,
    build_dtx_extraction_exchange_record,
    build_dtx_leb_bridge_record,
    build_dtx_packet_exchange_record,
    build_safe_text_document_exchange,
)
from hg_runtime.document_text_exchange.dtx_manifest import build_dtx_manifest
from hg_runtime.document_text_exchange.dtx_policy import build_dtx_boundary_policy
from hg_runtime.document_text_exchange.dtx_soak import build_dtx_soak_iteration
from hg_runtime.document_text_exchange.schemas import DOCUMENT_FIXTURE_FAMILIES, EXPECTED_OUTCOME_TYPES


def build_dtx0_fixture_records() -> dict:
    policy = build_dtx_boundary_policy()
    exchange = build_safe_text_document_exchange(exchange_id="dtx0-exchange-fixture", manifest_id="dtx0-manifest-fixture")
    manifest = build_dtx_manifest(
        manifest_id="dtx0-manifest-fixture",
        fixture_paths=[f"{policy['approved_root']}/family_01/plain_support.txt"],
        fixture_ids=["dtx-fixture-001"],
        family_ids=["PLAIN_TEXT_SUPPORT"],
    )
    fixture = build_dtx_document_fixture(
        fixture_id="dtx-fixture-001",
        family_id="PLAIN_TEXT_SUPPORT",
        path_ref=f"{policy['approved_root']}/family_01/plain_support.txt",
        logical_key="dtx.fixture.plain",
        media_type="text/plain",
    )
    outcome = build_dtx_expected_outcome(
        outcome_id="dtx-outcome-001",
        fixture_id=fixture["fixture_id"],
        family_id="PLAIN_TEXT_SUPPORT",
        outcome_type="PLAIN_TEXT_EXCHANGE_RECORDED",
    )
    extraction = build_dtx_extraction_exchange_record(
        exchange_record_id="dtx-extract-001",
        fixture_id=fixture["fixture_id"],
        extraction_receipt_id="dtx-receipt-001",
        content_hash="fixture-content-hash",
    )
    bridge = build_dtx_leb_bridge_record(
        bridge_id="dtx-bridge-001",
        fixture_id=fixture["fixture_id"],
        adapter_record_id="dtx-adapter-001",
        source_id="dtx-src-001",
    )
    packet = build_dtx_packet_exchange_record(
        packet_id="dtx-packet-001",
        fixture_id=fixture["fixture_id"],
        family_id="PLAIN_TEXT_SUPPORT",
        claim_text="Fixture claim for DTX schema foundation.",
    )
    soak = build_dtx_soak_iteration(
        iteration_id="dtx-soak-001",
        iteration_number=1,
        stable_hash="fixture-stable-hash",
        replay_match=True,
    )
    return {
        "dtx_boundary_policy": policy,
        "safe_text_document_exchange": exchange,
        "dtx_manifest": manifest,
        "dtx_document_fixture": fixture,
        "dtx_expected_outcome": outcome,
        "dtx_extraction_exchange_record": extraction,
        "dtx_leb_bridge_record": bridge,
        "dtx_packet_exchange_record": packet,
        "dtx_soak_iteration": soak,
        "document_fixture_families": sorted(DOCUMENT_FIXTURE_FAMILIES),
        "expected_outcome_types": sorted(EXPECTED_OUTCOME_TYPES),
    }


def build_dtx1_corpus_layer(*, root=None) -> dict:
    from pathlib import Path

    from hg_runtime.document_text_exchange.document_corpus_builder import build_document_corpus
    from hg_runtime.document_text_exchange.document_fixture_validator import validate_document_corpus
    from hg_runtime.document_text_exchange.dtx_corpus_replay import replay_corpus_layer

    workspace_root = Path(root) if root else Path(__file__).resolve().parents[2]
    layer = build_document_corpus()
    layer["validation"] = validate_document_corpus(workspace_root, layer)
    layer["replay"] = replay_corpus_layer(layer)
    return layer
