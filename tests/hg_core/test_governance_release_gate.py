import sys
from pathlib import Path

_workspace = Path(__file__).resolve().parents[2]
if str(_workspace) not in sys.path:
    sys.path.insert(0, str(_workspace))


def test_policy_gate_blocks_without_release_verdict(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    monkeypatch.setenv("HG_ENV", "test")
    monkeypatch.setenv("HG_RELEASE_GATE_ENFORCED", "1")

    from hg_realtime.integrations.policy_gate import PolicyGate

    decision = PolicyGate().allow_run(
        tenant_id="default",
        actor_id="operator",
        workflow_id="social",
        resolved_inputs={},
        correlation_id="corr-1",
    )
    assert decision.allowed is False
    assert "missing release verdict" in decision.reason


def test_policy_gate_skips_release_gate_when_demo_live_actions_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    monkeypatch.setenv("HG_ENV", "demo")
    monkeypatch.setenv("HG_DEMO_MODE", "1")
    monkeypatch.setenv("HG_DEMO_LIVE_ACTIONS_ENABLED", "1")
    monkeypatch.delenv("HG_RELEASE_GATE_ENFORCED", raising=False)

    from hg_realtime.integrations.policy_gate import PolicyGate

    decision = PolicyGate().allow_run(
        tenant_id="default",
        actor_id="operator",
        workflow_id="social-media",
        resolved_inputs={},
        correlation_id="corr-demo-live",
    )
    assert decision.allowed is True


def test_policy_gate_allows_with_eligible_release_verdict(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    monkeypatch.setenv("HG_ENV", "test")
    monkeypatch.setenv("HG_RELEASE_GATE_ENFORCED", "1")

    from hg_core.gate import create_benchmark_set, record_benchmark_run, evaluate_benchmark_run, create_release_verdict
    from hg_realtime.integrations.policy_gate import PolicyGate

    bench = create_benchmark_set(workflow_family="social", title="Gate", description="Test", weights={"p_h": 0.3, "p_ai": 0.2, "p_h_odei": 0.5})
    run = record_benchmark_run(benchmark_set_id=bench["benchmark_set_id"], workflow_family="social", candidate_label="v1", observations={"p_h": 0.7, "p_ai": 0.5, "p_h_odei": 0.8})
    evaluation = evaluate_benchmark_run(benchmark_run_id=run["benchmark_run_id"])
    create_release_verdict(workflow_family="social", target_kind="workflow", target_id="social", evaluation_id=evaluation["evaluation_id"], verdict="eligible", reason="ready")

    decision = PolicyGate().allow_run(
        tenant_id="default",
        actor_id="operator",
        workflow_id="social",
        resolved_inputs={},
        correlation_id="corr-1",
    )
    assert decision.allowed is True
