"""F12A simulated social/economic work capsule tests.

Capsule is simulated only. Simulated work is not customer work.
Social output is not a social post. Review pass is not customer acceptance.
Value estimate is not payment permission.
"""

from __future__ import annotations

import pytest

from hg_runtime.simulated_work_capsule.artifact_writer import (
    build_capsule_artifacts, secret_scan,
)
from hg_runtime.simulated_work_capsule.capsule import (
    validate_capsule_artifact,
    validate_capsule_task,
    validate_review_packet,
    validate_state_memory_ref,
    validate_work_plan,
)
from hg_runtime.simulated_work_capsule.fixtures import (
    fixture_authority_mutation_attempt,
    fixture_capsule_artifact,
    fixture_capsule_review_packet,
    fixture_capsule_state_memory_ref,
    fixture_capsule_task,
    fixture_capsule_work_plan,
    fixture_defective_work,
    fixture_economic_value_estimate,
    fixture_hg_local_attempt,
    fixture_invoice_attempt,
    fixture_live_customer_contact_attempt,
    fixture_live_effect_attempt,
    fixture_live_posting_attempt,
    fixture_live_provider_attempt,
    fixture_message_send_attempt,
    fixture_patch_attempt,
    fixture_payment_attempt,
    fixture_phase19_laundering_attempt,
    fixture_phase24_laundering_attempt,
    fixture_secret_material_artifact,
    fixture_soak_defect_workload,
    fixture_soak_economic_workload,
    fixture_soak_maintenance_workload,
    fixture_soak_repair_recommendation_workload,
    fixture_soak_review_workload,
    fixture_social_draft,
    fixture_tool_auth_attempt,
)
from hg_runtime.simulated_work_capsule.gate import validate_f12a_gate
from hg_runtime.simulated_work_capsule.replay import replay_capsule_artifacts
from hg_runtime.simulated_work_capsule.schemas import (
    PHASE19_VERDICT, PHASE24_STATUS, PROVIDER_MODE, VERDICT_GREEN,
    SimulatedWorkCapsuleError, reject_capsule_overreach,
)


# --- schema invariants ---

def test_f12a_verdict_green():
    assert "GREEN" in VERDICT_GREEN and "F12A" in VERDICT_GREEN

def test_f12a_provider_mode():
    assert PROVIDER_MODE == "FIXTURE_ONLY_PROVIDER_DISABLED"

def test_f12a_phase19_yellow():
    assert "YELLOW" in PHASE19_VERDICT

def test_f12a_phase24_infra():
    assert PHASE24_STATUS == "infrastructure_only"


# --- capsule task intake ---

def test_f12a_creates_capsule_task_intake():
    t = fixture_capsule_task()
    assert t["task_id"]
    assert t["is_simulated"] is True
    assert t["real_customer"] is False
    assert validate_capsule_task(t) == []

def test_f12a_creates_capsule_work_plan():
    p = fixture_capsule_work_plan()
    assert p["plan_id"]
    assert p["f02_state_ref"]
    assert p["p63_sim_ref"]
    assert validate_work_plan(p) == []

def test_f12a_creates_capsule_artifact():
    a = fixture_capsule_artifact()
    assert a["artifact_id"]
    assert a["is_simulated"] is True
    assert a["live_submission_target"] is None
    assert a["social_post_target"] is None
    assert a["payment_target"] is None
    assert validate_capsule_artifact(a) == []

def test_f12a_creates_capsule_review_packet():
    r = fixture_capsule_review_packet()
    assert r["review_id"]
    assert r["operator_review_required"] is True
    assert r["is_customer_acceptance"] is False
    assert r["is_payment_permission"] is False
    assert validate_review_packet(r) == []


# --- upstream linkage ---

def test_f12a_links_to_p63_simulated_task():
    t = fixture_capsule_task()
    assert t["p63_task_ref"] == "sim-task-001"

def test_f12a_links_to_p64_review_receipt():
    r = fixture_capsule_review_packet()
    assert r["p64_review_ref"] == "rev-receipt-001"

def test_f12a_links_to_p65_consolidation_receipt():
    r = fixture_capsule_review_packet()
    assert r["p65_consolidation_ref"] == "consol-receipt-001"

def test_f12a_links_to_f02_state_snapshot():
    ref = fixture_capsule_state_memory_ref()
    assert ref["f02_snapshot_ref"] == "snap-001"
    assert ref["state_estimate_is_truth"] is False

def test_f12a_links_to_f02_repair_recommendation():
    ref = fixture_capsule_state_memory_ref()
    assert ref["f02_recommendation_ref"] == "rec-001"
    assert ref["recommendation_is_permission"] is False


# --- soak workloads ---

def test_f12a_generates_soak_workload():
    wl = fixture_soak_maintenance_workload()
    assert len(wl) == 3
    assert all(t["is_simulated"] for t in wl)

