"""MEL Phase 1 — append-only hash-chained ledger."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from hg_csm import evaluate_change
from hg_mel import (
    MaintenanceLedger,
    record_csm_decision,
    record_final_verdict,
    record_proposal,
    record_ter_receipt,
)
from hg_mel.redaction import redact_payload
from hg_mel.types import GENESIS_HASH, LedgerRecord
from hg_srp.bundle import create_maintenance_bundle
from hg_srp.intake import ingest_pytest_failure_artifact
from hg_ter.types import CommandReceipt

NOW = "2026-06-11T12:00:00.000000Z"
FIXTURE = Path(__file__).resolve().parents[1] / "srp" / "fixtures" / "pytest_failure_sample.json"


def test_records_append(tmp_path: Path):
    ledger = MaintenanceLedger(tmp_path / "mel.jsonl")
    record = record_proposal(ledger, bundle_id="b1", bundle_hash="sha256:aaa", payload={"status": "proposed"})
    assert record.record_type == "MEL_PROPOSAL_RECORDED"
    assert ledger.head_hash == record.record_hash


def test_hash_chain_verifies(tmp_path: Path):
    ledger = MaintenanceLedger(tmp_path / "mel.jsonl")
    record_proposal(ledger, bundle_id="b1", bundle_hash="sha256:aaa", payload={"n": 1})
    record_final_verdict(ledger, bundle_id="b1", bundle_hash="sha256:aaa", verdict="ok", reason_code="test")
    verify = ledger.verify_chain()
    assert verify.ok
    assert verify.records_checked == 2
    assert verify.head_hash is not None


def test_mutation_breaks_chain(tmp_path: Path):
    path = tmp_path / "mel.jsonl"
    ledger = MaintenanceLedger(path)
    record_proposal(ledger, bundle_id="b1", bundle_hash="sha256:aaa", payload={"n": 1})
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    tampered = json.loads(lines[0])
    tampered["payload_redacted"]["n"] = 999
    path.write_text(json.dumps(tampered) + "\n", encoding="utf-8")
    ledger2 = MaintenanceLedger(path)
    verify = ledger2.verify_chain()
    assert not verify.ok


def test_secret_redaction():
    redacted, applied = redact_payload({"api_key": "secret123", "note": "Bearer abcdef"})
    assert applied
    assert redacted["api_key"] == "[REDACTED]"
    assert "[REDACTED]" in redacted["note"]


def test_ledger_records_csm_and_ter(tmp_path: Path):
    obs = ingest_pytest_failure_artifact(FIXTURE, observed_at=NOW)
    bundle = create_maintenance_bundle([obs], created_at=NOW)
    from hg_csm.policy import change_request_from_bundle

    request = change_request_from_bundle(bundle, proposed_files=("docs/reports/phases/x.md",))
    decision = evaluate_change(request)

    ledger = MaintenanceLedger(tmp_path / "mel.jsonl")
    record_proposal(ledger, bundle_id=bundle.bundle_id, bundle_hash=bundle.bundle_hash, payload={})
    record_csm_decision(ledger, decision)

    receipt = CommandReceipt(
        receipt_id="rcpt_1",
        request_id="req_1",
        argv_hash="sha256:argv",
        cwd=str(tmp_path),
        started_at=NOW,
        completed_at=NOW,
        exit_code=0,
        timed_out=False,
        stdout_artifact=None,
        stderr_artifact=None,
        stdout_hash=None,
        stderr_hash=None,
        redaction_applied=False,
        changed_files_summary=(),
        result_status="ok",
        refusal_reason=None,
        policy_version="ter_policy_phase0_v1",
    )
    record_ter_receipt(ledger, receipt, bundle_id=bundle.bundle_id)
    record_final_verdict(
        ledger, bundle_id=bundle.bundle_id, bundle_hash=bundle.bundle_hash, verdict="pending", reason_code="test"
    )
    assert ledger.verify_chain().ok
    assert ledger.verify_chain().records_checked == 4


def test_genesis_hash_first_record(tmp_path: Path):
    ledger = MaintenanceLedger(tmp_path / "mel.jsonl")
    record = record_proposal(ledger, bundle_id="b1", bundle_hash="sha256:aaa", payload={})
    assert record.previous_record_hash == GENESIS_HASH
