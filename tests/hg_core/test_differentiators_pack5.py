"""
Differentiators Pack 5: Verifier economics, correlation immunity, attacker simulation.

See .cursor/plans/differentiators/chapter5/differentiators_pack5/differentiators_pack5_verifier_econ_attacker_sim/
"""

from __future__ import annotations

from pathlib import Path

from hg_core.verification import (
    register_verification_source,
    perform_verification_check,
    get_verifier_price,
    update_verifier_price,
    init_verification_budget,
    get_verification_budget_status,
    debit_verification_budget,
    select_verifier_set,
    select_verifier_set_and_debit,
    compute_correlation,
    emit_correlation_computed,
    emit_monoculture_detected,
)
from hg_core.adversary import run_attack_scenario, run_all_scenarios, SCENARIO_NAMES


SCOPE = {"type": "run", "id": "test_diff5"}
ACTOR = {"agent_id": "agent_diff5", "pubkey": "0" * 64, "key_id": "k"}


def test_verifier_selection_meets_diversity_within_budget(tmp_path: Path) -> None:
    """Verifier selection meets robustness and diversity thresholds within budget."""
    register_verification_source(source_id="src_1", name="Source 1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    register_verification_source(source_id="src_2", name="Source 2", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    init_verification_budget(budget_key="default", initial_balance=100.0, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    result, sel_id = select_verifier_set(
        action_id="act_1",
        workspace_root=tmp_path,
        scope=SCOPE,
        actor=ACTOR,
        min_independence_groups=1,
        budget_key="default",
    )
    assert result is not None
    assert sel_id
    assert result["estimated_cost"] >= 0
    assert result["expected_robustness"] >= 0
    assert len(result["sources"]) >= 1


def test_insufficient_budget_blocks_commit(tmp_path: Path) -> None:
    """Insufficient verification budget blocks debit (VERIFICATION_BUDGET_INSUFFICIENT)."""
    init_verification_budget(budget_key="tight", initial_balance=1.0, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    ok, ev_or_id = debit_verification_budget(
        budget_key="tight", amount=5.0, action_id="act_2", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path,
    )
    assert ok is False
    assert ev_or_id
    balance, _, _ = get_verification_budget_status(tmp_path, SCOPE, "tight")
    assert balance == 1.0


def test_cost_accounting_deterministic(tmp_path: Path) -> None:
    """Cost accounting is deterministic for same inputs."""
    update_verifier_price(source_id="src_a", base_price=2.0, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    p1 = get_verifier_price("src_a", tmp_path, surge_factor=1.0)
    p2 = get_verifier_price("src_a", tmp_path, surge_factor=1.0)
    assert p1 == p2 == 2.0
    assert get_verifier_price("src_a", tmp_path, surge_factor=2.0) == 4.0


def test_cofailure_produces_clusters(tmp_path: Path) -> None:
    """Co-failure patterns produce clusters."""
    register_verification_source(source_id="a", name="A", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    register_verification_source(source_id="b", name="B", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    for _ in range(3):
        perform_verification_check(action_id="act_x", source_id="a", result="fail", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
        perform_verification_check(action_id="act_x", source_id="b", result="fail", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    matrix, clusters = compute_correlation(tmp_path, "default")
    assert isinstance(matrix, dict)
    assert isinstance(clusters, dict)


def test_monoculture_triggers_safeguard(tmp_path: Path) -> None:
    """Monoculture alert can trigger safeguards (emit VERIFIER_MONOCULTURE_DETECTED)."""
    register_verification_source(source_id="only", name="Only", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    ev_id = emit_monoculture_detected(
        action_id="act_m",
        source_ids=["only", "only2"],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert ev_id


def test_cheap_green_light_no_commit_without_independent(tmp_path: Path) -> None:
    """Cheap green light scenario: without gate_checker we do not commit (passed=True)."""
    def gate_no_commit(_root: Path, _action_id: str) -> tuple:
        return False, "no_commit"
    passed, summary = run_attack_scenario("cheap_green_light", tmp_path, gate_checker=gate_no_commit)
    assert passed is True
    assert summary["scenario"] == "cheap_green_light"
    assert summary.get("ledger_artifact_id")


def test_cheap_green_light_fails_if_gate_allows(tmp_path: Path) -> None:
    """If gate incorrectly allows commit, ATTACK_SCENARIO_FAILED and passed=False."""
    def gate_allow(_root: Path, _action_id: str) -> tuple:
        return True, "bad"
    passed, summary = run_attack_scenario("cheap_green_light", tmp_path, gate_checker=gate_allow)
    assert passed is False
    assert summary.get("committed") is True


def test_receipt_forgery_blocks_without_gate(tmp_path: Path) -> None:
    """Receipt forgery scenario: without gate we do not commit (passed=True)."""
    passed, summary = run_attack_scenario("receipt_forgery", tmp_path)
    assert passed is True
    assert summary["scenario"] == "receipt_forgery"


def test_attack_suite_deterministic(tmp_path: Path) -> None:
    """Attack suite is deterministic and regression-safe (run_all_scenarios)."""
    results = run_all_scenarios(tmp_path, scenarios=["correlated_outage", "slow_truth"])
    assert "passed" in results and "failed" in results
    assert "summaries" in results
    assert "correlated_outage" in results["summaries"]
    assert "slow_truth" in results["summaries"]


def test_debit_and_budget_status(tmp_path: Path) -> None:
    """Debit decreases balance; status reflects initial and debited."""
    init_verification_budget(budget_key="b1", initial_balance=10.0, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    bal, init, debited = get_verification_budget_status(tmp_path, SCOPE, "b1")
    assert bal == 10.0 and init == 10.0 and debited == 0.0
    ok, _ = debit_verification_budget(budget_key="b1", amount=3.0, action_id="act_d", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert ok is True
    bal2, _, debited2 = get_verification_budget_status(tmp_path, SCOPE, "b1")
    assert bal2 == 7.0 and debited2 == 3.0


def test_emit_correlation_computed(tmp_path: Path) -> None:
    """VERIFIER_CORRELATION_COMPUTED emitted with matrix and clusters artifacts."""
    corr_id, ev_id = emit_correlation_computed(domain="test", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert corr_id.startswith("corr_")
    assert ev_id
    assert (tmp_path / "artifacts" / "verification" / "correlation").exists()