def test_f12a_generates_defect_workload():
    wl = fixture_soak_defect_workload()
    assert len(wl) == 3
    assert all(t["domain"] == "DEFECT_TRIAGE" for t in wl)

def test_f12a_generates_economic_workload():
    wl = fixture_soak_economic_workload()
    assert len(wl) == 3

def test_f12a_generates_review_workload():
    wl = fixture_soak_review_workload()
    assert len(wl) == 3

def test_f12a_generates_repair_recommendations():
    recs = fixture_soak_repair_recommendation_workload()
    assert len(recs) == 3
    assert all(r["is_permission"] is False for r in recs)
    assert all(r["operator_review_required"] for r in recs)


# --- simulated-only boundary ---

def test_f12a_capsule_is_simulated_only():
    t = fixture_capsule_task()
    assert t["is_simulated"] is True

def test_f12a_simulated_work_is_not_customer_work():
    t = fixture_capsule_task()
    assert t["real_customer"] is False
    assert t["customer_contact"] is False

def test_f12a_social_output_is_not_social_post():
    d = fixture_social_draft()
    assert d["social_post_target"] is None
    assert d["is_simulated"] is True

def test_f12a_review_pass_is_not_customer_acceptance():
    r = fixture_capsule_review_packet()
    assert r["is_customer_acceptance"] is False

def test_f12a_value_estimate_is_not_payment_permission():
    r = fixture_economic_value_estimate()
    assert r["is_payment_permission"] is False
    assert r["value_estimate"]["is_payment_permission"] is False

def test_f12a_repair_recommendation_is_not_permission():
    ref = fixture_capsule_state_memory_ref()
    assert ref["recommendation_is_permission"] is False

def test_f12a_defective_work_links_repair():
    d = fixture_defective_work()
    assert len(d["defect_summary"]) > 0
    assert d["f02_repair_ref"] == "rec-001"


# --- rejection tests ---

def test_f12a_refuses_customer_contact():
    with pytest.raises(SimulatedWorkCapsuleError):
        reject_capsule_overreach(fixture_live_customer_contact_attempt())

def test_f12a_refuses_live_posting():
    with pytest.raises(SimulatedWorkCapsuleError):
        reject_capsule_overreach(fixture_live_posting_attempt())

def test_f12a_refuses_message_send():
    with pytest.raises(SimulatedWorkCapsuleError):
        reject_capsule_overreach(fixture_message_send_attempt())

def test_f12a_refuses_payment():
    with pytest.raises(SimulatedWorkCapsuleError):
        reject_capsule_overreach(fixture_payment_attempt())

def test_f12a_refuses_invoice_creation():
    with pytest.raises(SimulatedWorkCapsuleError):
        reject_capsule_overreach(fixture_invoice_attempt())

def test_f12a_refuses_tool_authorization():
    with pytest.raises(SimulatedWorkCapsuleError):
        reject_capsule_overreach(fixture_tool_auth_attempt())

def test_f12a_refuses_live_provider_enablement():
    with pytest.raises(SimulatedWorkCapsuleError):
        reject_capsule_overreach(fixture_live_provider_attempt())

def test_f12a_refuses_live_effect():
    with pytest.raises(SimulatedWorkCapsuleError):
        reject_capsule_overreach(fixture_live_effect_attempt())

def test_f12a_refuses_hg_local_touch():
    with pytest.raises(SimulatedWorkCapsuleError):
        reject_capsule_overreach(fixture_hg_local_attempt())

def test_f12a_refuses_patch_application():
    with pytest.raises(SimulatedWorkCapsuleError):
        reject_capsule_overreach(fixture_patch_attempt())

def test_f12a_refuses_authority_mutation():
    with pytest.raises(SimulatedWorkCapsuleError):
        reject_capsule_overreach(fixture_authority_mutation_attempt())

def test_f12a_refuses_phase19_laundering():
    with pytest.raises(SimulatedWorkCapsuleError):
        reject_capsule_overreach(fixture_phase19_laundering_attempt())

def test_f12a_refuses_phase24_laundering():
    with pytest.raises(SimulatedWorkCapsuleError):
        reject_capsule_overreach(fixture_phase24_laundering_attempt())

def test_f12a_reject_clean():
    reject_capsule_overreach({"simulated": True, "advisory": True})

def test_f12a_fake_green_rejected():
    with pytest.raises(SimulatedWorkCapsuleError):
        reject_capsule_overreach({"claims_agi": True})


# --- replay tests ---

def test_f12a_replay_preserves_hashes():
    a = replay_capsule_artifacts()
    b = replay_capsule_artifacts()
    assert a["artifact_hash"] == b["artifact_hash"]

def test_f12a_replay_rejects_mutation():
    arts = replay_capsule_artifacts()
    orig = arts["artifact_hash"]
    arts["task_count"] = 999
    from hg_runtime.simulated_work_capsule.artifact_writer import _stable_hash
    assert _stable_hash(arts) != orig

