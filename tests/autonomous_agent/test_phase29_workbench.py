"""Phase 29 governed workbench tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.workbench import (
    ToolRegistry,
    Workbench,
    WorkbenchError,
    WorkbenchPolicy,
    WorkbenchReceiptLog,
    artifact_hash,
    build_invocation_receipt,
    classify_command,
    draft_artifact_receipt,
    validate_phase29_proof_bundle,
    validate_tool_capability,
)
from hg_runtime.workbench.gate import evaluate_phase29_gate
from hg_runtime.memory_ledger.hash_chain import canonical_hash

NOW = "2026-06-19T13:55:00.000000Z"


def _cap(capability_id: str = "tool:read-file", tool_kind: str = "read_file", **overrides):
    payload = {
        "schema": "tool_capability_v1",
        "capability_id": capability_id,
        "tool_kind": tool_kind,
        "description": "governed workbench tool",
        "scope": {"read_only": tool_kind in {"read_file", "inspect_log", "compare_outputs"}},
        "authority_refs": ["gpp:reference-only", "hal:reference-only", "ueak:reference-only", "oea:reference-only"],
        "receipt_required": True,
        "default_mode": "dry_run",
    }
    payload.update(overrides)
    return payload


def _entry(tool_id: str, capability: dict):
    payload = {"schema": "tool_registry_entry_v1", "tool_id": tool_id, "capability": capability}
    payload["registry_hash"] = canonical_hash(payload)
    return payload


def _registry(*entries):
    registry = ToolRegistry()
    for entry in entries:
        registry.register(entry)
    return registry


def _bench(tmp_path: Path, registry: ToolRegistry):
    root = tmp_path / "workspace"
    artifacts = tmp_path / "artifacts"
    root.mkdir()
    artifacts.mkdir()
    source = root / "source.txt"
    source.write_text("hello governed workbench\n", encoding="utf-8")
    policy = WorkbenchPolicy(workspace_root=root, artifact_root=artifacts, read_roots=(root,), mutation_permit_refs=("permit:phase29:test",))
    return Workbench(registry=registry, policy=policy, receipt_log=WorkbenchReceiptLog(tmp_path / "receipts.jsonl")), root, artifacts


def _request(tool_id: str, operation: str, inputs: dict, *, mode: str = "dry_run", receipt_refs=None):
    return {
        "schema": "workbench_request_v1",
        "request_id": "req-" + tool_id.replace(":", "-") + "-" + operation,
        "tool_id": tool_id,
        "operation": operation,
        "mode": mode,
        "inputs": inputs,
        "receipt_refs": list(receipt_refs or []),
        "claim_boundary": "workbench_governed_dry_run_default",
    }


def test_tool_registry_cannot_bypass_authority():
    with pytest.raises(WorkbenchError, match="authority_bypass_attempt"):
        validate_tool_capability(_cap(authority_created=True))


def test_dry_run_does_not_mutate_workspace(tmp_path: Path):
    registry = _registry(_entry("tool:write-artifact", _cap("tool:write-artifact", "write_artifact")))
    bench, _, artifacts = _bench(tmp_path, registry)
    target = artifacts / "draft.md"
    result = bench.invoke(_request("tool:write-artifact", "write", {"path": str(target), "content": "draft"}, receipt_refs=["receipt:phase29:test"]))
    assert result["result"]["mutated"] is False
    assert not target.exists()


def test_live_tool_requires_permit(tmp_path: Path):
    registry = _registry(_entry("tool:write-artifact", _cap("tool:write-artifact", "write_artifact")))
    bench, _, artifacts = _bench(tmp_path, registry)
    with pytest.raises(WorkbenchError, match="receipt_required"):
        bench.invoke(_request("tool:write-artifact", "write", {"path": str(artifacts / "x.md"), "content": "x"}, mode="mutating"))


def test_shell_sandbox_blocks_forbidden_command():
    assert classify_command("rm -rf .").allowed is False
    assert classify_command("rm -rf .").reason == "forbidden_command_rejected"


def test_tool_capability_schema_required():
    with pytest.raises(WorkbenchError, match="schema_violation:missing"):
        validate_tool_capability({"capability_id": "x"})


def test_tool_registry_rejects_unknown_tool(tmp_path: Path):
    bench, root, _ = _bench(tmp_path, _registry())
    with pytest.raises(WorkbenchError, match="unknown_tool_rejected"):
        bench.invoke(_request("tool:missing", "read", {"path": str(root / "source.txt")}))


def test_domain_pack_allowed_tool_is_not_permission():
    with pytest.raises(WorkbenchError, match="authority_bypass_attempt"):
        validate_tool_capability(_cap(domain_pack_as_permission=True))


def test_skill_reference_is_not_permission():
    with pytest.raises(WorkbenchError, match="authority_bypass_attempt"):
        validate_tool_capability(_cap(skill_as_permission=True))


def test_memory_reference_is_not_permission():
    with pytest.raises(WorkbenchError, match="authority_bypass_attempt"):
        validate_tool_capability(_cap(memory_as_permission=True))


def test_read_file_scope_is_enforced(tmp_path: Path):
    registry = _registry(_entry("tool:read-file", _cap()))
    bench, _, _ = _bench(tmp_path, registry)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    with pytest.raises(WorkbenchError, match="read_file_scope_violation"):
        bench.invoke(_request("tool:read-file", "read", {"path": str(outside)}))


def test_write_artifact_scope_is_enforced(tmp_path: Path):
    registry = _registry(_entry("tool:write-artifact", _cap("tool:write-artifact", "write_artifact")))
    bench, root, _ = _bench(tmp_path, registry)
    with pytest.raises(WorkbenchError, match="write_artifact_scope_violation"):
        bench.invoke(_request("tool:write-artifact", "write", {"path": str(root / "bad.md"), "content": "bad"}, receipt_refs=["receipt:phase29:test"]))


def test_credential_path_read_is_rejected(tmp_path: Path):
    registry = _registry(_entry("tool:read-file", _cap()))
    bench, root, _ = _bench(tmp_path, registry)
    secret_path = root / ".env"
    secret_path.write_text("VALUE=redacted\n", encoding="utf-8")
    with pytest.raises(WorkbenchError, match="credential_path_read_rejected"):
        bench.invoke(_request("tool:read-file", "read", {"path": str(secret_path)}))


def test_network_tool_refuses_by_default(tmp_path: Path):
    registry = _registry(_entry("tool:network", _cap("tool:network", "network")))
    bench, _, _ = _bench(tmp_path, registry)
    with pytest.raises(WorkbenchError, match="network_tool_refuses_by_default"):
        bench.invoke(_request("tool:network", "fetch", {"url": "https://example.invalid"}))


def test_package_install_command_is_rejected():
    assert classify_command("pip install example").reason == "package_install_command_rejected"


def test_arbitrary_shell_command_is_rejected():
    assert classify_command("python script.py").reason == "arbitrary_shell_command_rejected"


def test_patch_candidate_is_draft_not_merge(tmp_path: Path):
    registry = _registry(_entry("tool:patch", _cap("tool:patch", "patch_candidate")))
    bench, _, _ = _bench(tmp_path, registry)
    result = bench.invoke(_request("tool:patch", "draft", {"patch": "diff --git a/x b/x"}, receipt_refs=["receipt:phase29:test"]))
    assert result["result"]["draft_only"] is True
    assert result["result"]["merged"] is False


def test_test_run_receipt_required(tmp_path: Path):
    registry = _registry(_entry("tool:test", _cap("tool:test", "test_run")))
    bench, _, _ = _bench(tmp_path, registry)
    with pytest.raises(WorkbenchError, match="test_run_receipt_required"):
        bench.invoke(_request("tool:test", "test", {"command": "python -m pytest tests/autonomous_agent/test_phase29_workbench.py -q"}))


def test_artifact_hash_required():
    receipt = draft_artifact_receipt(artifact_path="draft.md", content="draft", receipt_refs=["receipt:phase29:test"])
    assert receipt["artifact_hash"].startswith("sha256:")


def test_workspace_mutation_requires_policy(tmp_path: Path):
    registry = _registry(_entry("tool:write-artifact", _cap("tool:write-artifact", "write_artifact")))
    bench, _, artifacts = _bench(tmp_path, registry)
    with pytest.raises(WorkbenchError, match="live_tool_requires_permit"):
        bench.invoke(_request("tool:write-artifact", "write", {"path": str(artifacts / "x.md"), "content": "x"}, mode="mutating", receipt_refs=["permit:wrong"]))


def test_dry_run_result_cannot_claim_live_completion():
    request = _request("tool:test", "test", {"command": "python -m pytest x -q"})
    with pytest.raises(WorkbenchError, match="fake_green_rejected"):
        build_invocation_receipt(request=request, status="observed", result={"claims_live_completion": True}, receipt_refs=[])


def test_missing_receipt_blocks_success():
    request = _request("tool:test", "test", {"command": "python -m pytest x -q"})
    with pytest.raises(WorkbenchError, match="missing_receipt_blocks_success"):
        build_invocation_receipt(request=request, status="success", result={"ok": True}, receipt_refs=[])


def test_fake_green_attempt_is_rejected():
    request = _request("tool:test", "test", {"command": "python -m pytest x -q"})
    with pytest.raises(WorkbenchError, match="fake_green_rejected"):
        build_invocation_receipt(request=request, status="green", result={"claims_live_completion": True}, receipt_refs=[])


def test_stop_panic_preempts_workbench_operation(tmp_path: Path):
    registry = _registry(_entry("tool:read-file", _cap()))
    bench, root, _ = _bench(tmp_path, registry)
    with pytest.raises(WorkbenchError, match="REFUSED_STOP"):
        bench.invoke(_request("tool:read-file", "read", {"path": str(root / "source.txt")}), control=OperationControl(stop_active=True))
    with pytest.raises(WorkbenchError, match="REFUSED_PANIC"):
        bench.receipt_log.replay(control=OperationControl(panic_active=True))


def test_replay_divergence_is_failure(tmp_path: Path):
    registry = _registry(_entry("tool:read-file", _cap()))
    bench, root, _ = _bench(tmp_path, registry)
    bench.invoke(_request("tool:read-file", "read", {"path": str(root / "source.txt")}))
    row = json.loads(bench.receipt_log.path.read_text(encoding="utf-8").splitlines()[0])
    row["chain_hash"] = "sha256:bad"
    bench.receipt_log.path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    assert not bench.receipt_log.replay().ok


def test_phase29_gate_refuses_without_phase26_and_phase28_green(tmp_path: Path):
    result = evaluate_phase29_gate(tmp_path, phase26_green=False, phase28_green=True, proof_bundle=None, tests_passed=True)
    assert result["verdict"] == "RED_PHASE29_PHASE26_GREEN_REQUIRED"
    result = evaluate_phase29_gate(tmp_path, phase26_green=True, phase28_green=False, proof_bundle=None, tests_passed=True)
    assert result["verdict"] == "RED_PHASE29_PHASE28_GREEN_REQUIRED"


def test_phase29_gate_refuses_without_proof_bundle(tmp_path: Path):
    result = evaluate_phase29_gate(tmp_path, phase26_green=True, phase28_green=True, proof_bundle=None, tests_passed=True)
    assert result["verdict"] == "RED_PHASE29_PROOF_BUNDLE_MISSING"


def test_workbench_replay_is_deterministic(tmp_path: Path):
    registry = _registry(_entry("tool:read-file", _cap()), _entry("tool:compare", _cap("tool:compare", "compare_outputs")))
    bench, root, _ = _bench(tmp_path, registry)
    bench.invoke(_request("tool:read-file", "read", {"path": str(root / "source.txt")}))
    bench.invoke(_request("tool:compare", "compare", {"left": "a", "right": "a"}))
    a = bench.receipt_log.replay()
    b = bench.receipt_log.replay()
    assert a.ok and b.ok
    assert a.chain_root == b.chain_root


def test_phase29_proof_validator_accepts_resolved_path(tmp_path: Path, monkeypatch):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    for name in ("HEAD.txt", "command_log.jsonl", "manifest.json", "summary.json", "status.md"):
        (bundle / name).write_text("{}\n", encoding="utf-8")
    (bundle / "gate_result.json").write_text(json.dumps({"proof_bundle": str(bundle.resolve())}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    ok, failures = validate_phase29_proof_bundle(Path("bundle"))
    assert ok
    assert failures == []


def test_artifact_hash_is_deterministic():
    assert artifact_hash("same") == artifact_hash("same")
