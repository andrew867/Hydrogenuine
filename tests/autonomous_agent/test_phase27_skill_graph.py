"""Phase 27 skill graph and transfer engine tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_runtime.memory_ledger import PersistentMemoryLedger
from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.skill_graph import (
    SkillGraph,
    SkillGraphError,
    create_transfer_candidate,
    evaluate_transfer_execution,
    extract_skill_from_experience,
    validate_phase27_proof_bundle,
    validate_skill_node,
    validate_transfer_candidate,
)
from hg_runtime.skill_graph.gate import evaluate_phase27_gate

NOW = "2026-06-19T13:10:00.000000Z"
RECEIPT = ["receipt:phase27:test"]
PROOF = ["docs/proofs/autonomous_agent_zero/PHASE-27/test/gate_result.json"]


def _experience(**overrides):
    payload = {
        "task_id": "task:phase27",
        "procedure": "summarize-failure-and-gate",
        "inputs_hash": "sha256:inputs",
        "outputs_hash": "sha256:outputs",
        "result": "success",
        "failure_mode": None,
        "receipt_refs": ["receipt:phase26:experience"],
        "proof_refs": ["docs/proofs/autonomous_agent_zero/PHASE-26/gate_result.json"],
        "lessons_learned": ["reuse only when evidence and gate checks are present"],
        "promotion_status": "promoted",
        "authority_refs": ["gpp:reference-only"],
        "claim_boundary": "evidence_only",
    }
    payload.update(overrides)
    return payload


def _phase26_entry(tmp_path: Path, **overrides):
    ledger = PersistentMemoryLedger(tmp_path / "memory.jsonl")
    return ledger.append_experience_entry(_experience(**overrides), created_at=NOW)


def _skill_payload(entry, **overrides):
    payload = {
        "name": "evidence-bound-gate-check",
        "domain": "runtime_governance",
        "procedure": "summarize-failure-and-gate",
        "phase26_entry_ref": entry.entry_id,
        "provenance_refs": [entry.chain_hash],
        "evidence_refs": list(entry.payload["receipt_refs"]),
        "receipt_refs": RECEIPT,
        "authority_refs": ["gpp:reference-only"],
        "claim_boundary": "advisory_only",
        "status": "draft",
    }
    payload.update(overrides)
    return payload


def _transfer_payload(skill_id: str, **overrides):
    payload = {
        "source_skill_id": skill_id,
        "source_domain": "runtime_governance",
        "target_domain": "operator_review",
        "analogy": "both require evidence-bound gate review",
        "evidence_refs": ["skill:evidence:test"],
        "verification_requirements": ["focused tests", "operator review"],
        "negative_transfer_refs": [],
        "status": "candidate",
        "claim_boundary": "advisory_only",
        "authority_refs": ["hal:reference-only"],
    }
    payload.update(overrides)
    return payload


def test_skill_node_requires_phase26_ledger_provenance(tmp_path: Path):
    entry = _phase26_entry(tmp_path)
    skill = extract_skill_from_experience(entry, name="evidence-bound-gate-check", domain="runtime_governance")
    assert skill["phase26_entry_ref"] == entry.entry_id
    assert skill["provenance_refs"] == [entry.chain_hash]


def test_skill_cannot_authorize_tools(tmp_path: Path):
    entry = _phase26_entry(tmp_path)
    with pytest.raises(SkillGraphError, match="authority_bypass_attempt"):
        validate_skill_node(_skill_payload(entry, authority_refs=[{"ref": "ueak:x", "authorizes_tool": "moltbook.post"}]))


def test_transfer_candidate_requires_evidence(tmp_path: Path):
    graph = SkillGraph(tmp_path / "skills.jsonl")
    entry = _phase26_entry(tmp_path)
    skill = graph.add_skill(_skill_payload(entry), created_at=NOW)
    with pytest.raises(SkillGraphError, match="evidence_required"):
        validate_transfer_candidate(_transfer_payload(skill.skill_id, evidence_refs=[]))


def test_negative_transfer_is_rejected(tmp_path: Path):
    graph = SkillGraph(tmp_path / "skills.jsonl")
    entry = _phase26_entry(tmp_path)
    skill = graph.add_skill(_skill_payload(entry), created_at=NOW)
    candidate = graph.add_transfer_candidate(
        _transfer_payload(skill.skill_id, negative_transfer_refs=["neg:unsafe"], status="rejected"),
        created_at=NOW,
    )
    assert candidate.payload["status"] == "rejected"
    assert candidate.transfer_advisory_only is True


def test_skill_version_change_is_audited(tmp_path: Path):
    graph = SkillGraph(tmp_path / "skills.jsonl")
    entry = _phase26_entry(tmp_path)
    skill = graph.add_skill(_skill_payload(entry), created_at=NOW)
    version = graph.add_skill_version(skill.skill_id, parent_refs=[skill.skill_hash], change_summary="tighten evidence")
    assert version.payload["parent_refs"] == (skill.skill_hash,)
    assert version.payload["version_hash"].startswith("sha256:")


def test_skill_extraction_requires_receipt_backed_experience(tmp_path: Path):
    entry = _phase26_entry(tmp_path, result="failure", receipt_refs=[], proof_refs=[], promotion_status="blocked")
    with pytest.raises(SkillGraphError, match="receipt_backed_experience_required"):
        extract_skill_from_experience(entry, name="bad", domain="runtime_governance")


def test_memory_reference_does_not_become_permission(tmp_path: Path):
    entry = _phase26_entry(tmp_path)
    skill = validate_skill_node(_skill_payload(entry))
    assert skill["permission_granted"] is False
    assert skill["authority_created"] is False


def test_transfer_candidate_is_advisory_only(tmp_path: Path):
    graph = SkillGraph(tmp_path / "skills.jsonl")
    entry = _phase26_entry(tmp_path)
    skill = graph.add_skill(_skill_payload(entry), created_at=NOW)
    transfer = graph.add_transfer_candidate(_transfer_payload(skill.skill_id), created_at=NOW)
    assert transfer.payload["advisory_only"] is True
    assert transfer.can_authorize_execution is False


def test_surface_similarity_does_not_count_as_transfer_proof(tmp_path: Path):
    entry = _phase26_entry(tmp_path)
    skill = validate_skill_node(_skill_payload(entry))
    with pytest.raises(SkillGraphError, match="surface_similarity_not_proof"):
        create_transfer_candidate(skill, target_domain="operator_review", similarity_only=True)


def test_missing_provenance_blocks_skill_creation(tmp_path: Path):
    entry = _phase26_entry(tmp_path)
    with pytest.raises(SkillGraphError, match="provenance_required"):
        validate_skill_node(_skill_payload(entry, provenance_refs=[]))


def test_schema_violation_blocks_skill_graph_entry():
    with pytest.raises(SkillGraphError, match="schema_violation"):
        validate_skill_node({"name": "missing"})


def test_authority_bypass_attempt_is_rejected(tmp_path: Path):
    entry = _phase26_entry(tmp_path)
    with pytest.raises(SkillGraphError, match="authority_bypass_attempt"):
        validate_skill_node(_skill_payload(entry, authority_refs=[{"ref": "gpp:x", "grants_authority": True}]))


def test_fake_green_attempt_is_rejected(tmp_path: Path):
    graph = SkillGraph(tmp_path / "skills.jsonl")
    entry = _phase26_entry(tmp_path)
    skill = graph.add_skill(_skill_payload(entry), created_at=NOW)
    with pytest.raises(SkillGraphError, match="fake_green_rejected"):
        graph.record_transfer_evidence(skill.skill_id, result="success", evidence_refs=[], receipt_refs=[])


def test_dry_live_boundary_is_enforced(tmp_path: Path):
    entry = _phase26_entry(tmp_path)
    skill = validate_skill_node(_skill_payload(entry))
    decision = evaluate_transfer_execution(skill, OperationControl())
    assert decision.allowed is False
    assert decision.reason == "SKILL_GRAPH_ADVISORY_ONLY"


def test_stop_panic_preempts_skill_operation(tmp_path: Path):
    graph = SkillGraph(tmp_path / "skills.jsonl")
    entry = _phase26_entry(tmp_path)
    with pytest.raises(SkillGraphError, match="REFUSED_STOP"):
        graph.add_skill(_skill_payload(entry), control=OperationControl(stop_active=True))
    with pytest.raises(SkillGraphError, match="REFUSED_PANIC"):
        graph.replay(control=OperationControl(panic_active=True))


def test_replay_divergence_is_failure(tmp_path: Path):
    graph = SkillGraph(tmp_path / "skills.jsonl")
    entry = _phase26_entry(tmp_path)
    graph.add_skill(_skill_payload(entry), created_at=NOW)
    row = json.loads(graph.path.read_text(encoding="utf-8").splitlines()[0])
    row["chain_hash"] = "sha256:bad"
    graph.path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    assert not graph.replay().ok


def test_missing_receipt_blocks_success(tmp_path: Path):
    graph = SkillGraph(tmp_path / "skills.jsonl")
    entry = _phase26_entry(tmp_path)
    skill = graph.add_skill(_skill_payload(entry), created_at=NOW)
    with pytest.raises(SkillGraphError, match="receipt_required"):
        graph.record_transfer_evidence(skill.skill_id, result="success", evidence_refs=["e"], receipt_refs=[])


def test_skill_graph_replay_is_deterministic(tmp_path: Path):
    graph = SkillGraph(tmp_path / "skills.jsonl")
    entry = _phase26_entry(tmp_path)
    skill = graph.add_skill(_skill_payload(entry), created_at=NOW)
    graph.add_transfer_candidate(_transfer_payload(skill.skill_id), created_at=NOW)
    a = graph.replay()
    b = graph.replay()
    assert a.ok and b.ok
    assert a.chain_root == b.chain_root


def test_phase27_gate_refuses_without_phase26_green(tmp_path: Path):
    result = evaluate_phase27_gate(tmp_path, phase26_green=False, proof_bundle=None, tests_passed=True)
    assert result["verdict"] == "RED_PHASE27_PHASE26_GREEN_REQUIRED"


def test_phase27_gate_refuses_without_proof_bundle(tmp_path: Path):
    result = evaluate_phase27_gate(tmp_path, phase26_green=True, proof_bundle=None, tests_passed=True)
    assert result["verdict"] == "RED_PHASE27_PROOF_BUNDLE_MISSING"


def test_query_by_domain_and_provenance(tmp_path: Path):
    graph = SkillGraph(tmp_path / "skills.jsonl")
    entry = _phase26_entry(tmp_path)
    skill = graph.add_skill(_skill_payload(entry), created_at=NOW)
    assert graph.query(domain="runtime_governance")[0]["skill_id"] == skill.skill_id
    assert graph.query(provenance_ref=entry.chain_hash)[0]["skill_id"] == skill.skill_id


def test_graph_edge_requires_evidence(tmp_path: Path):
    graph = SkillGraph(tmp_path / "skills.jsonl")
    with pytest.raises(SkillGraphError, match="evidence_required"):
        graph.add_edge(source_id="a", target_id="b", edge_type="refines", evidence_refs=[], receipt_refs=RECEIPT)


def test_phase27_proof_validator_accepts_resolved_path(tmp_path: Path, monkeypatch):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    for name in ("HEAD.txt", "command_log.jsonl", "manifest.json", "summary.json", "status.md"):
        (bundle / name).write_text("{}\n", encoding="utf-8")
    (bundle / "gate_result.json").write_text(json.dumps({"proof_bundle": str(bundle.resolve())}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    ok, failures = validate_phase27_proof_bundle(Path("bundle"))
    assert ok
    assert failures == []
