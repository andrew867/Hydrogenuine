"""OEA bounded external actuation tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from hg_oea.binding import BindingError, create_binding
from hg_oea.bounded_executor import OEABoundedExecutor
from hg_oea.config import OEAConfig
from hg_oea.dry_run import perform_dry_run
from hg_oea.factory import create_oea_executor
from hg_oea.registry import lookup_capability
from hg_oea.receipts import OEAReceiptLedger
from hg_oea.validation import ValidationError, input_hash, redact_text, validate_arguments
from hg_runtime.bus import EventBus
from hg_runtime.handlers.stubs import StubKernelHandler
from hg_runtime.replay import replay
from hg_ueak.commit_scaffold import CommitScaffold


NOW = "2026-06-12T01:00:00.000000Z"


def _config(tmp_path: Path) -> OEAConfig:
    return OEAConfig(
        mode="real",
        real_enabled=True,
        allowed_capabilities=frozenset({"local_report_file.write"}),
        proof_dir=tmp_path / "proof",
        require_confirmation_for_medium=True,
        disable_network=True,
    )


def _commit_payload(**overrides):
    action = {
        "action_type": "local_report_file_write",
        "capability_id": "local_report_file.write",
        "effect_class": "local_report",
        "arguments": {
            "filename": "marker.txt",
            "content": "oea-proof",
            "overwrite": True,
        },
    }
    action.update(overrides.get("action", {}))
    payload = {
        "commit_ref": "ueak_commit_test_1",
        "request_id": "exec_req_test_1",
        "decision_id": "dec_test_1",
        "capability_id": "local_report_file.write",
        "effect_class": "local_report",
        "action": action,
    }
    payload.update({k: v for k, v in overrides.items() if k != "action"})
    return payload


def test_capability_registry_loads_safe_capability():
    capability = lookup_capability("local_report_file.write")
    assert capability is not None
    assert capability.risk_class == "harmless"
    assert capability.enabled_by_default is True


def test_disabled_capability_refuses(tmp_path: Path):
    config = _config(tmp_path)
    config = OEAConfig(
        mode="real",
        real_enabled=True,
        allowed_capabilities=frozenset(),
        proof_dir=tmp_path / "proof",
    )
    with pytest.raises(BindingError, match="scope_required|capability_disabled"):
        create_binding(
            capability_id="local_report_file.write",
            ueak_commit_ref="ueak_1",
            authority_ref="auth_1",
            requested_by="test",
            arguments={"filename": "a.txt", "content": "x"},
            created_at=NOW,
            config=config,
            skip_dry_run_check=True,
        )


def test_prohibited_capability_refuses(tmp_path: Path):
    config = _config(tmp_path)
    config = OEAConfig(
        mode="real",
        real_enabled=True,
        allowed_capabilities=frozenset({"social_post.publish"}),
        proof_dir=tmp_path / "proof",
    )
    with pytest.raises(BindingError, match="capability_disabled|capability_prohibited"):
        create_binding(
            capability_id="social_post.publish",
            ueak_commit_ref="ueak_1",
            authority_ref="auth_1",
            requested_by="test",
            arguments={},
            created_at=NOW,
            config=config,
            skip_dry_run_check=True,
        )


def test_invalid_args_refuse(tmp_path: Path):
    capability = lookup_capability("local_report_file.write")
    assert capability is not None
    with pytest.raises(ValidationError):
        validate_arguments(capability, {"filename": "../evil.txt", "content": "x"})


def test_path_traversal_refuses(tmp_path: Path):
    capability = lookup_capability("local_report_file.write")
    assert capability is not None
    with pytest.raises(ValidationError):
        validate_arguments(capability, {"filename": "../evil", "content": "x"})


def test_oversized_payload_refuses(tmp_path: Path):
    capability = lookup_capability("local_report_file.write")
    assert capability is not None
    with pytest.raises(ValidationError):
        validate_arguments(capability, {"filename": "big.txt", "content": "x" * 70000})


def test_missing_ueak_commit_refuses(tmp_path: Path):
    config = _config(tmp_path)
    with pytest.raises(BindingError, match="missing_ueak_commit_ref"):
        create_binding(
            capability_id="local_report_file.write",
            ueak_commit_ref="",
            authority_ref="auth_1",
            requested_by="test",
            arguments={"filename": "a.txt", "content": "x"},
            created_at=NOW,
            config=config,
            skip_dry_run_check=True,
        )


def test_binding_hash_changes_if_args_change(tmp_path: Path):
    config = _config(tmp_path)
    b1 = create_binding(
        capability_id="local_report_file.write",
        ueak_commit_ref="ueak_1",
        authority_ref="auth_1",
        requested_by="test",
        arguments={"filename": "a.txt", "content": "one"},
        created_at=NOW,
        config=config,
        skip_dry_run_check=True,
    )
    b2 = create_binding(
        capability_id="local_report_file.write",
        ueak_commit_ref="ueak_1",
        authority_ref="auth_1",
        requested_by="test",
        arguments={"filename": "a.txt", "content": "two"},
        created_at=NOW,
        config=config,
        skip_dry_run_check=True,
    )
    assert b1.input_hash != b2.input_hash


def test_dry_run_required_without_dry_run_refuses(tmp_path: Path):
    config = _config(tmp_path)
    with pytest.raises(BindingError, match="dry_run_required"):
        create_binding(
            capability_id="local_report_file.write",
            ueak_commit_ref="ueak_1",
            authority_ref="auth_1",
            requested_by="test",
            arguments={"filename": "a.txt", "content": "x", "overwrite": True},
            created_at=NOW,
            config=config,
        )


def test_local_proof_writes_only_inside_owned_path(tmp_path: Path):
    config = _config(tmp_path)
    executor = OEABoundedExecutor(config, clock=lambda: NOW)
    drafts = executor.dispatch_committed(
        [
            {
                "type": "UEAK_EXECUTION_COMMITTED",
                "event_id": "evt_commit_1",
                "payload": _commit_payload(),
            }
        ]
    )
    types = [d["type"] for d in drafts]
    assert "OEA_EXECUTION_COMPLETED" in types
    marker = config.proof_dir / "marker.txt"
    assert marker.exists()
    assert marker.read_text(encoding="utf-8") == "oea-proof"
    assert str(marker.resolve()).startswith(str(config.proof_dir.resolve()))


def test_invalid_path_refused(tmp_path: Path):
    config = _config(tmp_path)
    executor = OEABoundedExecutor(config, clock=lambda: NOW)
    payload = _commit_payload()
    payload["action"]["arguments"]["filename"] = "sub/escape.txt"
    drafts = executor.dispatch_committed(
        [{"type": "UEAK_EXECUTION_COMMITTED", "event_id": "evt_1", "payload": payload}]
    )
    assert any(d["type"] == "OEA_BINDING_REFUSED" for d in drafts)


def test_receipt_contains_hashes(tmp_path: Path):
    config = _config(tmp_path)
    executor = OEABoundedExecutor(config, clock=lambda: NOW)
    executor.dispatch_committed(
        [{"type": "UEAK_EXECUTION_COMMITTED", "event_id": "evt_1", "payload": _commit_payload()}]
    )
    receipt = executor.effect_records[0]
    assert receipt["input_hash"].startswith("sha256:")
    assert receipt["output_hash"].startswith("sha256:")
    ledger = OEAReceiptLedger(config.proof_dir / "receipts.jsonl")
    assert ledger.verify_chain()["ok"] is True


def test_receipt_redacts_secrets():
    text = redact_text("Bearer abcdefghijklmnop token=secretvalue")
    assert "[REDACTED]" in text


def test_real_mode_does_not_fall_back_to_stub(tmp_path: Path):
    config = _config(tmp_path)
    executor = create_oea_executor(config)
    assert executor.handler_id == "oea.bounded.executor"
    drafts = executor.dispatch_committed(
        [{"type": "UEAK_EXECUTION_COMMITTED", "event_id": "evt_1", "payload": _commit_payload()}]
    )
    assert not any(d["type"] == "OEA_EFFECT_STUB_RECORDED" for d in drafts)
    assert any(d["type"] == "OEA_EFFECT_RECEIPT_RECORDED" for d in drafts)


def test_stub_mode_explicit_and_labeled():
    config = OEAConfig(mode="stub", real_enabled=False)
    executor = create_oea_executor(config)
    assert executor.handler_id == "oea.phase1.stub_executor"
    drafts = executor.dispatch_committed(
        [
            {
                "type": "UEAK_EXECUTION_COMMITTED",
                "event_id": "evt_1",
                "payload": {
                    "commit_ref": "ueak_1",
                    "request_id": "req_1",
                    "effect_class": "audit_log",
                    "action": {"action_type": "oea_stub_log"},
                },
            }
        ]
    )
    receipt = next(d for d in drafts if d["type"] == "EFFECT_RECEIPTED")
    assert receipt["payload"]["executor_mode"] == "stub"


def test_rtc_events_replay_deterministically(tmp_path: Path):
    config = _config(tmp_path)
    runtime_dir = tmp_path / "runtime"
    bus = EventBus(runtime_dir, clock=lambda: NOW)
    executor = OEABoundedExecutor(config, clock=lambda: NOW)
    for draft in executor.dispatch_committed(
        [{"type": "UEAK_EXECUTION_COMMITTED", "event_id": "evt_1", "payload": _commit_payload()}]
    ):
        bus.emit_draft(draft, source="oea:test")
    result = replay(runtime_dir)
    assert result.ok is True
    assert result.state["activity"]["oea"]["executions_completed"] == 1


def test_ueak_oea_receipt_chain_linked(tmp_path: Path):
    ueak = CommitScaffold()
    decision = {
        "type": "DECISION_EVENT",
        "event_id": "evt_decision",
        "payload": {
            "decision_id": "dec_1",
            "action": _commit_payload()["action"],
        },
    }
    ueak_drafts = ueak.execute([decision], {})
    assert ueak_drafts[0]["type"] == "UEAK_EXECUTION_COMMITTED"
    config = _config(tmp_path)
    oea = OEABoundedExecutor(config, clock=lambda: NOW)
    oea_drafts = oea.dispatch_committed(
        [
            {
                "type": "UEAK_EXECUTION_COMMITTED",
                "event_id": "evt_commit",
                "payload": ueak_drafts[0]["payload"],
            }
        ]
    )
    receipt_draft = next(d for d in oea_drafts if d["type"] == "EFFECT_RECEIPTED")
    assert receipt_draft["payload"]["commit_ref"] == ueak_drafts[0]["payload"]["commit_ref"]
    assert receipt_draft["payload"]["executor_mode"] == "real"


def test_kernel_real_oea_integration(tmp_path: Path):
    config = _config(tmp_path)
    from hg_oea.bounded_executor import OEABoundedExecutor

    kernel = StubKernelHandler(oea=OEABoundedExecutor(config, clock=lambda: NOW))
    decision = {
        "type": "DECISION_EVENT",
        "event_id": "evt_decision",
        "payload": {"decision_id": "dec_1", "action": _commit_payload()["action"]},
    }
    drafts = kernel.execute([decision], {})
    types = [d["type"] for d in drafts]
    assert "UEAK_EXECUTION_COMMITTED" in types
    assert "OEA_EFFECT_RECEIPT_RECORDED" in types
    assert "EFFECT_RECEIPTED" in types


def test_non_idempotent_capability_does_not_retry_by_default(tmp_path: Path):
    from dataclasses import replace

    from hg_oea.retry import may_retry

    capability = lookup_capability("local_report_file.write")
    assert capability is not None
    non_idempotent = replace(capability, idempotent=False, retry_policy="none")
    assert may_retry(non_idempotent, retry_count=0, result_status="failed") is False