def test_f12a_no_secret_material_in_artifacts():
    task = fixture_capsule_task()
    plan = fixture_capsule_work_plan()
    art = fixture_capsule_artifact()
    rev = fixture_capsule_review_packet()
    ref = fixture_capsule_state_memory_ref()
    arts = build_capsule_artifacts([task], [plan], [art], [rev], [ref])
    assert secret_scan(arts) == []

def test_f12a_secret_scan_detects_secret():
    art = fixture_secret_material_artifact()
    arts = build_capsule_artifacts([], [], [art], [], [])
    hits = secret_scan(arts)
    assert len(hits) > 0

def test_f12a_build_artifacts():
    task = fixture_capsule_task()
    plan = fixture_capsule_work_plan()
    art = fixture_capsule_artifact()
    rev = fixture_capsule_review_packet()
    ref = fixture_capsule_state_memory_ref()
    soak = fixture_soak_maintenance_workload()
    arts = build_capsule_artifacts([task], [plan], [art], [rev], [ref], soak)
    assert arts["all_tasks_valid"] is True
    assert arts["all_plans_valid"] is True
    assert arts["all_artifacts_valid"] is True
    assert arts["all_reviews_valid"] is True
    assert arts["capsule_simulated_only"] is True
    assert arts["no_customer_contact"] is True
    assert arts["no_payment_permission"] is True
    assert "artifact_hash" in arts


# --- gate tests ---

def _gate(**overrides):
    data = {
        "verdict": VERDICT_GREEN,
        "capsule_task_exists": True, "work_plan_exists": True,
        "artifact_exists": True, "review_packet_exists": True,
        "soak_workload_exists": True, "f02_memory_ref_exists": True,
        "capsule_simulated_only": True,
        "no_customer_contact": True, "no_live_posting": True,
        "no_message_send": True, "no_payment": True,
        "no_money_movement": True, "no_invoice": True,
        "no_tool_authorization": True, "no_patch_application": True,
        "no_authority_mutation": True, "no_live_provider": True,
        "no_live_effects": True, "no_hg_local": True,
        "phase19_yellow_preserved": True,
        "phase24_infrastructure_only_preserved": True,
        "replay_preserves_hashes": True,
        "proof_bundle_valid": True, "report_present": True,
        "fake_green_rejected": True, "secret_scan_clean": True,
        "p63_ref_exists": True, "p64_ref_exists": True,
        "p65_ref_exists": True,
        "review_not_customer_acceptance": True,
        "value_not_payment_permission": True,
        # forbidden flags
        "real_customer": False, "customer_contact": False,
        "social_post_published": False, "message_sent": False,
        "real_payment": False, "money_movement": False,
        "invoice_created": False, "tool_authorized": False,
        "tool_executed": False, "patch_applied": False,
        "authority_mutated": False, "live_effect": False,
        "live_provider_enabled": False, "live_submission": False,
        "hg_local_touched": False, "deployment_claim": False,
        "claims_agi": False, "phase19_green_claimed": False,
        "phase24_full_overnight_green_claimed": False,
        "web_browse_performed": False, "external_provider_call": False,
    }
    data.update(overrides)
    return data

def test_f12a_gate_green():
    assert validate_f12a_gate(_gate())["ok"] is True

def test_f12a_gate_requires_capsule_task():
    assert validate_f12a_gate(_gate(capsule_task_exists=False))["ok"] is False

def test_f12a_gate_requires_artifact():
    assert validate_f12a_gate(_gate(artifact_exists=False))["ok"] is False

def test_f12a_gate_requires_review_packet():
    assert validate_f12a_gate(_gate(review_packet_exists=False))["ok"] is False

def test_f12a_gate_requires_f02_reference():
    assert validate_f12a_gate(_gate(f02_memory_ref_exists=False))["ok"] is False

def test_f12a_gate_refuses_live_work():
    assert validate_f12a_gate(_gate(live_submission=True))["ok"] is False

def test_f12a_gate_refuses_tool_authorization():
    assert validate_f12a_gate(_gate(tool_authorized=True))["ok"] is False

def test_f12a_gate_refuses_payment_permission():
    assert validate_f12a_gate(_gate(real_payment=True))["ok"] is False

def test_f12a_gate_refuses_live_effects():
    assert validate_f12a_gate(_gate(live_effect=True))["ok"] is False

def test_f12a_gate_refuses_customer_contact():
    assert validate_f12a_gate(_gate(customer_contact=True))["ok"] is False

def test_f12a_gate_refuses_social_posting():
    assert validate_f12a_gate(_gate(social_post_published=True))["ok"] is False

def test_f12a_gate_refuses_money_movement():
    assert validate_f12a_gate(_gate(money_movement=True))["ok"] is False
