"""
Interop Pack 5: Cross-domain settlement, incentives, dispute resolution.
"""
from __future__ import annotations

from pathlib import Path

from hg_core.interop import (
    open_dispute,
    load_dispute,
    triage_dispute,
    start_arbitration,
    resolve_dispute,
    publish_settlement,
    load_settlement,
    attest_reputation,
    import_reputation,
    load_reputation_attestation,
)


SCOPE = {"type": "run", "id": "test_iop5"}
ACTOR = {"agent_id": "agent_iop5", "pubkey": "0" * 64, "key_id": "k"}


def test_dispute_open_requires_bundle_ids(tmp_path: Path) -> None:
    """Dispute open requires claim artifact and evidence bundle ids (and optional signatures)."""
    dispute_id = open_dispute(
        claimant_domain="domain_a",
        respondent_domain="domain_b",
        subject_ref={"action_id": "act_1"},
        claim_artifact_id="claim_art_1",
        evidence_bundle_ids=["bundle_1", "bundle_2"],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        bundle_signatures={"bundle_1": "sig1"},
    )
    assert dispute_id.startswith("disp_")
    d = load_dispute(tmp_path, dispute_id)
    assert d is not None
    assert d["claimant_domain"] == "domain_a"
    assert d["evidence_bundle_ids"] == ["bundle_1", "bundle_2"]
    assert d["status"] == "opened"


def test_triage_rejects_incomplete_evidence(tmp_path: Path) -> None:
    """Triage rejects when evidence incomplete (no bundle ids or no claim)."""
    dispute_id = open_dispute(
        claimant_domain="a",
        respondent_domain="b",
        subject_ref={},
        claim_artifact_id="",  # empty
        evidence_bundle_ids=[],  # empty
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    accepted, _ = triage_dispute(dispute_id=dispute_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path, require_evidence_complete=True)
    assert accepted is False
    d = load_dispute(tmp_path, dispute_id)
    assert d["status"] == "rejected"


def test_triage_accepts_complete_evidence(tmp_path: Path) -> None:
    """Triage accepts when claim and evidence bundles present."""
    dispute_id = open_dispute(
        claimant_domain="a",
        respondent_domain="b",
        subject_ref={},
        claim_artifact_id="claim_1",
        evidence_bundle_ids=["b1"],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    accepted, ev = triage_dispute(dispute_id=dispute_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path, require_evidence_complete=True)
    assert accepted is True
    assert ev
    d = load_dispute(tmp_path, dispute_id)
    assert d["status"] == "triage"


def test_arbitration_assigns_arbitrators(tmp_path: Path) -> None:
    """Arbitration assigns independent arbitrators."""
    dispute_id = open_dispute(
        claimant_domain="a",
        respondent_domain="b",
        subject_ref={},
        claim_artifact_id="c1",
        evidence_bundle_ids=["e1"],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    triage_dispute(dispute_id=dispute_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path, require_evidence_complete=True)
    ev = start_arbitration(dispute_id=dispute_id, arbitrator_ids=["arb_1", "arb_2"], scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert ev
    d = load_dispute(tmp_path, dispute_id)
    assert d["status"] == "arbitration"
    assert d.get("arbitrator_ids") == ["arb_1", "arb_2"]


def test_settlement_cannot_publish_without_quorum_proof(tmp_path: Path) -> None:
    """Settlement cannot publish without quorum proof (missing quorum_proof_artifact_id raises)."""
    import pytest
    with pytest.raises(ValueError, match="quorum_proof_artifact_id"):
        publish_settlement(
            dispute_id="disp_any",
            outcome="accept",
            quorum_proof_artifact_id="",
            scope=SCOPE,
            actor=ACTOR,
            workspace_root=tmp_path,
        )


def test_settlement_publish_with_quorum_proof(tmp_path: Path) -> None:
    """Settlement publishes when quorum proof provided."""
    (tmp_path / "artifacts" / "quorum").mkdir(parents=True, exist_ok=True)
    quorum_path = tmp_path / "artifacts" / "quorum" / "proof_1.json"
    quorum_path.write_text("{}", encoding="utf-8")
    settlement_id = publish_settlement(
        dispute_id="disp_1",
        outcome="partial",
        quorum_proof_artifact_id=str(quorum_path),
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert settlement_id.startswith("settle_")
    s = load_settlement(tmp_path, settlement_id)
    assert s is not None
    assert s["outcome"] == "partial"
    assert s["quorum_proof_artifact_id"] == str(quorum_path)


def test_reputation_import_blocked_without_continuity(tmp_path: Path) -> None:
    """Reputation import blocked without continuity and stake linkage."""
    att_id = attest_reputation(subject_did="did:test:alice", domain="domain_x", score=0.9, confidence=0.8, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    accepted, _ = import_reputation(
        attestation_id=att_id,
        target_domain="domain_y",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        require_continuity=True,
        identity_continuity_artifact_id="",
        stake_continuity_artifact_id="",
    )
    assert accepted is False


def test_reputation_import_with_continuity(tmp_path: Path) -> None:
    """Reputation import succeeds with identity and stake continuity artifacts."""
    att_id = attest_reputation(subject_did="did:test:bob", domain="d1", score=0.85, confidence=0.7, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    (tmp_path / "artifacts" / "continuity").mkdir(parents=True, exist_ok=True)
    id_art = tmp_path / "artifacts" / "continuity" / "id_chain.json"
    stake_art = tmp_path / "artifacts" / "continuity" / "stake.json"
    id_art.write_text("{}", encoding="utf-8")
    stake_art.write_text("{}", encoding="utf-8")
    accepted, ev = import_reputation(
        attestation_id=att_id,
        target_domain="d2",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        require_continuity=True,
        identity_continuity_artifact_id=str(id_art),
        stake_continuity_artifact_id=str(stake_art),
    )
    assert accepted is True
    assert ev


def test_dispute_resolve_after_settlement(tmp_path: Path) -> None:
    """Resolve dispute (status -> resolved)."""
    dispute_id = open_dispute(
        claimant_domain="x",
        respondent_domain="y",
        subject_ref={},
        claim_artifact_id="c",
        evidence_bundle_ids=["e"],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    triage_dispute(dispute_id=dispute_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path, require_evidence_complete=True)
    start_arbitration(dispute_id=dispute_id, arbitrator_ids=["arb"], scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    ev = resolve_dispute(dispute_id=dispute_id, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert ev
    d = load_dispute(tmp_path, dispute_id)
    assert d["status"] == "resolved"


def test_load_reputation_attestation(tmp_path: Path) -> None:
    """Load reputation attestation by id."""
    att_id = attest_reputation(subject_did="did:test:carol", domain="d", score=0.5, confidence=0.5, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    a = load_reputation_attestation(tmp_path, att_id)
    assert a is not None
    assert a["subject_did"] == "did:test:carol"
    assert a["domain"] == "d"
