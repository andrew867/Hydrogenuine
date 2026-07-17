import sys
from pathlib import Path

_workspace = Path(__file__).resolve().parents[2]
if str(_workspace) not in sys.path:
    sys.path.insert(0, str(_workspace))


def test_sealed_receipt_and_governance_flow(monkeypatch, tmp_path):
    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))

    from hg_core.receipts import create_sealed_receipt, verify_receipt, list_receipts
    from hg_core.policy_registry import create_policy_version, run_policy_simulation, activate_policy_version
    from hg_core.constitutional_memory import upsert_constitutional_root, add_checkpoint, add_drift_event, get_constitutional_root
    from hg_core.gate import create_benchmark_set, record_benchmark_run, evaluate_benchmark_run, create_release_verdict, enforce_release_gate

    receipt = create_sealed_receipt(
        tenant_id="default",
        receipt_kind="approval",
        subject_kind="approval",
        subject_id="ap-1",
        payload={"decision": "approve", "summary": "Looks good"},
    )
    verified = verify_receipt(receipt["receipt_id"])
    assert verified["verification_status"] == "verified"
    assert len(list_receipts()) >= 1

    policy = create_policy_version(
        policy_key="approval_policy",
        title="Approval Policy",
        category="approval",
        description="Base approval policy",
        content={"required_flags": ["human_review"]},
        rationale="Need a simple test policy",
        change_summary="Initial draft",
    )
    simulation = run_policy_simulation(
        version_id=policy["version_id"],
        scenario_label="operator-approval",
        inputs={"human_review": True},
    )
    assert simulation["result"]["pass"] is True
    activation = activate_policy_version(policy["version_id"])
    assert activation["version_id"] == policy["version_id"]

    root = upsert_constitutional_root(
        root_id=None,
        workflow_family="social",
        title="Social posture",
        root_goal="Post with judgment",
        material_constraints=["Do not spam", "Respect platform rules"],
        approved_subgoals=["Build relationships"],
        policy_version_id=policy["version_id"],
    )
    checkpoint = add_checkpoint(
        root_id=root["root_id"],
        summary="On track",
        state={"posture": "stable"},
        alignment_score=0.82,
    )
    drift = add_drift_event(
        root_id=root["root_id"],
        severity="watch",
        summary="Tone drift",
        details={"issue": "too editorial"},
    )
    root_detail = get_constitutional_root(root["root_id"])
    assert checkpoint["checkpoint_id"]
    assert drift["drift_event_id"]
    assert root_detail["root"]["drift_severity"] == "watch"

    benchmark_set = create_benchmark_set(
        workflow_family="social",
        title="Social gate",
        description="Basic social benchmark",
        weights={"p_h": 0.3, "p_ai": 0.2, "p_h_odei": 0.5},
    )
    benchmark_run = record_benchmark_run(
        benchmark_set_id=benchmark_set["benchmark_set_id"],
        workflow_family="social",
        candidate_label="v1",
        observations={"p_h": 0.71, "p_ai": 0.55, "p_h_odei": 0.81},
    )
    evaluation = evaluate_benchmark_run(benchmark_run_id=benchmark_run["benchmark_run_id"], policy_version_id=policy["version_id"])
    assert evaluation["verdict"] in {"eligible", "watch"}

    create_release_verdict(
        workflow_family="social",
        target_kind="workflow",
        target_id="social",
        evaluation_id=evaluation["evaluation_id"],
        verdict="eligible",
        reason="Good enough",
    )
    allowed = enforce_release_gate(workflow_family="social")
    assert allowed["ok"] is True


def test_mimicry_controls_policy_helpers(monkeypatch, tmp_path):
    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))

    from hg_core.drift.features import extract_mimicry_features
    from hg_core.drift.safeguards import apply_mimicry_safeguard
    from hg_core.governance.contracts import build_mimicry_policy_summary
    from hg_core.governance.independence import build_voice_belief_separation_summary
    from hg_core.policy_registry import activate_policy_version, create_policy_version

    policy = create_policy_version(
        policy_key="mimicry_controls",
        title="Mimicry Controls",
        category="governance",
        description="Caps on style and emotional mimicry",
        content={
            "max_mimicry_depth": 0.8,
            "max_emotional_intensity": 0.8,
            "require_grounding": True,
            "separate_voice_from_belief": True,
            "inject_contradiction_checks": True,
        },
        rationale="Keep style grounded",
        change_summary="Initial mimicry policy",
    )
    activate_policy_version(policy["version_id"])

    summary = build_mimicry_policy_summary()
    assert summary["status"] == "ready"
    assert summary["voice_belief_separated"] is True
    assert summary["grounding_required"] is True

    features = extract_mimicry_features(
        {
            "voice_directives": ["natural voice", "grounded"],
            "belief_claim": "durable belief",
            "grounding_signals": ["source"],
            "contradiction_signals": ["check one"],
            "emotional_register": {"steady": True},
            "voice_belief_separated": True,
            "mimicry_depth": 0.62,
            "emotional_intensity": 0.52,
        },
        thread_id="thread-1",
        work_item_id="wi-1",
        actor_id="operator",
    )
    safeguard = apply_mimicry_safeguard(features=features, policy=summary["limits"])
    voice_summary = build_voice_belief_separation_summary(
        mimicry_policy_summary=summary,
        self_model_summary={"status": "healthy", "dominant_uncertainty": "grounded"},
    )

    assert features["voice_belief_separated"] is True
    assert safeguard["status"] == "healthy"
    assert safeguard["voice_belief_separated"] is True
    assert voice_summary["status"] == "healthy"
    assert voice_summary["voice_belief_separated"] is True

    guarded = apply_mimicry_safeguard(
        features={
            "thread_id": "thread-2",
            "voice_strength": 0.95,
            "emotional_intensity": 0.9,
            "grounded": False,
            "voice_belief_separated": False,
            "contradiction_checks": False,
        },
        policy=summary["limits"],
    )
    assert guarded["status"] == "blocked"
    assert "grounding_required" in guarded["safeguards"]
    assert "voice_belief_coupled" in guarded["safeguards"]
