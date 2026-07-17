import sys
from pathlib import Path

_workspace = Path(__file__).resolve().parents[2]
if str(_workspace) not in sys.path:
    sys.path.insert(0, str(_workspace))


def test_repeated_policy_actions_are_idempotent(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))

    from hg_core.policy_registry import activate_policy_version, create_policy_version, rollback_policy_version

    v1 = create_policy_version(
        policy_key="approval_policy",
        title="Approval Policy",
        category="approval",
        description="Base",
        content={"required_flags": ["human_review"]},
        rationale="r1",
        change_summary="c1",
    )
    v1_dup = create_policy_version(
        policy_key="approval_policy",
        title="Approval Policy",
        category="approval",
        description="Base",
        content={"required_flags": ["human_review"]},
        rationale="r1",
        change_summary="c1",
    )
    assert v1_dup["version_id"] == v1["version_id"]
    activate_policy_version(v1["version_id"])

    v2 = create_policy_version(
        policy_key="approval_policy",
        title="Approval Policy",
        category="approval",
        description="Base",
        content={"required_flags": ["human_review", "benchmark_receipt"]},
        rationale="r2",
        change_summary="c2",
    )
    activate_policy_version(v2["version_id"])
    rolled = rollback_policy_version("approval_policy")
    assert rolled["version_id"] == v1["version_id"]


def test_receipt_tamper_detection_uses_ledger(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))

    from hg_core.receipts import create_sealed_receipt, verify_receipt
    from hg_gateway.db import get_connection

    receipt = create_sealed_receipt(
        tenant_id="default",
        receipt_kind="approval",
        subject_kind="approval",
        subject_id="ap-1",
        payload={"decision": "approve"},
    )
    with get_connection() as conn:
        conn.execute("UPDATE sealed_receipts SET canonical_json = ? WHERE receipt_id = ?", ('{"decision":"deny"}', receipt["receipt_id"]))
    verified = verify_receipt(receipt["receipt_id"])
    assert verified["verification_status"] == "failed"
    assert verified["ledger_ok"] is False


def test_release_verdict_staleness_uses_stale_after_ts(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    monkeypatch.setenv("HG_ENV", "test")

    from hg_core.gate import create_benchmark_set, create_release_verdict, enforce_release_gate, evaluate_benchmark_run, record_benchmark_run
    from hg_gateway.db import get_connection

    bench = create_benchmark_set(workflow_family="social", title="Gate", description="Test", weights={"p_h": 0.3, "p_ai": 0.2, "p_h_odei": 0.5})
    run = record_benchmark_run(benchmark_set_id=bench["benchmark_set_id"], workflow_family="social", candidate_label="v1", observations={"p_h": 0.8, "p_ai": 0.2, "p_h_odei": 0.9})
    evaluation = evaluate_benchmark_run(benchmark_run_id=run["benchmark_run_id"])
    verdict = create_release_verdict(workflow_family="social", target_kind="workflow", target_id="social", evaluation_id=evaluation["evaluation_id"], verdict="eligible", stale_after_hours=24)
    with get_connection() as conn:
        conn.execute("UPDATE gate_release_verdicts SET stale_after_ts = ? WHERE release_verdict_id = ?", ("2000-01-01T00:00:00Z", verdict["release_verdict_id"]))
    status = enforce_release_gate(workflow_family="social")
    assert status["blocked"] is True
    assert status["code"] == "stale_verdict"
