"""Receipt-map generation (workflow_receipt_map_v1).

Classifies a validated intake against the Hydrogenuine authority stages
(propose -> quality/source gate -> quarantine -> operator review -> permit ->
sandbox/stub effect) and emits: authority boundary map, decision points, receipt plan,
refusal plan, proof-bundle plan, runner projection, publicability, claim boundary.

Pure analysis: no external calls, no workflow effects, ever.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from hg_runtime.demos.governed_research_soak.orchestrator import _receipt_hash
from hg_runtime.demos.grs_runner.scenario_schema import validate_scenario
from hg_runtime.workflow_receipt_mapper.schema import load_intake, redact_intake


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build_authority_boundary_map(intake: dict) -> dict:
    effects = intake["external_effects"]
    return {
        "proposal_boundaries": [
            {"stage": "model_proposes", "rule": "model output is a proposal, never an action",
             "inputs": intake["input_sources"], "outputs": intake["model_outputs"]},
        ],
        "permission_boundaries": [
            {"action": a, "rule": "requires an explicit permit before any effect; "
                                   "expired or missing permit means the action does not execute"}
            for a in intake["proposed_actions"]
        ],
        "execution_boundaries": [
            {"effect": e, "status": "sandbox/stub until integration ships",
             "rule": "terminal effects remain sandbox/stubbed; no unscoped external effects"}
            for e in (effects or ["none declared"])
        ],
        "review_boundaries": [
            {"point": p, "rule": "operator review required; local signed demo operator "
                                 "is not production auth"}
            for p in intake["human_review_points"]
        ],
        "refusal_boundaries": [
            {"condition": c, "rule": "structural refusal with reason code and receipt"}
            for c in intake["must_refuse_conditions"]
        ],
    }


def build_decision_points(intake: dict) -> list[dict]:
    points = [
        {"id": "dp-01", "stage": "model_proposes",
         "description": f"agent ({intake['agent_role']}) produces: "
                        + "; ".join(intake["model_outputs"])},
        {"id": "dp-02", "stage": "runtime_checks",
         "description": "schema/authority checks; hallucinated permits are structurally inert"},
        {"id": "dp-03", "stage": "quality_source_gate",
         "description": "output quality classified; unsupported assertions routed to "
                        "source grounding or hold"},
        {"id": "dp-04", "stage": "operator_review",
         "description": "review points: " + "; ".join(intake["human_review_points"])},
        {"id": "dp-05", "stage": "permit_required",
         "description": "actions needing permits: " + "; ".join(intake["proposed_actions"])},
        {"id": "dp-06", "stage": "sandbox_effect",
         "description": "any executed effect runs dry-run/sandbox in demos"},
    ]
    if intake["external_effects"]:
        points.append({"id": "dp-07", "stage": "external_effect_blocked",
                       "description": "external effects blocked pending integration: "
                                      + "; ".join(intake["external_effects"])})
    return points


def build_receipt_plan(intake: dict) -> list[dict]:
    base = [
        ("session_receipt", "session", "workflow run starts", ["workflow_id", "operator_mode"], "runner"),
        ("model_proposal_receipt", "proposal", "model produces output",
         ["model", "content_hash", "data_tier"], "model_provider"),
        ("quality_gate_receipt", "quality", "proposal classified",
         ["quality_class", "issues", "artifact_hash"], "output_quality"),
        ("operator_review_packet", "review", "candidates ready for review",
         ["claims", "neutral_flags"], "operator_review"),
        ("operator_decision_receipt", "decision", "operator approves/denies",
         ["claim_id", "decision", "signature"], "operator_review"),
        ("promotion_receipt", "promotion", "approved candidates promote",
         ["promoted_claims", "denied_claims_not_promoted"], "promotion"),
    ]
    plan = [{
        "receipt_id": rid, "receipt_type": rtype, "trigger": trig, "fields": fields,
        "owner_module": owner, "required_before_promotion": rid != "promotion_receipt",
        "evidence_link": f"{rid}.json",
    } for rid, rtype, trig, fields, owner in base]
    for extra in intake["required_receipts"]:
        rid = extra.lower().replace(" ", "_")
        if not any(p["receipt_id"] == rid for p in plan):
            plan.append({"receipt_id": rid, "receipt_type": "workflow_specific",
                         "trigger": extra, "fields": ["workflow_id", "payload_hash"],
                         "owner_module": "workflow_adapter (roadmap)",
                         "required_before_promotion": True,
                         "evidence_link": f"{rid}.json"})
    return plan


def build_refusal_plan(intake: dict) -> list[dict]:
    plan = [{
        "refusal_condition": c,
        "refusal_receipt": "refusal_receipt.json (unified reason code)",
        "operator_message": f"Refused: {c}. The runtime holds; no effect executed.",
        "next_allowed_action": "operator may review the refusal and adjust the request "
                               "or approve an alternative path",
    } for c in intake["must_refuse_conditions"]]
    plan += [{
        "refusal_condition": f"HOLD: {c}",
        "refusal_receipt": "hold_receipt.json",
        "operator_message": f"Held for review: {c}.",
        "next_allowed_action": "operator review decides promote/deny",
    } for c in intake["must_hold_conditions"]]
    return plan


def build_proof_bundle_plan(intake: dict) -> dict:
    return {
        "manifest": "manifest.json (file hashes, sealed last)",
        "gate_result": "gate_result.json (JSON verdict field authoritative)",
        "source_receipts": "source_capture_receipts.jsonl (source is receipt, not truth)",
        "operator_decisions": "operator_decision_receipts.jsonl (signed)",
        "promotion_receipts": "promotion_receipt.json (denied never promoted)",
        "final_artifact": intake["proof_bundle_expectations"],
        "checksums": "checksums.sha256 (raw-byte sha256)",
    }


def build_runner_projection(intake: dict) -> tuple[dict, dict | None]:
    """Project onto the reusable GRS runner. Draft only — never claimed as run."""
    representable = intake["integration_status"] in ("native", "wrapper_roadmap")
    scenario = None
    if representable:
        scenario = {
            "scenario_id": f"{intake['workflow_id']}_draft",
            "title": f"[DRAFT — not run] {intake['title']}",
            "description": "DRAFT scenario projected from a workflow intake; fixture "
                           "mode; must be reviewed and run before any status claim.",
            "question": intake["operator_goal"],
            "mode": "fixture",
            "model": {"endpoint": "", "model_name": "fixture/grs-demo-model",
                      "require_live_model": False, "cloud_providers_allowed": False},
            "sources": {"mode": "fixture", "allowlist": [], "minimum_source_count": 0},
            "quality_gate": {"require_source_support": True,
                             "boilerplate_policy": "hold", "minimum_evidence_count": 1},
            "quarantine": {"enabled": True, "promotion_requires_review": True},
            "operator_review": {"mode": "fixture_simulated_operator",
                                "require_approve": True, "require_deny": True,
                                "production_operator_auth": False},
            "outputs": {"final_document_template": "default",
                        "proof_bundle_root": "docs/proofs/grs_demo_runner",
                        "website_handoff_enabled": False,
                        "video_capture_enabled": False},
            "claim_boundaries": {"no_model_correctness": True,
                                 "no_production_auth": True,
                                 "no_customer_deployment": True,
                                 "no_certification": True,
                                 "source_is_not_truth": True},
        }
        # Drafts must be runnable-shaped: validate against the real scenario schema.
        assert validate_scenario(scenario) == [], "draft scenario must validate"
    projection = {
        "can_run_through_grs_runner": representable,
        "status": "DRAFT_ONLY_NOT_RUN" if representable else "NOT_PROJECTABLE",
        "scenario_config_draft_path": "scenario_config_draft.json" if representable else None,
        "live_now": [],
        "fixture_now": intake["model_outputs"] if representable else [],
        "roadmap": intake["external_effects"] or [],
        "note": "a draft is not an implementation; a workflow counts as demoed only "
                "after a runner scenario and gate actually run",
    }
    return projection, scenario


def build_publicability(intake: dict) -> dict:
    if intake["data_sensitivity"] != "synthetic":
        status = "needs_redaction"
    elif intake["integration_status"] == "not_supported":
        status = "not_demoable"
    else:
        status = "internal_only"  # a map alone is never public_ready; a run demo may be
    return {"status": status,
            "rule": "a receipt map alone is internal_only at best; public_ready requires "
                    "a gate-GREEN run demo and a claim-firewall pass"}


def map_workflow(intake_raw: dict, out: Path) -> dict:
    intake = load_intake(intake_raw)
    out.mkdir(parents=True, exist_ok=True)
    wid = intake["workflow_id"]

    redacted = redact_intake(intake)
    (out / "intake_redacted.json").write_text(json.dumps(redacted, indent=2), encoding="utf-8")

    boundary = build_authority_boundary_map(intake)
    decision_points = build_decision_points(intake)
    receipt_plan = build_receipt_plan(intake)
    refusal_plan = build_refusal_plan(intake)
    bundle_plan = build_proof_bundle_plan(intake)
    projection, scenario_draft = build_runner_projection(intake)
    publicability = build_publicability(intake)

    receipt_map = {
        "schema_version": "workflow_receipt_map_v1",
        "map_id": f"wrm-{uuid.uuid4().hex[:12]}",
        "workflow_summary": {
            "workflow_id": wid, "title": intake["title"], "domain": intake["domain"],
            "operator_goal": intake["operator_goal"], "agent_role": intake["agent_role"],
            "risk_level": intake["risk_level"],
            "integration_status": intake["integration_status"],
        },
        "authority_boundary_map": boundary,
        "decision_points": decision_points,
        "receipt_plan": receipt_plan,
        "refusal_plan": refusal_plan,
        "proof_bundle_plan": bundle_plan,
        "runner_projection": projection,
        "publicability": publicability,
        "claim_boundary": {
            "shows": ["where model output enters", "where action is proposed",
                      "which authority boundary applies", "what is held/refused/reviewed",
                      "what receipts should be written",
                      "what a proof bundle would need to contain"],
            "does_not_show": ["a deployment", "an audit or certification",
                              "model correctness", "production operator auth",
                              "that the workflow is implemented (unless a runner "
                              "scenario and gate actually ran)"],
        },
        "generated_at": _now(),
    }
    receipt_map["hash"] = _receipt_hash(receipt_map)

    (out / "receipt_map.json").write_text(json.dumps(receipt_map, indent=2), encoding="utf-8")
    (out / "authority_boundary_map.json").write_text(json.dumps(boundary, indent=2), encoding="utf-8")
    (out / "receipt_plan.json").write_text(json.dumps(receipt_plan, indent=2), encoding="utf-8")
    (out / "refusal_plan.json").write_text(json.dumps(refusal_plan, indent=2), encoding="utf-8")
    (out / "proof_bundle_plan.json").write_text(json.dumps(bundle_plan, indent=2), encoding="utf-8")
    (out / "runner_projection.json").write_text(json.dumps(projection, indent=2), encoding="utf-8")
    if scenario_draft:
        (out / "scenario_config_draft.json").write_text(
            json.dumps(scenario_draft, indent=2), encoding="utf-8")

    (out / "summary_report.md").write_text(_summary_md(intake, receipt_map), encoding="utf-8")
    (out / "claim_boundary_report.md").write_text(_claim_boundary_md(intake), encoding="utf-8")

    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "checksums.sha256")
    (out / "checksums.sha256").write_text(
        "\n".join(f"{_sha256_file(p)}  {p.relative_to(out).as_posix()}" for p in files) + "\n",
        encoding="utf-8")
    return receipt_map


def _summary_md(intake: dict, m: dict) -> str:
    lines = [
        f"# Receipt Map — {intake['title']}",
        "",
        "**This is a governance artifact.** It maps the path; it does not deploy,",
        "audit, or certify anything, and it does not prove model correctness.",
        f"Data: synthetic example. Workflow id: `{intake['workflow_id']}`.",
        "",
        "## The path",
        "",
        "1. **This is what the agent proposes:** " + "; ".join(intake["model_outputs"]),
        "2. **This is where authority is needed:** " + "; ".join(intake["proposed_actions"]),
        "3. **This is where the runtime holds or refuses:** "
        + "; ".join(intake["must_refuse_conditions"] + intake["must_hold_conditions"]),
        "4. **This is what the operator reviews:** " + "; ".join(intake["human_review_points"]),
        "5. **This is what the system records:** "
        + ", ".join(p["receipt_id"] for p in m["receipt_plan"]),
        "6. **This is what a proof bundle would need to contain:** manifest, gate result,"
        " source receipts, signed operator decisions, promotion receipt, final artifact,"
        " checksums.",
        "",
        "## Runner projection",
        "",
        f"- {m['runner_projection']['status']}"
        + (" — draft scenario emitted (fixture; must be reviewed and run before any "
           "status claim)" if m['runner_projection']['can_run_through_grs_runner'] else ""),
        f"- Roadmap (blocked external effects): "
        + ("; ".join(m['runner_projection']['roadmap']) or "none declared"),
        "",
        f"## Publicability: {m['publicability']['status']}",
        "",
        m["publicability"]["rule"] + ".",
    ]
    return "\n".join(lines) + "\n"


def _claim_boundary_md(intake: dict) -> str:
    return f"""# Claim Boundary — receipt map for {intake['workflow_id']}

**What this map shows:** the proposal path, authority boundaries, review points,
refusal/hold conditions, the receipts the workflow should write, and what a proof
bundle would need to contain.

**What it does not show:** a deployment; an audit or certification; model correctness;
production operator auth; that the workflow is implemented. A mapped workflow counts as
demoed only after a runner scenario and gate actually run. Source is receipt, not
truth. Synthetic example data only; no external effects were performed.
"""
