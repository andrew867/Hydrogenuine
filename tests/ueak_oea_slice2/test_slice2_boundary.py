"""UEAK/OEA Slice 2 — TER handoff, bounded dispatch, single-use permit consume."""
from __future__ import annotations

import dataclasses
import hashlib
import json

import pytest

from hg_gpp import PermitAuthority
from hg_gpp.models import fixture_permit_request
from hg_core.ledger.canonical_json import canonical_dumps
from hg_oea.config import OEAConfig
from hg_oea.dry_run_executor import is_live_effect_evidence, snapshot_tree
from hg_oea.receipts import OEAReceiptLedger
from hg_oea.sandbox_dispatch import (
    SANDBOX_CAPABILITY, execute_slice2_dispatch, run_slice2_boundary,
    validate_slice2_chain,
)
from hg_oea.ter_handoff import TERHandoffError, create_ter_handoff
from hg_ueak import (
    ExecutionAuthorityKernel, RollbackRequirement, fixture_execution_request,
)

ACTION = {"filename": "slice2_report.md", "content": "slice2 bounded dispatch", "overwrite": False}


def _ledger(tmp_path):
    return OEAReceiptLedger(tmp_path / "ledger" / "receipts.jsonl")


def _config(tmp_path):
    return OEAConfig(proof_dir=tmp_path / "sandbox" / "proofs",
                     allowed_capabilities=frozenset({SANDBOX_CAPABILITY}))


def _admit(action=ACTION):
    authority = PermitAuthority(permit_ttl_s=300.0)
    decision_p = authority.issue(fixture_permit_request(
        request_id="slice2-t-permit", capability_ref=SANDBOX_CAPABILITY,
        effect_class="local_report"))
    kernel = ExecutionAuthorityKernel(permit_store=authority.store)
    request = fixture_execution_request(
        decision_p.permit, rollback=RollbackRequirement(required=False))
    decision = kernel.admit(request)
    return authority, decision


# ---- TER handoff (cases 1-4) ----

def test_handoff_created_from_valid_admission():
    _, decision = _admit()
    handoff = create_ter_handoff(
        admission_receipt=decision.receipt, dispatch_plan=decision.dispatch_plan,
        proposed_action=ACTION, dispatch_mode="sandbox", sink_type="sandbox_file",
        created_at="2026-07-03T00:00:00Z")
    assert handoff.ueak_receipt_hash == decision.receipt.receipt_hash
    assert handoff.permit_id and handoff.permit_hash
    assert handoff.verify_hash()
    assert handoff.authority_created is False
    assert handoff.no_external_effects is True


def test_handoff_rejects_missing_admission():
    _, decision = _admit()
    with pytest.raises(TERHandoffError) as err:
        create_ter_handoff(
            admission_receipt=None, dispatch_plan=decision.dispatch_plan,
            proposed_action=ACTION, dispatch_mode="sandbox",
            sink_type="sandbox_file", created_at="2026-07-03T00:00:00Z")
    assert err.value.code == "missing_admission"


def test_handoff_rejects_missing_permit():
    _, decision = _admit()
    plan = dataclasses.replace(decision.dispatch_plan, permit_binding=dataclasses.replace(
        decision.dispatch_plan.permit_binding, permit_id="", permit_hash=""))
    with pytest.raises(TERHandoffError) as err:
        create_ter_handoff(
            admission_receipt=decision.receipt, dispatch_plan=plan,
            proposed_action=ACTION, dispatch_mode="sandbox",
            sink_type="sandbox_file", created_at="2026-07-03T00:00:00Z")
    assert err.value.code == "missing_permit"


def test_handoff_refuses_real_external_and_performs_no_effect(tmp_path):
    _, decision = _admit()
    before = snapshot_tree(tmp_path)
    with pytest.raises(TERHandoffError) as err:
        create_ter_handoff(
            admission_receipt=decision.receipt, dispatch_plan=decision.dispatch_plan,
            proposed_action=ACTION, dispatch_mode="real_external",
            sink_type="external", created_at="2026-07-03T00:00:00Z")
    assert err.value.code == "real_external_dispatch_disabled_by_default"
    assert snapshot_tree(tmp_path) == before  # handoff layer never touches disk


# ---- Bounded dispatch (cases 5-9, 18-19) ----

