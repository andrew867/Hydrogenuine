"""LEB-2 local evidence to WMBR linker tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.bridge_replay import replay_wmbr_bridge
from hg_runtime.local_evidence_bridge.claim_linker import build_claim_bridge, build_evidence_claim_link
from hg_runtime.local_evidence_bridge.schemas import PHASE19_VERDICT, PHASE24_STATUS
from hg_runtime.local_evidence_bridge.text_ingestion import ingest_text_source
from hg_runtime.local_evidence_bridge.verification_task_linker import build_verification_task_links
from hg_runtime.local_evidence_bridge.wmbr_bridge_manifest import build_wmbr_bridge_manifest

ROOT = Path(__file__).resolve().parents[2]


def _layer():
    paths = ["tests/fixtures/local_evidence/source_001.md", "tests/fixtures/local_evidence/source_002.txt"]
    rows = [ingest_text_source(ROOT, path, source_id=f"src-{i}") for i, path in enumerate(paths, start=1)]
    receipts = [row["evidence_receipt"] for row in rows]
    bridge = build_claim_bridge(receipts)
    task_links = build_verification_task_links(bridge["links"])
    manifest = build_wmbr_bridge_manifest(
        links=bridge["links"],
        supports=bridge["supports"],
        contradictions=bridge["contradictions"],
        task_links=task_links,
    )
    replay = replay_wmbr_bridge(bridge["links"], bridge["supports"], bridge["contradictions"], task_links, manifest)
    return receipts, bridge["links"], bridge["supports"], bridge["contradictions"], task_links, manifest, replay


def test_leb2_creates_evidence_claim_links():
    _, links, *_ = _layer()
    assert {link["link_kind"] for link in links} == {"SUPPORT_CANDIDATE", "CONTRADICTION_CANDIDATE"}


def test_leb2_support_link_is_not_proof():
    _, links, supports, *_ = _layer()
    assert all(link["support_link_is_not_proof"] for link in links)
    assert all(record["support_link_is_not_proof"] for record in supports)


def test_leb2_contradiction_link_is_not_truth_resolution():
    _, links, _, contradictions, *_ = _layer()
    assert all(link["contradiction_link_is_not_truth_resolution"] for link in links)
    assert all(record["contradiction_link_is_not_truth_resolution"] for record in contradictions)


def test_leb2_evidence_receipt_is_not_automatic_belief_revision():
    _, links, supports, contradictions, task_links, manifest, _ = _layer()
    rows = links + supports + contradictions + task_links + [manifest]
    assert all(row["evidence_receipt_is_not_automatic_belief_revision"] for row in rows)


def test_leb2_does_not_mutate_wmbr03_ledger():
    _, links, _, _, task_links, manifest, _ = _layer()
    assert all(not row["wmbr03_ledger_mutated"] for row in links + task_links)
    assert manifest["bridge_does_not_mutate_wmbr03_ledger"] is True


def test_leb2_creates_reviewable_input_records_only():
    _, links, supports, contradictions, task_links, manifest, _ = _layer()
    rows = links + supports + contradictions + task_links + [manifest]
    assert all(row["reviewable_input_only"] for row in rows)


def test_leb2_creates_wmbr_verification_task_links():
    _, links, _, _, task_links, *_ = _layer()
    assert len(task_links) == len(links)
    assert all(link["task_link_is_not_execution"] for link in task_links)


def test_leb2_no_authority_tools_or_live_effects():
    _, links, supports, contradictions, task_links, manifest, _ = _layer()
    rows = links + supports + contradictions + task_links + [manifest]
    assert all(not row["authority_granted"] for row in rows)
    assert all(not row["tools_authorized"] for row in rows)
    assert all(not row["live_external_side_effects_created"] for row in rows)


def test_leb2_replay_preserves_bridge_hashes():
    *_, replay = _layer()
    assert replay["replay_preserves_bridge_hashes"] is True


def test_leb2_replay_rejects_mutated_link():
    _, links, supports, contradictions, task_links, manifest, _ = _layer()
    mutated = [dict(row) for row in links]
    mutated[0]["record_hash"] = "mutated"
    replay = replay_wmbr_bridge(mutated, supports, contradictions, task_links, manifest)
    assert replay["replay_preserves_bridge_hashes"] is False


def test_leb2_invalid_link_kind_rejected():
    receipts, *_ = _layer()
    try:
        build_evidence_claim_link(link_id="bad", receipt=receipts[0], claim_id="claim", link_kind="PROOF")
    except Exception as exc:
        assert "invalid_link_kind" in str(exc)
    else:
        raise AssertionError("invalid link kind was accepted")


def test_leb2_preserves_phase19_yellow_and_phase24_infrastructure_only():
    assert PHASE19_VERDICT.startswith("YELLOW_PHASE19")
    assert PHASE24_STATUS == "infrastructure_only"
