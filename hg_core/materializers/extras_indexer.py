"""
Ch7 extras indexer: incidents, policy events, audit events from ledger.
Output: incidents.jsonl, policy_events.jsonl, audit_events.jsonl for search and API.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from hg_core.ledger.ledger_writer import iter_events_by_scope
from ._checkpoint import get_materialized_root, save_checkpoint


def run(workspace_root: Path, rebuild: bool = False) -> None:
    workspace_root = Path(workspace_root)
    root = get_materialized_root(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    incidents: List[Dict[str, Any]] = []
    policy_events: List[Dict[str, Any]] = []
    audit_events: List[Dict[str, Any]] = []
    checkpoint: Dict[str, str] = {}

    for scope_type, scope_id, ev in iter_events_by_scope(workspace_root):
        scope_key = f"{scope_type}/{scope_id}"
        checkpoint[scope_key] = ev.get("event_id", "")
        action = ev.get("action")
        payload = ev.get("payload") or {}
        ts = ev.get("ts", "")
        actor = ev.get("actor") or {}
        base = {"event_id": ev.get("event_id"), "ts": ts, "scope_type": scope_type, "scope_id": scope_id, "agent_id": actor.get("agent_id", "")}

        if action == "INCIDENT_CANDIDATE_CREATED":
            incidents.append({
                **base,
                "incident_id": payload.get("candidate_id"),
                "candidate_id": payload.get("candidate_id"),
                "source": payload.get("source", ""),
                "evidence_refs": payload.get("evidence_refs", []),
                "severity": payload.get("severity", "medium"),
                "summary": payload.get("summary"),
                "status": "candidate",
            })
        elif action == "INCIDENT_CONFIRMED":
            iid = payload.get("incident_id") or payload.get("candidate_id")
            incidents.append({
                **base,
                "incident_id": iid,
                "candidate_id": payload.get("candidate_id"),
                "owner_agent_id": payload.get("owner_agent_id"),
                "sla_due_ts": payload.get("sla_due_ts"),
                "status": "confirmed",
            })
        elif action == "INCIDENT_RESOLVED":
            incidents.append({
                **base,
                "incident_id": payload.get("incident_id"),
                "postmortem_ref": payload.get("postmortem_ref"),
                "resolution_summary": payload.get("resolution_summary"),
                "status": "resolved",
            })
        elif action == "INCIDENT_MITIGATED":
            incidents.append({
                **base,
                "incident_id": payload.get("incident_id"),
                "mitigation_summary": payload.get("mitigation_summary"),
                "status": "mitigated",
            })
        elif action == "INCIDENT_CLOSED":
            incidents.append({
                **base,
                "incident_id": payload.get("incident_id"),
                "status": "closed",
            })
        elif action == "CORRECTIVE_ACTION_TRACKED":
            incidents.append({
                **base,
                "incident_id": payload.get("incident_id"),
                "action_ref": payload.get("action_ref"),
                "summary": payload.get("summary"),
                "status": "corrective_action",
            })
        elif action == "POLICY_CHANGE_LINKED":
            incidents.append({
                **base,
                "incident_id": payload.get("incident_id"),
                "policy_ref": payload.get("policy_ref"),
                "status": "policy_linked",
            })
        elif action in ("POLICY_PUBLISHED", "POLICY_APPLIED", "POLICY_OVERRIDE_APPLIED"):
            policy_events.append({
                **base,
                "action": action,
                "policy_type": payload.get("policy_type"),
                "artifact_path": payload.get("artifact_path"),
                "policy_ref": payload.get("policy_ref"),
                "override_spec": payload.get("override_spec"),
                "expiry_ts": payload.get("expiry_ts"),
            })
        elif action in (
            "AUDIT_BUNDLE_EXPORTED", "SENSITIVE_REVEAL_REQUESTED", "DECISION_AUDIT_EXPORTED", "TEMPORAL_AUDIT_EXPORTED",
            "PRIVILEGED_ACCESS", "TOMBSTONE_RECORDED",
            "ENFORCEMENT_APPLIED", "AUTONOMY_RESTORED",
            "RETENTION_JOB_RAN", "ARTIFACT_TOMBSTONED", "DATA_REMOVAL_REQUESTED", "DATA_REMOVAL_EXECUTED",
            "ANCHOR_PUBLISHED", "ANCHOR_VERIFIED",
            "SANDBOX_CREATED", "SANDBOX_DESTROYED", "TOOL_DENIED_BY_POLICY", "TOOL_EXECUTED_IN_SANDBOX",
            "LOOP_STARTED", "LOOP_STOPPED", "LOOP_TICK", "WORK_ITEM_SELECTED", "PLAN_GENERATED", "PLAN_STEP_EXECUTED", "LOOP_BLOCKED", "LOOP_SUMMARY_PUBLISHED",
            "VALUE_JUDGMENT_RECORDED", "GOVERNANCE_CONTRACT_PUBLISHED", "APPROVAL_POLICY_APPLIED", "DELEGATION_CONTRACT_CREATED", "ESCALATION_ROUTE_TAKEN",
            "TUNING_SUGGESTION_PUBLISHED", "POLICY_ROLLOUT_STARTED", "POLICY_ROLLOUT_COMPLETED", "POLICY_ROLLOUT_ROLLED_BACK",
            "ATTESTATION_PUBLISHED", "CONTROL_CHECK_RAN", "AUDIT_EXPORT_REQUESTED", "AUDIT_EXPORT_COMPLETED",
            "DLP_SCAN_COMPLETED", "DATA_QUARANTINED", "DATA_RELEASED", "LEGAL_HOLD_APPLIED", "LEGAL_HOLD_RELEASED", "KEY_ROTATED",
            "PLUGIN_INSTALLED", "PLUGIN_ENABLED", "PLUGIN_DISABLED",
            "VERIFICATION_SOURCE_REGISTERED", "VERIFICATION_CHECK_PERFORMED", "VERIFICATION_ROBUSTNESS_COMPUTED", "VERIFICATION_INSUFFICIENT",
            "MATERIALIZER_VERSION_REGISTERED", "MATERIALIZER_RUN_RECORDED", "REPLAY_COMPAT_PROFILE_PUBLISHED",
            "IMPACT_EDGE_RECORDED", "BLAST_RADIUS_COMPUTED",
            "GAP_SCORE_COMPUTED", "GAP_ALERT_RAISED", "GAP_CONTROL_APPLIED",
            "COUNTERFACTUAL_BRANCH_RECORDED", "COUNTERFACTUAL_PREDICTION_MADE", "REGRET_COMPUTED", "COUNTERFACTUAL_LESSON_PUBLISHED",
            "APPROVAL_BATCH_CREATED", "APPROVAL_BATCH_APPROVED", "APPROVAL_QUEUE_RANKED", "APPROVAL_FATIGUE_LIMIT_REACHED",
            "AUDIT_SPOTCHECK_REQUESTED", "AUDIT_SPOTCHECK_COMPLETED",
            "POLICY_DIFF_RISK_REPORT",
            "CONTINUITY_CONTRACT_PUBLISHED", "CONTINUITY_CHECK_PERFORMED", "CONTINUITY_INVALIDATED", "REVALIDATION_REQUESTED",
            "SAFEGUARD_APPLIED", "SAFEGUARD_LIFTED",
            "INDEPENDENT_REVIEW_REQUIRED", "REVIEWER_ASSIGNED", "APPROVAL_REJECTED_BY_INDEPENDENCE_RULE", "SPOTCHECK_ASSIGNED",
            "VALUE_PROFILE_PUBLISHED", "VALUE_PROFILE_APPLIED", "VALUE_PROFILE_RESOLVED",
            "CONFLICT_DETECTED", "CONFLICT_WORK_ITEM_CREATED", "CONFLICT_RESOLUTION_PUBLISHED",
            "EXCEPTION_GRANTED", "EXCEPTION_EXPIRED", "RISK_COST_COMPUTED",
            "VERIFIER_PRICE_UPDATED", "VERIFICATION_BUDGET_DEBITED", "VERIFIER_SET_SELECTED", "VERIFICATION_BUDGET_INSUFFICIENT",
            "VERIFICATION_BUDGET_INITIALIZED",
            "VERIFIER_CORRELATION_COMPUTED", "VERIFIER_CLUSTER_UPDATED", "VERIFIER_MONOCULTURE_DETECTED",
            "ATTACK_SIMULATION_STARTED", "ATTACK_SIMULATION_COMPLETED", "ATTACK_SCENARIO_FAILED",
            "REALITY_CONTRACT_PUBLISHED", "PINSET_PUBLISHED", "PINSET_APPLIED",
            "RELEASE_COMPAT_CHECK_RAN", "RELEASE_BLOCKED_BY_CONTRACT", "RELEASE_APPROVED",
            "CONNECTOR_REGISTERED", "CONNECTOR_REQUESTED", "CONNECTOR_CALL_EXECUTED", "CONNECTOR_CALL_DENIED", "CONNECTOR_CALL_VERIFIED",
            "CAPABILITY_GRANT_ISSUED", "CAPABILITY_GRANT_USED", "CAPABILITY_GRANT_REVOKED", "CAPABILITY_GRANT_EXPIRED",
            "A2A_MESSAGE_SENT", "A2A_MESSAGE_RECEIVED", "A2A_MESSAGE_REJECTED",
            "EXECUTION_PROFILE_DECLARED", "ATTESTATION_VERIFIED",
            "FEDERATION_LINK_PROPOSED", "FEDERATION_LINK_ACCEPTED", "FEDERATION_LINK_REJECTED", "FEDERATION_POLICY_APPLIED", "FEDERATION_VIOLATION_DETECTED",
            "DID_REGISTERED", "VC_ISSUED", "VC_REVOKED", "IDENTITY_TRUST_ROOT_PUBLISHED",
            "MEMORY_CAPSULE_PUBLISHED", "MEMORY_CAPSULE_SHARED", "MEMORY_CAPSULE_IMPORTED", "MEMORY_CAPSULE_REJECTED",
            "CONNECTOR_SDK_MANIFEST_PUBLISHED", "CONNECTOR_CONFORMANCE_RAN", "CONNECTOR_CERTIFIED",
            "TRUST_TIER_PROPOSED", "TRUST_TIER_ACCEPTED", "TRUST_TIER_REJECTED", "TRUST_TIER_DOWNGRADE_EXCEPTION_GRANTED",
            "EXTERNAL_APPROVAL_REQUESTED", "EXTERNAL_APPROVAL_RECEIPT_RECEIVED", "EXTERNAL_APPROVAL_VERIFIED", "EXTERNAL_APPROVAL_REJECTED",
            "APPROVAL_GRANTED", "APPROVAL_DENIED",
            "BRIDGE_CONFIG_PUBLISHED", "BRIDGE_SEND_SUCCEEDED", "BRIDGE_SEND_FAILED", "BRIDGE_WEBHOOK_RECEIVED",
            "THRESHOLD_ACTION_PROPOSED", "THRESHOLD_SIGNATURE_ADDED", "THRESHOLD_ACTION_FINALIZED", "THRESHOLD_ACTION_EXPIRED",
            "KEY_CREATED", "KEY_ROTATED", "KEY_REVOKED", "SECRET_TOKEN_ISSUED", "SECRET_TOKEN_REVOKED",
            "BREAK_GLASS_REQUESTED", "BREAK_GLASS_GRANTED", "BREAK_GLASS_EXPIRED", "VAULT_HEALTH_CHECK_RAN",
            "BRIDGE_TRUST_ROOT_PUBLISHED", "BRIDGE_TRUST_ROOT_ROTATED", "GRANTS_FROZEN", "COMPROMISE_RESPONSE_RECORDED",
            "ISSUER_GROUP_PUBLISHED", "ISSUER_GROUP_MEMBER_ADDED", "ISSUER_GROUP_MEMBER_REMOVED",
            "VC_ISSUANCE_PROPOSED", "VC_REVOCATION_PROPOSED",
            "DISPUTE_OPENED", "DISPUTE_TRIAGED", "DISPUTE_REJECTED", "DISPUTE_ARBITRATION_STARTED", "DISPUTE_RESOLVED",
            "SETTLEMENT_PUBLISHED",
            "REPUTATION_ATTESTED", "REPUTATION_IMPORTED", "REPUTATION_IMPORT_REJECTED",
            "ENTITY_PAUSED", "ENTITY_RESUMED", "CONTROL_OVERRIDE_APPLIED", "HANDOFF_TO_HUMAN_REQUESTED",
            "GOAL_ASSIGNED", "AUTONOMY_LEVEL_SET",
            "DRIFT_SCORE_COMPUTED", "DRIFT_ALERT_RAISED", "DRIFT_SAFEGUARD_APPLIED",
        ):
            audit_events.append({
                **base,
                "action": action,
                "resource": (
                    payload.get("resource") or payload.get("decision_id") or payload.get("path")
                    or payload.get("artifact_path") or payload.get("incident_id") or payload.get("job_id")
                    or payload.get("artifact_id") or payload.get("request_id") or payload.get("anchor_id")
                    or payload.get("sandbox_id") or payload.get("tool_call_id") or payload.get("loop_id")
                    or payload.get("work_item_id") or payload.get("contract_id") or payload.get("suggestion_id")
                    or payload.get("rollout_id") or payload.get("judgment_id")
                    or payload.get("attestation_id") or payload.get("check_id") or payload.get("plugin_id")
                    or payload.get("hold_id") or payload.get("key_id") or payload.get("scan_id")
                    or payload.get("robustness_id") or payload.get("source_id") or payload.get("run_id")
                    or payload.get("profile_id") or payload.get("blast_id") or payload.get("batch_id")
                    or payload.get("spotcheck_id") or payload.get("risk_id")
                    or payload.get("gap_id") or payload.get("regret_id") or payload.get("lesson_id") or payload.get("queue_id") or payload.get("branch_id")
                    or payload.get("contract_id") or payload.get("invalid_id") or payload.get("check_id") or payload.get("safeguard_id") or payload.get("spotcheck_assignment_id")
                    or payload.get("conflict_id") or payload.get("resolution_id") or payload.get("exception_id")
                    or payload.get("selection_id") or payload.get("budget_key") or payload.get("corr_id") or payload.get("cluster_id") or payload.get("run_id")
                    or payload.get("pinset_id") or payload.get("report_id")
                    or payload.get("grant_id") or payload.get("call_id") or payload.get("message_id")
                    or payload.get("link_id") or payload.get("vc_id") or payload.get("capsule_id") or payload.get("root_id")
                    or payload.get("receipt_id") or payload.get("bridge_id")
                    or payload.get("action_id") or payload.get("token_ref_id") or payload.get("group_id") or payload.get("response_id")
                    or payload.get("dispute_id") or payload.get("settlement_id") or payload.get("import_id")
                    or payload.get("drift_id") or ""
                ),
            })

    with open(root / "incidents.jsonl", "w", encoding="utf-8") as f:
        for r in incidents:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(root / "policy_events.jsonl", "w", encoding="utf-8") as f:
        for r in policy_events:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(root / "audit_events.jsonl", "w", encoding="utf-8") as f:
        for r in audit_events:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    save_checkpoint(workspace_root, "extras", checkpoint)
