"""TER Phase 0 — policy, executor, receipts, RTC, and SRP integration."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_PY = sys.executable

import pytest

from hg_runtime.bus import EventBus, TypeRegistry
from hg_runtime.replay import replay
from hg_runtime import world_state as ws
from hg_srp import (
    ChangeApprovalSignature,
    SelfMaintenanceLoop,
    attempt_bundle_apply,
    build_test_command_request,
    execute_evidence_command,
    ingest_pytest_failure_artifact,
    ter_receipt_as_evidence,
)
from hg_ter import TERExecutor, evaluate_policy
from hg_ter.redaction import redact_text
from hg_ter.types import CommandRequest, POLICY_VERSION, TERConfig, argv_hash


NOW = "2026-06-11T12:00:00.000000Z"
SAFE_TEST = "tests/ter/test_safe_fixture.py"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _request(argv: tuple[str, ...], cwd: Path | None = None, **kwargs) -> CommandRequest:
    root = _repo_root()
    return CommandRequest(
        request_id="ter_req_test",
        requested_by="test",
        purpose="unit_test",
        argv=argv,
        cwd=str(cwd or root),
        created_at=NOW,
        **kwargs,
    )


def test_default_deny_unknown_command():
    decision = evaluate_policy(_request(("node", "--version")))
    assert not decision.allowed
    assert decision.reason_code == "not_on_allowlist"


def test_allowed_git_status():
    decision = evaluate_policy(_request(("git", "status", "--short")))
    assert decision.allowed
    assert decision.reason_code == "allowed"


def test_allowed_pytest():
    decision = evaluate_policy(_request(("python", "-m", "pytest", SAFE_TEST, "-q")))
    assert decision.allowed


def test_shell_interpreter_refused():
    decision = evaluate_policy(_request(("bash", "-c", "echo hi")))
    assert not decision.allowed
    assert decision.reason_code == "shell_interpreter_forbidden"


def test_shell_metacharacters_refused():
    decision = evaluate_policy(_request(("git", "status;", "rm", "-rf", "/")))
    assert not decision.allowed
    assert decision.reason_code == "shell_metacharacters_forbidden"


def test_git_push_refused():
    decision = evaluate_policy(_request(("git", "push", "origin", "main")))
    assert not decision.allowed
    assert decision.reason_code in ("forbidden_git_subcommand:push", "git_push_forbidden")


def test_network_command_refused():
    decision = evaluate_policy(_request(("curl", "https://example.com")))
    assert not decision.allowed


def test_package_install_refused():
    decision = evaluate_policy(_request(("pip", "install", "requests")))
    assert not decision.allowed


def test_destructive_rm_refused():
    decision = evaluate_policy(_request(("rm", "-rf", "src")))
    assert not decision.allowed


def test_invalid_cwd_refused(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    decision = evaluate_policy(_request(("git", "status"), cwd=outside))
    assert not decision.allowed
    assert decision.reason_code == "cwd_outside_repo"


def _executor(tmp_path: Path, **kwargs) -> TERExecutor:
    artifact_root = tmp_path / "artifacts"
    return TERExecutor(
        config=TERConfig(
            repo_root=str(_repo_root()),
            artifact_root=str(artifact_root),
            **kwargs,
        )
    )


def test_executor_runs_allowed_command(tmp_path):
    executor = _executor(tmp_path)
    request = executor.make_request(("python", "--version"), requested_by="test", purpose="version_check")
    receipt, result = executor.execute(request, env=os.environ)
    assert receipt.result_status == "ok"
    assert receipt.stdout_artifact is not None
    assert Path(receipt.stdout_artifact).exists()
    assert result.exit_code == 0


def test_timeout_enforced(tmp_path, monkeypatch):
    monkeypatch.setenv("TER_ALLOW_SLEEP_TEST", "1")
    executor = _executor(tmp_path, default_timeout_seconds=0.3)
    request = executor.make_request(
        (_PY, "-c", "import time; time.sleep(2)"),
        requested_by="test",
        purpose="timeout_fixture",
        timeout_seconds=0.3,
    )
    receipt, result = executor.execute(request, env=os.environ)
    assert receipt.timed_out
    assert receipt.result_status == "timed_out"
    assert result.result_status == "timed_out"


def test_secrets_redacted(tmp_path):
    text, applied = redact_text("api_key=supersecret sk-abcdefghijklmnopqrstuvwxyz")
    assert applied
    assert "supersecret" not in text
    assert "[REDACTED]" in text


def test_refused_command_creates_receipt(tmp_path):
    executor = _executor(tmp_path)
    request = executor.make_request(("git", "push"), requested_by="test", purpose="should_refuse")
    receipt, outcome = executor.execute(request)
    assert receipt.result_status == "refused"
    assert receipt.refusal_reason is not None
    assert outcome.reason_code == receipt.refusal_reason


def test_receipt_hash_deterministic():
    argv = ("python", "--version")
    assert argv_hash(argv) == argv_hash(argv)
    assert argv_hash(argv) != argv_hash(("python", "--help"))


def test_ter_events_registered():
    registry = TypeRegistry()
    for name in (
        "TER_COMMAND_REQUESTED",
        "TER_COMMAND_POLICY_EVALUATED",
        "TER_COMMAND_REFUSED",
        "TER_COMMAND_STARTED",
        "TER_COMMAND_COMPLETED",
        "TER_COMMAND_TIMED_OUT",
        "TER_COMMAND_RECEIPT_RECORDED",
    ):
        assert name in registry


def test_rtc_ter_events_emit_and_replay(tmp_path):
    from hg_ter.rtc_bridge import execute_argv_with_bus

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    bus = EventBus(runtime_dir, clock=lambda: NOW)
    executor = _executor(tmp_path)
    receipt, _ = execute_argv_with_bus(
        bus,
        (_PY, "--version"),
        executor=executor,
        requested_by="test",
        purpose="rtc_emit",
    )
    result = replay(runtime_dir)
    assert result.ok is True
    state = result.state
    assert state["activity"]["ter"]["commands_requested"] >= 1
    assert state["activity"]["ter"]["last_receipt_hash"] == receipt.receipt_hash


def test_srp_references_ter_receipt_as_evidence(tmp_path):
    request = build_test_command_request(SAFE_TEST)
    receipt, _ = execute_evidence_command(request)
    evidence = ter_receipt_as_evidence(receipt)
    assert evidence["evidence_kind"] == "ter_command_receipt"
    assert evidence["receipt_hash"].startswith("sha256:")


def test_srp_direct_apply_still_refused(tmp_path):
    artifact_root = tmp_path / "srp"
    proof_root = tmp_path / "proofs"
    fixture = _repo_root() / "tests" / "srp" / "fixtures" / "pytest_failure_sample.json"
    obs = ingest_pytest_failure_artifact(fixture, observed_at=NOW)
    loop = SelfMaintenanceLoop(artifact_root=artifact_root, proof_root=proof_root)
    _, bundle = loop.run([obs], created_at=NOW)
    approval = ChangeApprovalSignature(
        approval_id="ter_test_apr",
        proposal_ref=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        approver="human:test",
        decision="approved",
        decided_at=NOW,
    )
    result = attempt_bundle_apply(bundle, approval=approval)
    assert not result.ok
    assert result.reason_code == "ter_execution_not_enabled"


def test_shell_true_impossible_via_executor():
    """Executor uses subprocess with shell=False; argv list only."""
    import inspect
    import subprocess

    source = inspect.getsource(TERExecutor.execute) + inspect.getsource(TERExecutor._execute_body)
    assert "shell=False" in source
    assert "shell=True" not in source
    with pytest.raises((FileNotFoundError, subprocess.SubprocessError, OSError)):
        subprocess.run(["this_executable_does_not_exist_xyz"], shell=False, capture_output=True)
