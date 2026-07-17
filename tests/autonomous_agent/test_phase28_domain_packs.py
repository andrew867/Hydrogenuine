"""Phase 28 domain pack runtime tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_runtime.domain_packs import (
    DomainPackError,
    DomainPackRegistry,
    activate_domain_pack,
    check_forbidden_claims,
    compute_pack_hash,
    evaluate_pack_execution,
    load_domain_pack,
    validate_domain_pack,
    validate_phase28_proof_bundle,
)
from hg_runtime.domain_packs.activation import PHASE26_GREEN, PHASE27_GREEN
from hg_runtime.domain_packs.gate import evaluate_phase28_gate
from hg_runtime.memory_ledger.schemas import OperationControl

NOW = "2026-06-19T13:30:00.000000Z"
TOOLS = {"proof.verify", "memory.read"}
SKILLS = {"skill:evidence-bound-gate-check"}
MEMORIES = {"p26-memory-ref"}


def _pack(**overrides):
    payload = {
        "schema": "domain_pack_v1",
        "domain_id": "runtime-governance",
        "version": "1.0.0",
        "task_templates": [
            {"schema": "domain_task_template_v1", "template_id": "review-gate", "description": "review an evidence-bound gate"}
        ],
        "quality_criteria": [
            {"schema": "domain_quality_criteria_v1", "criterion": "all claims cite proof", "required": True}
        ],
        "allowed_tool_refs": [
            {"schema": "domain_tool_ref_v1", "tool_ref": "proof.verify", "purpose": "read proof metadata only"}
        ],
        "forbidden_claims": [
            {"schema": "domain_forbidden_claim_v1", "claim": "AGI achieved"},
            {"schema": "domain_forbidden_claim_v1", "claim": "clean live field run"},
        ],
        "proof_expectations": [
            {"schema": "domain_proof_expectation_v1", "expectation": "focused tests pass", "required": True}
        ],
        "schema_refs": ["domain_pack_v1"],
        "fixture_refs": ["tests/fixtures/autonomous_agent/phase28/valid_domain_pack_v1.json"],
        "skill_refs": ["skill:evidence-bound-gate-check"],
        "memory_refs": ["p26-memory-ref"],
        "evaluation_refs": ["tests/autonomous_agent/test_phase28_domain_packs.py"],
        "claim_boundary": "declarative_advisory_only",
        "authority_refs": ["gpp:reference-only", "hal:reference-only", "ueak:reference-only", "oea:reference-only"],
        "signature_ref": "local-fixture-signature-ref",
    }
    payload.update(overrides)
    payload["pack_hash"] = compute_pack_hash(payload)
    return payload


def _load(payload):
    return load_domain_pack(payload, known_tool_refs=TOOLS, known_skill_refs=SKILLS, known_memory_refs=MEMORIES)


def test_domain_pack_cannot_expand_authority():
    payload = _pack(widens_scope=True)
    with pytest.raises(DomainPackError, match="authority_bypass_attempt"):
        _load(payload)


def test_unsigned_or_unhashed_pack_is_rejected():
    payload = _pack()
    payload.pop("signature_ref")
    with pytest.raises(DomainPackError, match="schema_violation:missing:signature_ref"):
        _load(payload)
    payload = _pack()
    payload.pop("pack_hash")
    with pytest.raises(DomainPackError, match="unhashed_pack_rejected"):
        _load(payload)


def test_pack_tool_reference_requires_registry_match():
    payload = _pack(allowed_tool_refs=[{"schema": "domain_tool_ref_v1", "tool_ref": "moltbook.post", "purpose": "not allowed"}])
    payload["pack_hash"] = compute_pack_hash(payload)
    with pytest.raises(DomainPackError, match="unknown_tool_ref"):
        _load(payload)


def test_forbidden_claim_blocks_output():
    pack = _load(_pack())
    result = check_forbidden_claims("This proves AGI achieved in a clean live field run.", pack)
    assert result.allowed is False
    assert "AGI achieved" in result.blocked_claims


def test_domain_pack_cannot_authorize_tools():
    payload = _pack(allowed_tool_refs=[{"schema": "domain_tool_ref_v1", "tool_ref": "proof.verify", "purpose": "read", "authorize": True}])
    payload["pack_hash"] = compute_pack_hash(payload)
    with pytest.raises(DomainPackError, match="authority_bypass_attempt"):
        _load(payload)


def test_domain_pack_cannot_create_live_effects():
    payload = _pack(live_side_effects_created=True)
    with pytest.raises(DomainPackError, match="authority_bypass_attempt"):
        _load(payload)


def test_domain_pack_cannot_override_gpp_hal_ueak():
    for key in ("override_gpp", "override_hal", "override_ueak", "override_oea"):
        payload = _pack(**{key: True})
        with pytest.raises(DomainPackError, match="authority_bypass_attempt"):
            _load(payload)


def test_domain_pack_cannot_treat_skill_as_permission():
    payload = _pack(treat_skill_as_permission=True)
    with pytest.raises(DomainPackError, match="authority_bypass_attempt"):
        _load(payload)


def test_domain_pack_cannot_treat_memory_as_permission():
    payload = _pack(treat_memory_as_permission=True)
    with pytest.raises(DomainPackError, match="authority_bypass_attempt"):
        _load(payload)


def test_pack_activation_requires_phase26_and_phase27_green():
    pack = _load(_pack())
    with pytest.raises(DomainPackError, match="phase28_activation_requires_phase26_and_phase27_green"):
        activate_domain_pack(pack, phase26_verdict="RED", phase27_verdict=PHASE27_GREEN, receipt_refs=["receipt:phase28:test"])


def test_pack_schema_violation_blocks_load():
    payload = _pack()
    payload.pop("quality_criteria")
    payload["pack_hash"] = compute_pack_hash(payload)
    with pytest.raises(DomainPackError, match="schema_violation"):
        _load(payload)


def test_pack_hash_mismatch_blocks_load():
    payload = _pack()
    payload["pack_hash"] = "sha256:bad"
    with pytest.raises(DomainPackError, match="pack_hash_mismatch"):
        _load(payload)


def test_pack_version_change_is_audited(tmp_path: Path):
    registry = DomainPackRegistry(tmp_path / "domain-packs.jsonl", known_tool_refs=TOOLS, known_skill_refs=SKILLS, known_memory_refs=MEMORIES)
    pack = registry.load_pack(_pack(), created_at=NOW)
    changed = _pack(version="1.0.1")
    version = registry.record_version_change(changed, parent_pack_hash=pack.payload["pack_hash"], change_summary="tighten criteria")
    assert version.payload["parent_pack_hash"] == pack.payload["pack_hash"]


def test_pack_quality_criteria_required():
    payload = _pack(quality_criteria=[])
    payload["pack_hash"] = compute_pack_hash(payload)
    with pytest.raises(DomainPackError, match="quality_criteria_required"):
        _load(payload)


def test_pack_proof_expectations_required():
    payload = _pack(proof_expectations=[])
    payload["pack_hash"] = compute_pack_hash(payload)
    with pytest.raises(DomainPackError, match="proof_expectations_required"):
        _load(payload)


def test_unknown_skill_ref_is_rejected_or_flagged():
    payload = _pack(skill_refs=["skill:unknown"])
    payload["pack_hash"] = compute_pack_hash(payload)
    with pytest.raises(DomainPackError, match="unknown_skill_refs"):
        _load(payload)


def test_unknown_memory_ref_is_rejected_or_flagged():
    payload = _pack(memory_refs=["p26-unknown"])
    payload["pack_hash"] = compute_pack_hash(payload)
    with pytest.raises(DomainPackError, match="unknown_memory_refs"):
        _load(payload)


def test_dry_live_boundary_is_enforced():
    pack = _load(_pack())
    decision = evaluate_pack_execution(pack, OperationControl())
    assert decision.allowed is False
    assert decision.reason == "DOMAIN_PACK_DECLARATIVE_ONLY"


def test_fake_green_attempt_is_rejected():
    payload = _pack(proof_expectations=[{"schema": "domain_proof_expectation_v1", "expectation": "declare green without tests", "required": True, "permission_granted": True}])
    payload["pack_hash"] = compute_pack_hash(payload)
    with pytest.raises(DomainPackError, match="authority_bypass_attempt"):
        _load(payload)


def test_stop_panic_preempts_pack_operation(tmp_path: Path):
    registry = DomainPackRegistry(tmp_path / "domain-packs.jsonl", known_tool_refs=TOOLS, known_skill_refs=SKILLS, known_memory_refs=MEMORIES)
    with pytest.raises(DomainPackError, match="REFUSED_STOP"):
        registry.load_pack(_pack(), control=OperationControl(stop_active=True))
    with pytest.raises(DomainPackError, match="REFUSED_PANIC"):
        registry.replay(control=OperationControl(panic_active=True))


def test_replay_divergence_is_failure(tmp_path: Path):
    registry = DomainPackRegistry(tmp_path / "domain-packs.jsonl", known_tool_refs=TOOLS, known_skill_refs=SKILLS, known_memory_refs=MEMORIES)
    registry.load_pack(_pack(), created_at=NOW)
    row = json.loads(registry.path.read_text(encoding="utf-8").splitlines()[0])
    row["chain_hash"] = "sha256:bad"
    registry.path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    assert not registry.replay().ok


def test_phase28_gate_refuses_without_proof_bundle(tmp_path: Path):
    result = evaluate_phase28_gate(tmp_path, phase26_green=True, phase27_green=True, proof_bundle=None, tests_passed=True)
    assert result["verdict"] == "RED_PHASE28_PROOF_BUNDLE_MISSING"


def test_pack_registry_replay_is_deterministic(tmp_path: Path):
    registry = DomainPackRegistry(tmp_path / "domain-packs.jsonl", known_tool_refs=TOOLS, known_skill_refs=SKILLS, known_memory_refs=MEMORIES)
    pack = registry.load_pack(_pack(), created_at=NOW)
    registry.activate_pack(
        pack.payload,
        phase26_verdict=PHASE26_GREEN,
        phase27_verdict=PHASE27_GREEN,
        receipt_refs=["receipt:phase28:test"],
        created_at=NOW,
    )
    a = registry.replay()
    b = registry.replay()
    assert a.ok and b.ok
    assert a.chain_root == b.chain_root


def test_pack_activation_receipt_is_advisory_only():
    pack = _load(_pack())
    receipt = activate_domain_pack(pack, phase26_verdict=PHASE26_GREEN, phase27_verdict=PHASE27_GREEN, receipt_refs=["receipt:phase28:test"])
    assert receipt["permission_granted"] is False
    assert receipt["tool_authorized"] is False


def test_loaded_pack_query_preserves_provenance(tmp_path: Path):
    registry = DomainPackRegistry(tmp_path / "domain-packs.jsonl", known_tool_refs=TOOLS, known_skill_refs=SKILLS, known_memory_refs=MEMORIES)
    record = registry.load_pack(_pack(), created_at=NOW)
    results = registry.query(domain_id="runtime-governance")
    assert results[0]["pack_hash"] == record.payload["pack_hash"]


def test_phase28_gate_refuses_without_phase26_or_phase27_green(tmp_path: Path):
    result = evaluate_phase28_gate(tmp_path, phase26_green=False, phase27_green=True, proof_bundle=None, tests_passed=True)
    assert result["verdict"] == "RED_PHASE28_PHASE26_GREEN_REQUIRED"
    result = evaluate_phase28_gate(tmp_path, phase26_green=True, phase27_green=False, proof_bundle=None, tests_passed=True)
    assert result["verdict"] == "RED_PHASE28_PHASE27_GREEN_REQUIRED"


def test_phase28_proof_validator_accepts_resolved_path(tmp_path: Path, monkeypatch):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    for name in ("HEAD.txt", "command_log.jsonl", "manifest.json", "summary.json", "status.md"):
        (bundle / name).write_text("{}\n", encoding="utf-8")
    (bundle / "gate_result.json").write_text(json.dumps({"proof_bundle": str(bundle.resolve())}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    ok, failures = validate_phase28_proof_bundle(Path("bundle"))
    assert ok
    assert failures == []


def test_validate_domain_pack_does_not_grant_authority():
    pack = validate_domain_pack(_pack(), expected_hash=compute_pack_hash(_pack()), known_tool_refs=TOOLS, known_skill_refs=SKILLS, known_memory_refs=MEMORIES)
    assert pack["authority_created"] is False
    assert pack["permission_granted"] is False
    assert pack["tool_authorized"] is False
    assert pack["live_side_effects_created"] is False
