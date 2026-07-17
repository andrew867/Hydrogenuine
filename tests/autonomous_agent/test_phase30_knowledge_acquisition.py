"""Phase 30 governed knowledge-acquisition-loop tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_runtime.memory_ledger.ledger import PersistentMemoryLedger
from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.knowledge_acquisition import (
    KnowledgeAcquisitionError,
    KnowledgeAcquisitionLog,
    audit_mini_task_result,
    build_acquisition_outcome_receipt,
    build_domain_readiness_record,
    build_skill_candidate,
    create_citation,
    create_claim_record,
    create_glossary_entry,
    define_mini_task,
    detect_contradictions,
    extract_concept,
    ingest_source,
    link_evidence,
    promote_to_memory,
    request_memory_promotion,
    require_review_if_stale,
    review_freshness,
    source_quality_is_advisory,
    trust_result,
)
from hg_runtime.knowledge_acquisition.gate import evaluate_phase30_gate, validate_phase30_proof_bundle

NOW = "2026-06-19T15:00:00.000000Z"


def _source(**overrides):
    payload = {
        "source_id": "src-1",
        "kind": "local_file",
        "locator": "fixtures/phase30/intro.md",
        "retrieved_at": NOW,
        "content": "governed acquisition primer",
        "claim_boundary": "governed_acquisition_advisory_default",
    }
    payload.update(overrides)
    return payload


def _citation(**overrides):
    payload = {
        "citation_id": "cit-1",
        "source_id": "src-1",
        "locator": "line:12",
        "excerpt": "acquisition is governed",
    }
    payload.update(overrides)
    return payload


def _claim(**overrides):
    payload = {
        "claim_id": "clm-1",
        "statement": "the loop is governed",
        "evidence_refs": ["ev-1"],
        "source_refs": ["src-1"],
        "status": "supported",
    }
    payload.update(overrides)
    return payload


def _promotion(**overrides):
    payload = {
        "promotion_id": "promo-1",
        "target_memory": "domain:acquisition",
        "claim_refs": ["clm-1"],
        "citation_refs": ["cit-1"],
        "audit_refs": ["audit-1"],
        "source_refs": ["src-1"],
        "claim_boundary": "governed_acquisition_advisory_default",
    }
    payload.update(overrides)
    return payload


def _audit(**overrides):
    payload = {
        "task_id": "task-1",
        "outcome": "passed",
        "auditor": "phase30",
        "findings": ["matches expected"],
        "receipt_refs": ["receipt:phase30:test"],
    }
    payload.update(overrides)
    return payload


# --- source ingest -----------------------------------------------------------

def test_source_ingest_requires_artifact_hash():
    with pytest.raises(KnowledgeAcquisitionError, match="source_ingest_requires_artifact_hash"):
        ingest_source(_source(content=None))


def test_source_ingest_hashes_content():
    src = ingest_source(_source())
    assert src["artifact_hash"].startswith("sha256:")


def test_network_acquisition_refuses_by_default():
    with pytest.raises(KnowledgeAcquisitionError, match="network_acquisition_refuses_by_default"):
        ingest_source(_source(kind="network", locator="https://example.invalid/doc"))


def test_credential_source_read_is_rejected():
    with pytest.raises(KnowledgeAcquisitionError, match="credential_source_read_rejected"):
        ingest_source(_source(locator=".hg-local/secrets/social.env"))


def test_source_treated_as_authority_is_rejected():
    with pytest.raises(KnowledgeAcquisitionError, match="source_authority_rejected"):
        ingest_source(_source(source_as_authority=True))


def test_source_quality_score_is_advisory_only():
    advisory = source_quality_is_advisory(_source(quality_score=0.99))
    assert advisory["advisory_only"] is True
    assert advisory["promotes_automatically"] is False


# --- citations ---------------------------------------------------------------

def test_source_citation_requires_locator():
    with pytest.raises(KnowledgeAcquisitionError, match="source_citation_requires_locator"):
        create_citation(_citation(locator=""))


# --- concepts & glossary -----------------------------------------------------

def test_concept_requires_source_refs():
    with pytest.raises(KnowledgeAcquisitionError, match="concept_requires_source_refs"):
        extract_concept({"concept_id": "c1", "term": "ledger", "definition": "append-only", "source_refs": []})


def test_glossary_update_requires_evidence():
    with pytest.raises(KnowledgeAcquisitionError, match="glossary_update_requires_evidence"):
        create_glossary_entry({"term": "ledger", "definition": "append-only log", "evidence_refs": []})


def test_glossary_entry_cannot_override_domain_pack():
    pack = {"pack_id": "acq", "locked_terms": ["authority"]}
    with pytest.raises(KnowledgeAcquisitionError, match="glossary_entry_cannot_override_domain_pack"):
        create_glossary_entry(
            {"term": "authority", "definition": "redefined", "evidence_refs": ["ev-1"]},
            domain_pack=pack,
        )


# --- claims ------------------------------------------------------------------

def test_unsourced_claim_is_marked_tbd():
    claim = create_claim_record(_claim(evidence_refs=[], source_refs=[], status="supported"))
    assert claim["status"] == "tbd"
    assert claim["supported"] is False


def test_unsupported_claim_cannot_be_green():
    claim = create_claim_record(_claim(evidence_refs=[], source_refs=[], status="green"))
    assert claim["status"] == "tbd"
    assert claim["supported"] is False


def test_source_claim_link_is_required():
    with pytest.raises(KnowledgeAcquisitionError, match="source_claim_link_required"):
        create_claim_record(_claim(evidence_refs=["ev-1"], source_refs=[], status="supported"))


def test_single_source_claim_is_limited_scope():
    claim = create_claim_record(_claim(source_refs=["src-1"]))
    assert claim["scope"] == "limited_single_source"
    assert claim["single_source"] is True


def test_contradictory_claims_are_flagged():
    claims = [
        {"claim_id": "a", "subject": "metal_conducts", "polarity": True},
        {"claim_id": "b", "subject": "metal_conducts", "polarity": False},
    ]
    assert detect_contradictions(claims) == ["a", "b"]


def test_acquired_knowledge_cannot_authorize_tools():
    with pytest.raises(KnowledgeAcquisitionError, match="authority_bypass_attempt:authorizes_tool"):
        create_claim_record(_claim(authorizes_tool=True))


def test_acquired_knowledge_cannot_widen_authority():
    with pytest.raises(KnowledgeAcquisitionError, match="authority_bypass_attempt:widens_authority"):
        create_claim_record(_claim(widens_authority=True))


# --- evidence ----------------------------------------------------------------

def test_evidence_link_binds_claim_to_source():
    link = link_evidence({"evidence_id": "ev-1", "claim_id": "clm-1", "citation_id": "cit-1", "source_id": "src-1"})
    assert link["schema"] == "evidence_link_v1"
    assert link["tool_authorized"] is False


# --- freshness ---------------------------------------------------------------

def test_stale_source_requires_review():
    review = review_freshness({"source_id": "src-1", "status": "stale", "reviewed_at": NOW})
    with pytest.raises(KnowledgeAcquisitionError, match="stale_source_requires_review"):
        require_review_if_stale(review)


def test_reviewed_stale_source_passes():
    review = review_freshness({"source_id": "src-1", "status": "stale", "reviewed_at": NOW, "review_completed": True})
    require_review_if_stale(review)  # no raise


# --- mini-tasks & audit ------------------------------------------------------

def test_mini_task_dry_run_default():
    task = define_mini_task({"task_id": "task-1", "domain": "acq", "objective": "summarize", "scope": "bounded", "mode": "dry_run"})
    assert task["live_side_effects_created"] is False


def test_dry_live_boundary_is_enforced():
    with pytest.raises(KnowledgeAcquisitionError, match="dry_live_boundary_enforced"):
        define_mini_task({"task_id": "task-1", "domain": "acq", "objective": "x", "scope": "bounded", "mode": "live", "permit_refs": []})


def test_mini_task_result_must_be_audited():
    with pytest.raises(KnowledgeAcquisitionError, match="mini_task_result_must_be_audited"):
        trust_result({"task_id": "task-1", "ok": True}, audit=None)


def test_workbench_result_is_not_truth_without_audit():
    with pytest.raises(KnowledgeAcquisitionError, match="mini_task_result_must_be_audited"):
        trust_result({"task_id": "wb-1", "artifact": "draft.md"}, audit=None)


def test_mini_task_failure_is_recorded_not_hidden():
    audit = audit_mini_task_result(_audit(outcome="failed", receipt_refs=[]))
    assert audit["passed"] is False
    assert audit["recorded"] is True
    assert audit["hidden"] is False


def test_audited_pass_is_trusted():
    audit = audit_mini_task_result(_audit())
    assert trust_result({"task_id": "task-1"}, audit=audit)["trusted"] is True


# --- promotion ---------------------------------------------------------------

def test_memory_promotion_requires_citation_and_audit():
    with pytest.raises(KnowledgeAcquisitionError, match="memory_promotion_requires_citation_and_audit"):
        request_memory_promotion(_promotion(citation_refs=["cit-1"], audit_refs=[]))


def test_stale_source_cannot_promote_without_review():
    with pytest.raises(KnowledgeAcquisitionError, match="stale_source_cannot_promote_without_review"):
        request_memory_promotion(_promotion(source_reviews=[{"source_id": "src-1", "status": "stale", "review_completed": False}]))


def test_memory_promotion_emits_phase26_receipt(tmp_path: Path):
    ledger = PersistentMemoryLedger(tmp_path / "memory.jsonl")
    entry, receipt = promote_to_memory(ledger, _promotion())
    assert receipt["phase26_schema"] == "memory_event_v1"
    assert receipt["memory_chain_hash"] == entry.chain_hash
    assert entry.payload["event_type"] == "PROMOTION"
    assert ledger.verify_chain().ok


def test_self_merge_attempt_is_rejected():
    with pytest.raises(KnowledgeAcquisitionError, match="self_merge_rejected"):
        request_memory_promotion(_promotion(self_merge=True))


def test_missing_receipt_blocks_success():
    with pytest.raises(KnowledgeAcquisitionError, match="missing_receipt_blocks_success"):
        build_acquisition_outcome_receipt(status="green", receipt_refs=[])


def test_skill_candidate_from_acquisition_is_advisory_only():
    candidate = build_skill_candidate({"candidate_id": "skc-1", "procedure": "summarize-source", "evidence_refs": ["ev-1"]})
    assert candidate["advisory_only"] is True
    assert candidate["tool_authorized"] is False


def test_domain_readiness_record_is_advisory_only():
    record = build_domain_readiness_record({"domain": "acq", "readiness": "candidate", "evidence_refs": ["ev-1"]})
    assert record["advisory_only"] is True
    assert record["authority_created"] is False


def test_fake_green_attempt_is_rejected():
    with pytest.raises(KnowledgeAcquisitionError, match="fake_green_rejected"):
        create_claim_record(_claim(evidence_refs=[], source_refs=[], status="verified", enforce_status=True))


# --- STOP/PANIC, replay ------------------------------------------------------

def test_stop_panic_preempts_acquisition_operation():
    with pytest.raises(KnowledgeAcquisitionError, match="REFUSED_STOP"):
        ingest_source(_source(), control=OperationControl(stop_active=True))
    with pytest.raises(KnowledgeAcquisitionError, match="REFUSED_PANIC"):
        define_mini_task(
            {"task_id": "t", "domain": "d", "objective": "o", "scope": "bounded", "mode": "dry_run"},
            control=OperationControl(panic_active=True),
        )


def test_acquisition_replay_is_deterministic(tmp_path: Path):
    log = KnowledgeAcquisitionLog(tmp_path / "acq.jsonl")
    log.append("source_artifact_v1", ingest_source(_source()))
    log.append("claim_record_v1", create_claim_record(_claim()))
    a = log.replay()
    b = log.replay()
    assert a.ok and b.ok
    assert a.chain_root == b.chain_root


def test_replay_divergence_is_failure(tmp_path: Path):
    log = KnowledgeAcquisitionLog(tmp_path / "acq.jsonl")
    log.append("claim_record_v1", create_claim_record(_claim()))
    row = json.loads(log.path.read_text(encoding="utf-8").splitlines()[0])
    row["chain_hash"] = "sha256:bad"
    log.path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    assert not log.replay().ok


def test_replay_panic_preempts(tmp_path: Path):
    log = KnowledgeAcquisitionLog(tmp_path / "acq.jsonl")
    log.append("claim_record_v1", create_claim_record(_claim()))
    with pytest.raises(KnowledgeAcquisitionError, match="REFUSED_PANIC"):
        log.replay(control=OperationControl(panic_active=True))


# --- gate --------------------------------------------------------------------

def test_phase30_gate_refuses_without_phase26_phase28_phase29_green(tmp_path: Path):
    base = dict(proof_bundle=None, tests_passed=True)
    assert evaluate_phase30_gate(tmp_path, phase26_green=False, phase28_green=True, phase29_green=True, **base)["verdict"] == "RED_PHASE30_PHASE26_GREEN_REQUIRED"
    assert evaluate_phase30_gate(tmp_path, phase26_green=True, phase28_green=False, phase29_green=True, **base)["verdict"] == "RED_PHASE30_PHASE28_GREEN_REQUIRED"
    assert evaluate_phase30_gate(tmp_path, phase26_green=True, phase28_green=True, phase29_green=False, **base)["verdict"] == "RED_PHASE30_PHASE29_GREEN_REQUIRED"


def test_phase30_gate_refuses_without_proof_bundle(tmp_path: Path):
    result = evaluate_phase30_gate(tmp_path, phase26_green=True, phase28_green=True, phase29_green=True, proof_bundle=None, tests_passed=True)
    assert result["verdict"] == "RED_PHASE30_PROOF_BUNDLE_MISSING"


def test_phase30_proof_validator_accepts_resolved_path(tmp_path: Path, monkeypatch):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    for name in ("HEAD.txt", "command_log.jsonl", "manifest.json", "summary.json", "status.md"):
        (bundle / name).write_text("{}\n", encoding="utf-8")
    (bundle / "gate_result.json").write_text(json.dumps({"proof_bundle": str(bundle.resolve())}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    ok, failures = validate_phase30_proof_bundle(Path("bundle"))
    assert ok and failures == []
