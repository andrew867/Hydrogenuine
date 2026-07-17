"""Phase 26 persistent memory / experience ledger tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_runtime.memory_ledger import (
    MemoryLedgerError,
    OperationControl,
    PersistentMemoryLedger,
    evaluate_memory_driven_action,
    validate_experience_entry,
    validate_memory_event,
)
from hg_runtime.memory_ledger.gate import evaluate_phase26_gate
from hg_runtime.memory_ledger.gate import validate_phase26_proof_bundle

NOW = "2026-06-19T12:00:00.000000Z"


def _ledger(tmp_path: Path) -> PersistentMemoryLedger:
    return PersistentMemoryLedger(tmp_path / "phase26-memory.jsonl")


def _receipt() -> list[str]:
    return ["receipt:phase26:test"]


def _proof() -> list[str]:
    return ["docs/proofs/autonomous_agent_zero/PHASE-26/test/gate_result.json"]


def _memory_payload(**overrides):
    payload = {
        "event_type": "OBSERVATION",
        "subject": "agent0:test",
        "scope": "phase26",
        "claim": "observed deterministic replay behavior",
        "provenance_refs": ["tests/autonomous_agent/test_phase26_memory_ledger.py"],
        "authority_refs": ["gpp:reference-only"],
        "receipt_refs": _receipt(),
        "confidence": "verified",
        "status": "recorded",
        "claim_boundary": "evidence_only",
    }
    payload.update(overrides)
    return payload


def _experience_payload(**overrides):
    payload = {
        "task_id": "task:phase26",
        "procedure": "phase26:test",
        "inputs_hash": "sha256:inputs",
        "outputs_hash": "sha256:outputs",
        "result": "success",
        "failure_mode": None,
        "receipt_refs": _receipt(),
        "proof_refs": _proof(),
        "lessons_learned": ["receipt-bound learning only"],
        "promotion_status": "promoted",
        "authority_refs": ["hal:reference-only"],
        "claim_boundary": "evidence_only",
    }
    payload.update(overrides)
    return payload


def test_memory_append_is_immutable(tmp_path: Path):
    ledger = _ledger(tmp_path)
    first = ledger.append_memory_event(_memory_payload(), created_at=NOW)
    second = ledger.append_memory_event(_memory_payload(subject="agent0:test:2"), created_at=NOW)
    assert first.previous_hash == "sha256:phase26_genesis"
    assert second.previous_hash == first.chain_hash
    assert ledger.verify_chain().ok

    rows = ledger.path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(rows[0])
    tampered["payload"]["claim"] = "rewritten"
    rows[0] = json.dumps(tampered)
    ledger.path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    assert not ledger.verify_chain().ok


def test_memory_cannot_grant_authority():
    with pytest.raises(MemoryLedgerError, match="authority_reference_only"):
        validate_memory_event(_memory_payload(authority_refs=[{"ref": "gpp:x", "grants_authority": True}]))


def test_experience_learning_requires_receipt():
    with pytest.raises(MemoryLedgerError, match="receipt_required"):
        validate_experience_entry(_experience_payload(receipt_refs=[], proof_refs=[]))


def test_authority_memory_is_reference_only(tmp_path: Path):
    record = _ledger(tmp_path).append_memory_event(_memory_payload(), created_at=NOW)
    assert record.payload["authority_refs"] == ("gpp:reference-only",)
    assert record.authority_granted is False
    assert record.can_authorize_tools is False


def test_failure_memory_blocks_fake_green(tmp_path: Path):
    ledger = _ledger(tmp_path)
    ledger.append_experience_entry(
        _experience_payload(result="failure", failure_mode="missing receipt", promotion_status="blocked"),
        created_at=NOW,
    )
    gate = ledger.assess_fake_green()
    assert not gate["ok"]
    assert gate["reason"] == "failure_memory_blocks_green"


def test_memory_replay_is_deterministic(tmp_path: Path):
    ledger = _ledger(tmp_path)
    ledger.append_memory_event(_memory_payload(), created_at=NOW)
    a = ledger.replay()
    b = ledger.replay()
    assert a.ok and b.ok
    assert a.chain_root == b.chain_root


def test_compaction_preserves_hash_chain(tmp_path: Path):
    ledger = _ledger(tmp_path)
    ledger.append_memory_event(_memory_payload(subject="a"), created_at=NOW)
    ledger.append_memory_event(_memory_payload(subject="b"), created_at=NOW)
    before = ledger.replay().chain_root
    receipt = ledger.compact(summary="two observations summarized", receipt_refs=_receipt(), created_at=NOW)
    assert receipt.pre_compaction_root == before
    assert receipt.post_compaction_root == before
    assert receipt.receipt_hash.startswith("sha256:")
    assert ledger.verify_chain().ok


def test_redaction_does_not_destroy_provenance(tmp_path: Path):
    ledger = _ledger(tmp_path)
    record = ledger.append_memory_event(_memory_payload(claim="sensitive marker abc123"), created_at=NOW)
    redacted = ledger.redact(record.entry_id, reason="sensitive preview", created_at=NOW)
    assert redacted.payload["redaction"]["redacted_entry_id"] == record.entry_id
    assert redacted.payload["redaction"]["original_chain_hash"] == record.chain_hash
    assert redacted.payload["provenance_refs"]


def test_panic_blocks_memory_driven_action():
    decision = evaluate_memory_driven_action(_memory_payload(), OperationControl(panic_active=True))
    assert not decision.allowed
    assert decision.reason == "REFUSED_PANIC"


def test_stale_memory_is_marked_not_silently_trusted(tmp_path: Path):
    ledger = _ledger(tmp_path)
    ledger.append_memory_event(_memory_payload(status="stale"), created_at=NOW)
    result = ledger.query(subject="agent0:test")
    assert result[0]["trust_status"] == "stale_not_silently_trusted"


def test_self_authorization_attempt_is_rejected():
    with pytest.raises(MemoryLedgerError, match="self_authorization_rejected"):
        validate_memory_event(_memory_payload(claim_boundary="self_authorizing"))


def test_fake_green_attempt_is_rejected():
    with pytest.raises(MemoryLedgerError, match="fake_green_rejected"):
        validate_experience_entry(_experience_payload(result="success", proof_refs=[], receipt_refs=[]))


def test_dry_live_boundary_is_enforced(tmp_path: Path):
    ledger = _ledger(tmp_path)
    record = ledger.append_memory_event(_memory_payload(event_type="LIVE_ACTION_REQUEST"), created_at=NOW)
    decision = evaluate_memory_driven_action(record.payload, OperationControl())
    assert not decision.allowed
    assert decision.reason == "MEMORY_CANNOT_CREATE_LIVE_EFFECTS"


def test_stop_panic_preempts_phase_operation(tmp_path: Path):
    ledger = _ledger(tmp_path)
    ledger.append_memory_event(_memory_payload(), created_at=NOW)
    with pytest.raises(MemoryLedgerError, match="REFUSED_STOP"):
        ledger.promote_learning(ledger.iter_entries()[0].entry_id, receipt_refs=_receipt(), control=OperationControl(stop_active=True))
    with pytest.raises(MemoryLedgerError, match="REFUSED_PANIC"):
        ledger.replay(control=OperationControl(panic_active=True))


def test_replay_divergence_is_failure(tmp_path: Path):
    ledger = _ledger(tmp_path)
    ledger.append_memory_event(_memory_payload(), created_at=NOW)
    rows = ledger.path.read_text(encoding="utf-8").splitlines()
    row = json.loads(rows[0])
    row["chain_hash"] = "sha256:bad"
    ledger.path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    assert not ledger.replay().ok


def test_missing_receipt_blocks_success():
    with pytest.raises(MemoryLedgerError, match="receipt_required"):
        validate_experience_entry(_experience_payload(result="success", receipt_refs=[]))


def test_schema_violation_blocks_success():
    with pytest.raises(MemoryLedgerError, match="schema_violation"):
        validate_memory_event({"event_type": "OBSERVATION"})


def test_authority_bypass_attempt_is_rejected():
    with pytest.raises(MemoryLedgerError, match="authority_bypass_attempt"):
        validate_experience_entry(_experience_payload(authority_refs=[{"ref": "ueak:x", "authorizes_tool": "moltbook.post"}]))


def test_receipt_required_for_memory_promotion(tmp_path: Path):
    ledger = _ledger(tmp_path)
    record = ledger.append_memory_event(_memory_payload(status="recorded"), created_at=NOW)
    with pytest.raises(MemoryLedgerError, match="receipt_required"):
        ledger.promote_learning(record.entry_id, receipt_refs=[])


def test_phase26_gate_refuses_without_proof_bundle(tmp_path: Path):
    result = evaluate_phase26_gate(tmp_path, proof_bundle=None, tests_passed=True)
    assert result["verdict"] == "RED_PHASE26_PROOF_BUNDLE_MISSING"
    assert result["ok"] is False


def test_phase26_proof_validator_accepts_resolved_bundle_path(tmp_path: Path, monkeypatch):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    for name in ("HEAD.txt", "command_log.jsonl", "manifest.json", "summary.json", "status.md"):
        (bundle / name).write_text("{}\n", encoding="utf-8")
    (bundle / "gate_result.json").write_text(
        json.dumps({"proof_bundle": str(bundle.resolve())}),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    ok, failures = validate_phase26_proof_bundle(Path("bundle"))
    assert ok
    assert failures == []


def test_query_returns_provenance(tmp_path: Path):
    ledger = _ledger(tmp_path)
    ledger.append_memory_event(_memory_payload(provenance_refs=["proof:a"]), created_at=NOW)
    result = ledger.query(subject="agent0:test")
    assert result[0]["provenance_refs"] == ["proof:a"]
    assert result[0]["claim_boundary"] == "evidence_only"


def test_compaction_refuses_without_receipt(tmp_path: Path):
    ledger = _ledger(tmp_path)
    ledger.append_memory_event(_memory_payload(), created_at=NOW)
    with pytest.raises(MemoryLedgerError, match="receipt_required"):
        ledger.compact(summary="unsafe", receipt_refs=[])


def test_scan_refuses_under_panic(tmp_path: Path):
    ledger = _ledger(tmp_path)
    ledger.append_memory_event(_memory_payload(), created_at=NOW)
    with pytest.raises(MemoryLedgerError, match="REFUSED_PANIC"):
        ledger.query(control=OperationControl(panic_active=True))