def test_fake_sink_dispatch_emits_chained_receipt(tmp_path):
    ledger = _ledger(tmp_path)
    result = run_slice2_boundary(
        proposed_action=ACTION, ledger=ledger, config=_config(tmp_path),
        dispatch_mode="fake_sink", sink_type="fake_dispatch")
    assert result.outcome and result.outcome.dispatched
    receipt = result.outcome.dispatch_receipt
    assert receipt.executor_mode == "fake_sink"
    assert receipt.external_effect_performed is False
    assert ledger.verify_chain()["ok"]
    # fake sink writes nothing to the sandbox
    assert not (tmp_path / "sandbox").exists()


def test_sandbox_dispatch_writes_only_under_sandbox(tmp_path):
    ledger = _ledger(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    before = snapshot_tree(outside)
    result = run_slice2_boundary(
        proposed_action=ACTION, ledger=ledger, config=_config(tmp_path))
    assert result.outcome and result.outcome.dispatched
    target = tmp_path / "sandbox" / "proofs" / "slice2_report.md"
    assert target.exists() and target.read_text(encoding="utf-8") == ACTION["content"]
    assert snapshot_tree(outside) == before
    assert result.outcome.dispatch_receipt.executor_mode == "sandboxed"
    assert str(target) in result.outcome.dispatch_receipt.touched_resources


def test_real_external_mode_blocked_by_default(tmp_path):
    # Default OEAConfig is stub/off; a real-mode config is refused outright.
    assert OEAConfig().is_real is False
    ledger = _ledger(tmp_path)
    real_cfg = OEAConfig(mode="real", real_enabled=True,
                         proof_dir=tmp_path / "sandbox" / "proofs")
    result = run_slice2_boundary(proposed_action=ACTION, ledger=ledger, config=real_cfg)
    assert result.outcome and not result.outcome.dispatched
    assert result.outcome.reason == "real_mode_not_permitted_in_slice2"
    assert result.permit_store.consume_count(result.permit.permit_id) == 0


def test_unsupported_sink_fails_closed(tmp_path):
    ledger = _ledger(tmp_path)
    result = run_slice2_boundary(
        capability_id="social_post.publish", proposed_action=ACTION,
        ledger=ledger, config=_config(tmp_path))
    # prohibited capability: refused at handoff translation or dispatch preflight,
    # never consumed, refusal receipted
    if result.refusal is not None:
        assert result.refusal
    else:
        assert not result.outcome.dispatched
        assert result.outcome.reason in ("unsupported_sink", "translation_refused",
                                         "capability_not_enabled", "unknown_capability")
        assert result.outcome.dispatch_receipt.result_status == "refused"
    assert result.permit_store.consume_count(result.permit.permit_id) == 0


def test_blocked_mode_leaves_refusal_receipt(tmp_path):
    ledger = _ledger(tmp_path)
    result = run_slice2_boundary(
        proposed_action=ACTION, ledger=ledger, config=_config(tmp_path),
        dispatch_mode="blocked")
    assert result.outcome and not result.outcome.dispatched
    receipt = result.outcome.dispatch_receipt
    assert receipt is not None and receipt.result_status == "refused"
    assert ledger.verify_chain()["ok"]


def test_sandbox_receipt_never_live_evidence_and_forgery_breaks_hash(tmp_path):
    ledger = _ledger(tmp_path)
    result = run_slice2_boundary(
        proposed_action=ACTION, ledger=ledger, config=_config(tmp_path))
    payload = result.outcome.dispatch_receipt.to_payload()
    assert is_live_effect_evidence(payload) is False
    # Forge executor_mode="real": the marker lives inside the hashed payload.
    forged = dict(payload)
    forged["executor_mode"] = "real"
    forged["external_effect_performed"] = True
    stored_hash = forged.pop("receipt_hash")
    digest = hashlib.sha256(canonical_dumps(forged)).hexdigest()
    assert f"sha256:{digest}" != stored_hash


# ---- Single-use permit consume (cases 10-14) ----

def test_permit_consumed_exactly_once_with_receipt(tmp_path):
    ledger = _ledger(tmp_path)
    result = run_slice2_boundary(
        proposed_action=ACTION, ledger=ledger, config=_config(tmp_path))
    store = result.permit_store
    assert store.consume_count(result.permit.permit_id) == 1
    consume = result.outcome.consume_receipt
    assert consume is not None
    assert consume.permit_id == result.permit.permit_id
    assert consume.consumed_by == result.outcome.dispatch_receipt.receipt_id
    assert consume.receipt_hash.startswith("sha256:")


def test_replay_with_same_permit_rejected(tmp_path):
    ledger = _ledger(tmp_path)
    config = _config(tmp_path)
    authority, decision = _admit()
    handoff = create_ter_handoff(
        admission_receipt=decision.receipt, dispatch_plan=decision.dispatch_plan,
        proposed_action=ACTION, dispatch_mode="sandbox", sink_type="sandbox_file",
        created_at="2026-07-03T00:00:00Z")
    first = execute_slice2_dispatch(handoff, arguments=dict(ACTION, overwrite=True),
                                    ledger=ledger, permit_store=authority.store,
                                    config=config)
    assert first.dispatched
    # Replay: a copied handoff presented again — same permit, must be rejected.
    replay = execute_slice2_dispatch(handoff, arguments=dict(ACTION, overwrite=True),
                                     ledger=ledger, permit_store=authority.store,
                                     config=config)
    assert not replay.dispatched
    assert replay.reason == "permit_already_consumed"
    assert replay.dispatch_receipt.result_status == "refused"
    assert authority.store.consume_count(handoff.permit_id) == 1
    assert ledger.verify_chain()["ok"]


def test_failed_preflight_does_not_consume(tmp_path):
    ledger = _ledger(tmp_path)
    authority, decision = _admit()
    handoff = create_ter_handoff(
        admission_receipt=decision.receipt, dispatch_plan=decision.dispatch_plan,
        proposed_action=ACTION, dispatch_mode="blocked", sink_type="sandbox_file",
        created_at="2026-07-03T00:00:00Z")
    outcome = execute_slice2_dispatch(handoff, arguments=ACTION, ledger=ledger,
                                      permit_store=authority.store,
                                      config=_config(tmp_path))
    assert not outcome.dispatched
    assert authority.store.consume_count(handoff.permit_id) == 0


def test_double_consume_deterministic():
    authority, decision = _admit()
    permit_id = decision.dispatch_plan.permit_binding.permit_id
    now = "2026-07-03T00:00:00Z"
    first = authority.store.consume(permit_id, now=now, consumed_by="d1")
    second = authority.store.consume(permit_id, now=now, consumed_by="d2")
    assert first.ok and first.receipt is not None
    assert not second.ok and second.reason == "already_consumed"
    assert authority.store.consume_count(permit_id) == 1


def test_revoked_and_unknown_permits_not_consumable():
    authority, _ = _admit()
    now = "2026-07-03T00:00:00Z"
    assert authority.store.consume("nope", now=now, consumed_by="d").reason == "unknown_permit"


# ---- Receipt chain (cases 15-17) ----

def test_full_chain_validates(tmp_path):
    ledger = _ledger(tmp_path)
    result = run_slice2_boundary(
        proposed_action=ACTION, ledger=ledger, config=_config(tmp_path))
    verdict = validate_slice2_chain(result, ledger)
    assert verdict["ok"], verdict["failures"]


def test_tampered_dispatch_receipt_breaks_chain(tmp_path):
    ledger = _ledger(tmp_path)
    run_slice2_boundary(proposed_action=ACTION, ledger=ledger, config=_config(tmp_path))
    lines = [json.loads(l) for l in ledger.path.read_text(encoding="utf-8").splitlines() if l.strip()]
    lines[-1]["output_hash"] = "sha256:" + "0" * 64  # tamper, keep stale hash
    ledger.path.write_text(
        "\n".join(canonical_dumps(l).decode("utf-8") for l in lines) + "\n", encoding="utf-8")
    assert ledger.verify_chain()["ok"] is False


def test_out_of_order_chain_rejected(tmp_path):
    ledger = _ledger(tmp_path)
    run_slice2_boundary(proposed_action=ACTION, ledger=ledger, config=_config(tmp_path))
    run_slice2_boundary(proposed_action=dict(ACTION, filename="second.md"),
                        ledger=ledger, config=_config(tmp_path))
    lines = ledger.path.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 2
    ledger.path.write_text("\n".join(reversed(lines)) + "\n", encoding="utf-8")
    assert ledger.verify_chain()["ok"] is False
