"""
RTC world state — a deterministic, pure reduction of the event stream
(RTC_WORLD_STATE_SPEC.md, INV-A31).

    world_state(seq_n) = reduce(apply, events[0..n], initial_state())

`apply` performs no I/O and reads no clock — every timestamp it stores comes
from the event itself. Same events on any host at any wall-clock time produce
the same state hash (WST-U1). Delete every derived store and the worldview
rebuilds from the log (WST-E1).
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping

from hg_core.ledger.canonical_json import canonical_dumps

# Bounded ring sizes — bounds are part of the reducer definition, so replay
# reproduces them exactly.
RECENT_INGRESS_MAX = 32
RECENT_RECEIPTS_MAX = 32
CONVERSATION_TURNS_MAX = 16
PENDING_META_MAX = 64


def initial_state() -> Dict[str, Any]:
    return {
        "activity": {
            "recent_ingress": [],       # [{event_id, type, source}]
            "recent_receipts": [],      # [{event_id, type, refs}]
            "recent_governance_traces": [],
            "recent_memory_retrievals": [],
            "recent_aep_signals": [],
            "proposals": {"emitted": 0, "failed": 0, "tokens": 0},
            "decisions": {"allowed": 0, "blocked": 0},
            "hal": {"requested": 0, "recorded": 0, "accepted": 0, "rejected": 0},
            "soar": {
                "domain_evaluated": 0,
                "d7_decisions": 0,
                "d7_critiques": 0,
                "accepted": 0,
                "deferred": 0,
                "rejected": 0,
            },
            "executions": {"committed": 0, "denied": 0, "receipted": 0, "oea_stub_logged": 0},
            "oea": {
                "bindings_created": 0,
                "bindings_refused": 0,
                "dry_runs": 0,
                "executions_requested": 0,
                "executions_started": 0,
                "executions_completed": 0,
                "executions_refused": 0,
                "executions_failed": 0,
                "receipts_recorded": 0,
                "lockdown": False,
                "last_binding_id": None,
                "last_capability_id": None,
                "last_receipt_id": None,
                "counts_by_status": {},
                "refusal_counts_by_reason": {},
            },
            "ter": {
                "commands_requested": 0,
                "policy_evaluations": 0,
                "refused": 0,
                "started": 0,
                "completed": 0,
                "timed_out": 0,
                "receipts_recorded": 0,
                "last_command_id": None,
                "last_receipt_hash": None,
                "counts_by_status": {},
                "refusal_counts_by_reason": {},
            },
            "memory": {"retrieved": 0, "written": 0},
            "aep": {
                "signals": 0,
                "signals_recorded": 0,
                "arousal_updates": 0,
                "modulations": 0,
            },
            "crr": {
                "trigger_decisions": 0,
                "eligibility_evaluations": 0,
                "checkpoints": 0,
                "cycles": 0,
                "state_transitions": 0,
                "hygiene_delegations": 0,
                "hygiene_executor_started": 0,
                "hygiene_executor_completed": 0,
                "hygiene_executor_failed": 0,
                "rehydration_verifications": 0,
                "load_order_verifications": 0,
                "trusted_snapshots": 0,
                "drain_cycles": 0,
                "cooldowns_set": 0,
                "escalation_refusals": 0,
            },
            "msc": {
                "requested": 0,
                "started": 0,
                "windows_selected": 0,
                "listening_completed": 0,
                "summaries_recorded": 0,
                "settled": 0,
                "skipped": 0,
                "failed": 0,
                "refused": 0,
                "refused_by_reason": {},
                "agents": {},
            },
            "ysr": {
                "requested": 0,
                "started": 0,
                "snapshots": 0,
                "scratch_cleared": 0,
                "event_head_reads": 0,
                "world_state_refreshed": 0,
                "memory_refs_refreshed": 0,
                "resync_verified": 0,
                "completed": 0,
                "no_op": 0,
                "refused": 0,
                "escalated": 0,
                "failed": 0,
                "refused_by_reason": {},
                "total_event_lag": 0,
                "yawn_count": 0,
                "agents": {},
            },
            "els": {
                "wake_requested": 0,
                "process_started": 0,
                "identity_bound": 0,
                "event_bus_connected": 0,
                "event_head_reads": 0,
                "replay_verified": 0,
                "replay_failed": 0,
                "world_state_derived": 0,
                "readiness_checks": 0,
                "ready_declared": 0,
                "degraded_ready_declared": 0,
                "work_admission_opened": 0,
                "wake_refused": 0,
                "wake_failed": 0,
                "safe_mode_entered": 0,
                "subagents_declared": 0,
                "subagents_ready": 0,
                "subagents_refused": 0,
                "refused_by_reason": {},
                "active_subagents": {},
            },
            "governance": {
                "trace_records": 0,
                "gpp_trace_records": 0,
                "permits_bound": 0,
                "binds_denied": 0,
            },
            "csm": {
                "changes_requested": 0,
                "classified": 0,
                "policy_evaluations": 0,
                "allowed": 0,
                "refused": 0,
                "approval_required": 0,
                "high_risk_confirmation_required": 0,
                "transition_refusals": 0,
                "last_change_id": None,
                "last_decision_hash": None,
                "refusal_counts_by_reason": {},
            },
            "mel": {
                "records_appended": 0,
                "receipts_recorded": 0,
                "chains_verified": 0,
                "chains_broken": 0,
                "ledger_head_hash": None,
                "chain_status": "unknown",
            },
            "srp": {
                "drifts_observed": 0,
                "test_failures_observed": 0,
                "audit_findings_observed": 0,
                "proposals": 0,
                "bundles_created": 0,
                "signatures_required": 0,
                "signatures_recorded": 0,
                "apply_refusals": 0,
                "apply_requests": 0,
                "approvals_verified": 0,
                "approvals_rejected": 0,
                "sandboxes_prepared": 0,
                "patches_applied": 0,
                "apply_tests_passed": 0,
                "apply_tests_failed": 0,
                "review_artifacts_created": 0,
                "merge_ready_marked": 0,
                "apply_rejected": 0,
                "apply_closed": 0,
                "self_edit_started": 0,
                "self_edit_completed": 0,
                "self_edit_rejected": 0,
                "self_edit_lockdowns": 0,
                "self_edit_rollbacks": 0,
                "final_confirmations_verified": 0,
                "protected_base_verified": 0,
                "handoffs_created": 0,
                "outcomes_recorded": 0,
            },
            "max_auto": {
                "runs_requested": 0,
                "runs_completed": 0,
                "runs_failed": 0,
                "runs_refused": 0,
                "observations_recorded": 0,
                "bundles_created": 0,
                "scope_approved": 0,
                "scope_rejected": 0,
                "worktrees_prepared": 0,
                "patches_completed": 0,
                "tests_completed": 0,
                "local_commits_created": 0,
                "lockdowns": 0,
                "last_run_id": None,
                "last_state": None,
                "last_bundle_hash": None,
                "last_commit_sha": None,
                "last_verdict": None,
            },
        },
        "conversations": {},            # session_id -> {turns: [...], last_event_id}
        "goals": {
            "pending_tasks": [],        # [{event_id, ref}]
            "gaps": [],                 # [{event_id, ref}]
        },
        "environment": {
            "arousal": {"max_severity": 0, "dimensions": {}},
            "recovery_state": "NORMAL",
            "panic": False,
            "health": {
                "handler_failures": 0,
                "events_dropped": 0,
                "slow_ticks": 0,
                "memory_write_failures": 0,
                "memory_retrieve_failures": 0,
                "panic_blocks": 0,
                "stop_requests": 0,
            },
        },
        "self": {
            "runtime_version": None,
            "registry_hash": None,
            "started_at": None,
            "ticks": 0,
            "last_tick_seq": None,
            "last_recovery_cycle": None,
            "last_meditation_by_agent": {},
            "last_yawn_by_agent": {},
            "wake_state": "COLD",
            "startup_posture": None,
            "last_wake_verdict": None,
            "work_admission_open": False,
            "last_wake_by_agent": {},
        },
        "meta": {
            "last_seq": None,
            "events_applied": 0,
            "unhandled_types": {},
        },
    }


def _push(ring: List[Any], item: Any, cap: int) -> List[Any]:
    out = list(ring)
    out.append(item)
    if len(out) > cap:
        out = out[-cap:]
    return out


def apply(state: Mapping[str, Any], event: Mapping[str, Any]) -> Dict[str, Any]:
    """Pure reducer: returns a new state dict; never mutates the input."""
    s = json.loads(json.dumps(state))  # deep copy via JSON — state is JSON-only by construction
    etype = event["type"]
    payload = event.get("payload", {})
    eid = event["event_id"]

    if etype == "CHAT_MESSAGE":
        session = str(payload.get("session_id", "default"))
        conv = s["conversations"].get(session, {"turns": [], "last_event_id": None})
        conv["turns"] = _push(
            conv["turns"],
            {"event_id": eid, "role": payload.get("role", "user")},
            CONVERSATION_TURNS_MAX,
        )
        conv["last_event_id"] = eid
        s["conversations"][session] = conv
        s["activity"]["recent_ingress"] = _push(
            s["activity"]["recent_ingress"],
            {"event_id": eid, "type": etype, "source": event["source"]},
            RECENT_INGRESS_MAX,
        )
    elif etype in ("API_REQUEST", "WEBHOOK_IN", "TIMER_EVENT", "FILE_WATCH"):
        s["activity"]["recent_ingress"] = _push(
            s["activity"]["recent_ingress"],
            {"event_id": eid, "type": etype, "source": event["source"]},
            RECENT_INGRESS_MAX,
        )
    elif etype in ("PROPOSAL_EMITTED", "MODEL_PROPOSAL_RECORDED"):
        s["activity"]["proposals"]["emitted"] += 1
    elif etype in ("PROPOSAL_FAILED", "MODEL_STREAM_FAILED"):
        s["activity"]["proposals"]["failed"] += 1
    elif etype in ("PROPOSAL_TOKEN_EMITTED", "MODEL_TOKEN_DELTA"):
        s["activity"]["proposals"]["tokens"] += 1
    elif etype in ("PROPOSAL_STREAM_STARTED", "MODEL_STREAM_STARTED", "MODEL_STREAM_COMPLETED"):
        pass  # informational; counted via emitted/failed terminals
    elif etype == "SOAR_DOMAIN_EVALUATED":
        s["activity"]["soar"]["domain_evaluated"] += 1
    elif etype == "SOAR_D7_DECISION_RECORDED":
        s["activity"]["soar"]["d7_decisions"] += 1
        binding = str(payload.get("binding", ""))
        if binding == "ACCEPT":
            s["activity"]["soar"]["accepted"] += 1
        elif binding == "DEFER":
            s["activity"]["soar"]["deferred"] += 1
        elif binding in ("REJECT", "NO_OP"):
            s["activity"]["soar"]["rejected"] += 1
    elif etype == "SOAR_D7_CRITIQUE_RECORDED":
        s["activity"]["soar"]["d7_critiques"] += 1
    elif etype == "HAL_ARBITRATION_REQUESTED":
        s["activity"]["hal"]["requested"] += 1
    elif etype == "HAL_ARBITRATION_RECORDED":
        s["activity"]["hal"]["recorded"] += 1
        routing = str(payload.get("routing", ""))
        if routing == "ACCEPT":
            s["activity"]["hal"]["accepted"] += 1
        elif routing in ("REJECT", "DEFER"):
            s["activity"]["hal"]["rejected"] += 1
    elif etype == "DECISION_EVENT":
        s["activity"]["decisions"]["allowed"] += 1
    elif etype == "DECISION_BLOCKED":
        s["activity"]["decisions"]["blocked"] += 1
    elif etype == "GOVERNANCE_TRACE_RECORDED":
        s["activity"]["governance"]["trace_records"] += 1
        s["activity"]["recent_governance_traces"] = _push(
            s["activity"]["recent_governance_traces"],
            {
                "event_id": eid,
                "trace_event_hash": payload.get("trace_event_hash"),
                "trace_path": payload.get("trace_path"),
            },
            RECENT_RECEIPTS_MAX,
        )
    elif etype == "GPP_TRACE_RECORDED":
        s["activity"]["governance"]["gpp_trace_records"] += 1
        s["activity"]["recent_governance_traces"] = _push(
            s["activity"]["recent_governance_traces"],
            {
                "event_id": eid,
                "trace_event_hash": payload.get("trace_event_hash"),
                "trace_path": payload.get("trace_path"),
            },
            RECENT_RECEIPTS_MAX,
        )
    elif etype == "GPP_PERMIT_BOUND":
        s["activity"]["governance"]["permits_bound"] += 1
    elif etype == "GPP_BIND_DENIED":
        s["activity"]["governance"]["binds_denied"] += 1
    elif etype in ("ACTION_COMMITTED", "UEAK_EXECUTION_COMMITTED"):
        s["activity"]["executions"]["committed"] += 1
    elif etype in ("ACTION_DENIED", "UEAK_EXECUTION_DENIED"):
        s["activity"]["executions"]["denied"] += 1
    elif etype == "EFFECT_RECEIPTED":
        s["activity"]["executions"]["receipted"] += 1
        s["activity"]["recent_receipts"] = _push(
            s["activity"]["recent_receipts"],
            {"event_id": eid, "receipt_id": payload.get("receipt_id")},
            RECENT_RECEIPTS_MAX,
        )
    elif etype in ("OEA_STUB_RECORDED", "OEA_EFFECT_STUB_RECORDED"):
        s["activity"]["executions"]["oea_stub_logged"] += 1
    elif etype == "OEA_BINDING_CREATED":
        s["activity"]["oea"]["bindings_created"] += 1
        s["activity"]["oea"]["last_binding_id"] = payload.get("binding_id")
        s["activity"]["oea"]["last_capability_id"] = payload.get("capability_id")
    elif etype == "OEA_BINDING_REFUSED":
        s["activity"]["oea"]["bindings_refused"] += 1
        reason = str(payload.get("reason", "unknown"))
        counts = s["activity"]["oea"]["refusal_counts_by_reason"]
        counts[reason] = int(counts.get(reason, 0)) + 1
    elif etype == "OEA_DRY_RUN_COMPLETED":
        s["activity"]["oea"]["dry_runs"] += 1
    elif etype == "OEA_EXECUTION_REQUESTED":
        s["activity"]["oea"]["executions_requested"] += 1
    elif etype == "OEA_EXECUTION_STARTED":
        s["activity"]["oea"]["executions_started"] += 1
    elif etype == "OEA_EXECUTION_COMPLETED":
        s["activity"]["oea"]["executions_completed"] += 1
        status = str(payload.get("result_status", "unknown"))
        counts = s["activity"]["oea"]["counts_by_status"]
        counts[status] = int(counts.get(status, 0)) + 1
    elif etype == "OEA_EXECUTION_REFUSED":
        s["activity"]["oea"]["executions_refused"] += 1
        reason = str(payload.get("reason", "unknown"))
        counts = s["activity"]["oea"]["refusal_counts_by_reason"]
        counts[reason] = int(counts.get(reason, 0)) + 1
    elif etype == "OEA_EXECUTION_FAILED":
        s["activity"]["oea"]["executions_failed"] += 1
    elif etype == "OEA_EFFECT_RECEIPT_RECORDED":
        s["activity"]["oea"]["receipts_recorded"] += 1
        s["activity"]["oea"]["last_receipt_id"] = payload.get("receipt_id")
    elif etype == "OEA_LOCKDOWN_ENTERED":
        s["activity"]["oea"]["lockdown"] = True
    elif etype in ("AEP_SIGNAL_EMITTED", "AEP_SIGNAL_RECORDED"):
        if etype == "AEP_SIGNAL_RECORDED":
            s["activity"]["aep"]["signals_recorded"] += 1
        else:
            s["activity"]["aep"]["signals"] += 1
        signal_class = payload.get("class")
        severity = int(payload.get("severity", 0))
        s["activity"]["recent_aep_signals"] = _push(
            s["activity"]["recent_aep_signals"],
            {
                "event_id": eid,
                "signal_id": payload.get("signal_id"),
                "class": signal_class,
                "severity": severity,
                "scope": payload.get("scope"),
            },
            RECENT_RECEIPTS_MAX,
        )
        dimensions = dict(s["environment"]["arousal"].get("dimensions", {}))
        if signal_class:
            dimensions[str(signal_class)] = max(int(dimensions.get(str(signal_class), 0)), severity)
        s["environment"]["arousal"] = {
            "max_severity": max(int(s["environment"]["arousal"].get("max_severity", 0)), severity),
            "dimensions": dimensions,
        }
    elif etype == "AEP_AROUSAL_STATE_UPDATED":
        s["activity"]["aep"]["arousal_updates"] += 1
        levels = payload.get("levels", {})
        dimensions = {name: int(value) for name, value in levels.items() if int(value) > 0}
        s["environment"]["arousal"] = {
            "max_severity": int(payload.get("max_severity", 0)),
            "dimensions": dimensions,
            "scope": payload.get("scope"),
            "state_hash": payload.get("state_hash"),
        }
    elif etype == "AEP_MODULATION_RECORDED":
        s["activity"]["aep"]["modulations"] += 1
    elif etype == "AROUSAL_CHANGED":
        s["environment"]["arousal"] = {
            "max_severity": int(payload.get("max_severity", 0)),
            "dimensions": dict(payload.get("dimensions", {})),
        }
    elif etype == "RECOVERY_STATE_CHANGED":
        s["environment"]["recovery_state"] = str(payload.get("state", "NORMAL"))
        if payload.get("state") == "NORMAL" and payload.get("cycle_id"):
            s["self"]["last_recovery_cycle"] = payload.get("cycle_id")
    elif etype == "CRR_TRIGGER_DECIDED":
        s["activity"]["crr"]["trigger_decisions"] += 1
    elif etype == "CRR_RECOVERY_ELIGIBILITY_EVALUATED":
        s["activity"]["crr"]["eligibility_evaluations"] += 1
    elif etype == "CRR_RECOVERY_CYCLE_STARTED":
        pass
    elif etype == "CRR_RECOVERY_LEVEL_SELECTED":
        pass
    elif etype == "CRR_RECOVERY_STATE_TRANSITION":
        s["activity"]["crr"]["state_transitions"] += 1
        s["environment"]["recovery_state"] = str(payload.get("to_state", "RECOVERY"))
    elif etype == "CRR_ADMISSION_PAUSED":
        pass
    elif etype == "CRR_DRAIN_STARTED":
        pass
    elif etype == "CRR_DRAIN_COMPLETED":
        s["activity"]["crr"]["drain_cycles"] += 1
    elif etype == "CRR_CHECKPOINT_RECORDED":
        s["activity"]["crr"]["checkpoints"] += 1
    elif etype == "CRR_HYGIENE_DELEGATED":
        s["activity"]["crr"]["hygiene_delegations"] += 1
    elif etype == "CRR_HYGIENE_EXECUTOR_STARTED":
        s["activity"]["crr"]["hygiene_executor_started"] += 1
    elif etype == "CRR_HYGIENE_EXECUTOR_COMPLETED":
        s["activity"]["crr"]["hygiene_executor_completed"] += 1
    elif etype == "CRR_HYGIENE_EXECUTOR_FAILED":
        s["activity"]["crr"]["hygiene_executor_failed"] += 1
    elif etype == "CRR_REHYDRATION_VERIFIED":
        s["activity"]["crr"]["rehydration_verifications"] += 1
    elif etype == "CRR_REHYDRATION_LOAD_ORDER_VERIFIED":
        s["activity"]["crr"]["load_order_verifications"] += 1
    elif etype == "CRR_RECOVERY_COOLDOWN_SET":
        s["activity"]["crr"]["cooldowns_set"] += 1
    elif etype == "CRR_RECOVERY_ESCALATION_REFUSED":
        s["activity"]["crr"]["escalation_refusals"] += 1
    elif etype == "CRR_TRUSTED_SNAPSHOT_RECORDED":
        s["activity"]["crr"]["trusted_snapshots"] += 1
    elif etype == "CRR_RECOVERY_CYCLE_COMPLETED":
        pass
    elif etype == "CRR_RECOVERY_CYCLE_FAILED":
        pass
    elif etype == "CRR_CYCLE_RECORDED":
        s["activity"]["crr"]["cycles"] += 1
    elif etype == "MSC_MEDITATION_REQUESTED":
        s["activity"]["msc"]["requested"] += 1
    elif etype == "MSC_MEDITATION_STARTED":
        s["activity"]["msc"]["started"] += 1
    elif etype == "MSC_EVENT_WINDOW_SELECTED":
        s["activity"]["msc"]["windows_selected"] += 1
    elif etype == "MSC_LISTENING_COMPLETED":
        s["activity"]["msc"]["listening_completed"] += 1
    elif etype == "MSC_SUMMARY_RECORDED":
        s["activity"]["msc"]["summaries_recorded"] += 1
        agent_id = str(payload.get("agent_id", "unknown"))
        s["activity"]["msc"]["agents"][agent_id] = {
            "last_summary_hash": payload.get("summary_hash"),
            "last_summary_id": payload.get("summary_id"),
            "observed_event_count": payload.get("observed_event_count"),
        }
    elif etype == "MSC_SETTLED":
        s["activity"]["msc"]["settled"] += 1
        cycle = payload.get("cycle", {})
        if isinstance(cycle, Mapping):
            agent_id = str(cycle.get("agent_id", "unknown"))
            s["self"]["last_meditation_by_agent"][agent_id] = {
                "cycle_id": cycle.get("cycle_id"),
                "status": cycle.get("result_status", "SETTLED"),
                "summary_hash": payload.get("summary_hash"),
                "observed_event_count": cycle.get("observed_event_count", 0),
            }
    elif etype == "MSC_SKIPPED":
        s["activity"]["msc"]["skipped"] += 1
    elif etype == "MSC_FAILED":
        s["activity"]["msc"]["failed"] += 1
    elif etype == "MSC_REFUSED":
        s["activity"]["msc"]["refused"] += 1
        reason = str(payload.get("reason_code", "unknown"))
        counts = s["activity"]["msc"]["refused_by_reason"]
        counts[reason] = counts.get(reason, 0) + 1
        cycle = payload.get("cycle", {})
        if isinstance(cycle, Mapping):
            agent_id = str(cycle.get("agent_id", "unknown"))
            s["self"]["last_meditation_by_agent"][agent_id] = {
                "cycle_id": cycle.get("cycle_id"),
                "status": cycle.get("result_status", reason),
                "summary_hash": None,
                "observed_event_count": 0,
            }
    elif etype == "YSR_YAWN_REQUESTED":
        s["activity"]["ysr"]["requested"] += 1
    elif etype == "YSR_YAWN_STARTED":
        s["activity"]["ysr"]["started"] += 1
    elif etype == "YSR_SCRATCH_SNAPSHOT_RECORDED":
        s["activity"]["ysr"]["snapshots"] += 1
    elif etype == "YSR_SCRATCH_CLEARED":
        s["activity"]["ysr"]["scratch_cleared"] += 1
    elif etype == "YSR_EVENT_HEAD_READ":
        s["activity"]["ysr"]["event_head_reads"] += 1
        lag = int(payload.get("event_lag_count", 0) or 0)
        s["activity"]["ysr"]["total_event_lag"] += lag
    elif etype == "YSR_WORLD_STATE_REFRESHED":
        s["activity"]["ysr"]["world_state_refreshed"] += 1
    elif etype == "YSR_MEMORY_REFS_REFRESHED":
        s["activity"]["ysr"]["memory_refs_refreshed"] += 1
    elif etype == "YSR_RESYNC_VERIFIED":
        s["activity"]["ysr"]["resync_verified"] += 1
    elif etype == "YSR_YAWN_COMPLETED":
        s["activity"]["ysr"]["completed"] += 1
        s["activity"]["ysr"]["yawn_count"] += 1
        cycle = payload.get("cycle", {})
        if isinstance(cycle, Mapping):
            agent_id = str(cycle.get("agent_id", "unknown"))
            s["activity"]["ysr"]["agents"][agent_id] = {
                "last_cycle_id": cycle.get("cycle_id"),
                "status": cycle.get("result_status", "RESUMED"),
                "event_lag_count": cycle.get("event_lag_count", 0),
            }
            s["self"]["last_yawn_by_agent"][agent_id] = {
                "cycle_id": cycle.get("cycle_id"),
                "status": "RESUMED",
                "event_lag_count": cycle.get("event_lag_count", 0),
            }
    elif etype == "YSR_YAWN_NO_OP":
        s["activity"]["ysr"]["no_op"] += 1
    elif etype == "YSR_YAWN_REFUSED":
        s["activity"]["ysr"]["refused"] += 1
        reason = str(payload.get("reason_code", "unknown"))
        counts = s["activity"]["ysr"]["refused_by_reason"]
        counts[reason] = counts.get(reason, 0) + 1
        agent_id = str(payload.get("agent_id", "unknown"))
        s["self"]["last_yawn_by_agent"][agent_id] = {
            "cycle_id": payload.get("cycle_id"),
            "status": "REFUSED",
            "reason": reason,
        }
    elif etype == "YSR_ESCALATED_TO_CRR":
        s["activity"]["ysr"]["escalated"] += 1
    elif etype == "YSR_YAWN_FAILED":
        s["activity"]["ysr"]["failed"] += 1
    elif etype == "ELS_WAKE_REQUESTED":
        s["activity"]["els"]["wake_requested"] += 1
        s["self"]["wake_state"] = "WAKE_REQUESTED"
        agent_id = str(payload.get("agent_id", "unknown"))
        s["self"]["last_wake_by_agent"][agent_id] = {
            "wake_id": payload.get("wake_id"),
            "profile": payload.get("profile"),
            "status": "WAKE_REQUESTED",
        }
    elif etype == "ELS_PROCESS_STARTED":
        s["activity"]["els"]["process_started"] += 1
        s["self"]["wake_state"] = "PROCESS_STARTED"
    elif etype == "ELS_IDENTITY_BOUND":
        s["activity"]["els"]["identity_bound"] += 1
        s["self"]["wake_state"] = "IDENTITY_BOUND"
    elif etype == "ELS_EVENT_BUS_CONNECTED":
        s["activity"]["els"]["event_bus_connected"] += 1
        s["self"]["wake_state"] = "EVENT_BUS_CONNECTED"
    elif etype == "ELS_EVENT_HEAD_READ":
        s["activity"]["els"]["event_head_reads"] += 1
        s["self"]["wake_state"] = "EVENT_HEAD_READ"
    elif etype == "ELS_REPLAY_VERIFIED":
        s["activity"]["els"]["replay_verified"] += 1
        s["self"]["wake_state"] = "REPLAY_VERIFIED"
    elif etype == "ELS_REPLAY_FAILED":
        s["activity"]["els"]["replay_failed"] += 1
        s["self"]["wake_state"] = "REPLAY_FAILED"
    elif etype == "ELS_WORLD_STATE_DERIVED":
        s["activity"]["els"]["world_state_derived"] += 1
        s["self"]["wake_state"] = "WORLD_STATE_DERIVED"
    elif etype == "ELS_READINESS_CHECK_RECORDED":
        s["activity"]["els"]["readiness_checks"] += 1
        check = payload.get("check", {})
        if isinstance(check, dict) and check.get("status") == "fail":
            failed = s["self"].setdefault("failed_readiness_checks", [])
            if isinstance(failed, list):
                failed.append(check.get("check_id"))
    elif etype == "ELS_POSTURE_SELECTED":
        s["self"]["startup_posture"] = payload.get("posture")
        s["self"]["wake_state"] = "POSTURE_SELECTED"
    elif etype == "ELS_READY_DECLARED":
        s["activity"]["els"]["ready_declared"] += 1
        s["self"]["wake_state"] = "READY_DECLARED"
        s["self"]["last_wake_verdict"] = "ready"
        s["self"]["startup_posture"] = payload.get("posture")
    elif etype == "ELS_DEGRADED_READY_DECLARED":
        s["activity"]["els"]["degraded_ready_declared"] += 1
        s["self"]["wake_state"] = "DEGRADED_READY_DECLARED"
        s["self"]["last_wake_verdict"] = "degraded_ready"
        s["self"]["startup_posture"] = payload.get("posture")
    elif etype == "ELS_WORK_ADMISSION_OPENED":
        s["activity"]["els"]["work_admission_opened"] += 1
        s["self"]["wake_state"] = "WORK_ADMISSION_OPEN"
        s["self"]["work_admission_open"] = True
    elif etype == "ELS_WAKE_REFUSED":
        s["activity"]["els"]["wake_refused"] += 1
        reason = str(payload.get("reason_code", "unknown"))
        counts = s["activity"]["els"]["refused_by_reason"]
        counts[reason] = counts.get(reason, 0) + 1
        s["self"]["wake_state"] = "WAKE_REFUSED"
        s["self"]["last_wake_verdict"] = "refused"
        s["self"]["work_admission_open"] = False
        agent_id = str(payload.get("agent_id", "unknown"))
        s["self"]["last_wake_by_agent"][agent_id] = {
            "wake_id": payload.get("wake_id"),
            "status": "WAKE_REFUSED",
            "reason": reason,
        }
    elif etype == "ELS_WAKE_FAILED":
        s["activity"]["els"]["wake_failed"] += 1
        s["self"]["wake_state"] = "WAKE_FAILED"
        s["self"]["last_wake_verdict"] = "failed"
        s["self"]["work_admission_open"] = False
    elif etype == "ELS_SAFE_MODE_ENTERED":
        s["activity"]["els"]["safe_mode_entered"] += 1
        s["self"]["wake_state"] = "SAFE_MODE_ENTERED"
        s["self"]["startup_posture"] = "SAFE_MODE"
        s["self"]["last_wake_verdict"] = "safe_mode"
        s["self"]["work_admission_open"] = False
    elif etype == "ELS_SUBAGENT_DECLARED":
        s["activity"]["els"]["subagents_declared"] += 1
        agent_id = str(payload.get("agent_id", "unknown"))
        s["activity"]["els"]["active_subagents"][agent_id] = {
            "parent_agent_id": payload.get("parent_agent_id"),
            "status": "SUBAGENT_DECLARED",
        }
    elif etype == "ELS_SUBAGENT_READY":
        s["activity"]["els"]["subagents_ready"] += 1
        agent_id = str(payload.get("agent_id", "unknown"))
        s["activity"]["els"]["active_subagents"][agent_id] = {
            "status": "SUBAGENT_READY",
            "posture": payload.get("posture"),
        }
    elif etype == "ELS_SUBAGENT_REFUSED":
        s["activity"]["els"]["subagents_refused"] += 1
        agent_id = str(payload.get("agent_id", "unknown"))
        s["activity"]["els"]["active_subagents"][agent_id] = {
            "status": "SUBAGENT_REFUSED",
            "reason": payload.get("refusal_reason"),
        }
    elif etype in (
        "ELS_CONFIG_LOADED",
        "ELS_MEMORY_CONTEXT_LOADED",
        "ELS_CAPABILITY_CATALOG_LOADED",
        "ELS_QUIET_SETTLING_STARTED",
        "ELS_QUIET_SETTLING_COMPLETED",
        "ELS_SUBAGENT_IDENTITY_BOUND",
        "ELS_SUBAGENT_SCOPE_BOUND",
        "ELS_SUBAGENT_CONTEXT_LOADED",
    ):
        pass  # witnessed; no aggregate counter beyond lifecycle
    elif etype == "PANIC_ENTERED":
        s["environment"]["panic"] = True
    elif etype == "PANIC_CLEARED":
        s["environment"]["panic"] = False
    elif etype == "RUNTIME_STARTED":
        s["self"]["runtime_version"] = payload.get("runtime_version")
        s["self"]["registry_hash"] = payload.get("registry_hash")
        s["self"]["started_at"] = event["timestamp"]
    elif etype == "RUNTIME_TICK_STARTED":
        pass  # witnessed; tick counter advances on completion events
    elif etype in ("TICK_COMPLETED", "RUNTIME_TICK_COMPLETED"):
        s["self"]["ticks"] += 1
        s["self"]["last_tick_seq"] = event["seq"]
    elif etype == "RUNTIME_STOP_REQUESTED":
        s["environment"]["health"]["stop_requests"] += 1
    elif etype in ("RUNTIME_STOPPING", "RUNTIME_STOPPED"):
        pass
    elif etype == "RUNTIME_PANIC_BLOCKED":
        s["environment"]["health"]["panic_blocks"] += 1
    elif etype == "TICK_SLOW":
        s["environment"]["health"]["slow_ticks"] += 1
    elif etype in ("MEMORY_RETRIEVE_REQUESTED", "MEMORY_STORE_REQUESTED"):
        pass  # lifecycle witness; counts on completion/failure
    elif etype in ("MEMORY_RETRIEVE_COMPLETED", "MEMORY_RETRIEVED"):
        s["activity"]["memory"]["retrieved"] += 1
        provenance = payload.get("provenance", payload)
        s["activity"]["recent_memory_retrievals"] = _push(
            s["activity"]["recent_memory_retrievals"],
            {
                "event_id": eid,
                "query": provenance.get("query") if isinstance(provenance, Mapping) else None,
                "result_refs": list(
                    provenance.get("result_refs", []) if isinstance(provenance, Mapping) else []
                ),
                "status": payload.get("status", "ok"),
            },
            RECENT_RECEIPTS_MAX,
        )
    elif etype == "MEMORY_RETRIEVE_FAILED":
        s["environment"]["health"]["memory_retrieve_failures"] += 1
    elif etype in ("MEMORY_STORE_COMPLETED", "MEMORY_WRITTEN", "MEMORY_CONSOLIDATED"):
        s["activity"]["memory"]["written"] += 1
    elif etype in ("MEMORY_STORE_FAILED", "MEMORY_WRITE_FAILED"):
        s["environment"]["health"]["memory_write_failures"] += 1
    elif etype == "TER_COMMAND_REQUESTED":
        s["activity"]["ter"]["commands_requested"] += 1
        s["activity"]["ter"]["last_command_id"] = payload.get("request_id")
    elif etype == "TER_COMMAND_POLICY_EVALUATED":
        s["activity"]["ter"]["policy_evaluations"] += 1
    elif etype == "TER_COMMAND_REFUSED":
        s["activity"]["ter"]["refused"] += 1
        reason = str(payload.get("reason_code", "unknown"))
        counts = s["activity"]["ter"]["refusal_counts_by_reason"]
        counts[reason] = counts.get(reason, 0) + 1
    elif etype == "TER_COMMAND_STARTED":
        s["activity"]["ter"]["started"] += 1
    elif etype == "TER_COMMAND_COMPLETED":
        s["activity"]["ter"]["completed"] += 1
        status = str(payload.get("result_status", "unknown"))
        counts = s["activity"]["ter"]["counts_by_status"]
        counts[status] = counts.get(status, 0) + 1
    elif etype == "TER_COMMAND_TIMED_OUT":
        s["activity"]["ter"]["timed_out"] += 1
        counts = s["activity"]["ter"]["counts_by_status"]
        counts["timed_out"] = counts.get("timed_out", 0) + 1
    elif etype == "TER_COMMAND_RECEIPT_RECORDED":
        s["activity"]["ter"]["receipts_recorded"] += 1
        s["activity"]["ter"]["last_receipt_hash"] = payload.get("receipt_hash")
        s["activity"]["recent_receipts"] = _push(
            s["activity"]["recent_receipts"],
            {
                "event_id": eid,
                "type": etype,
                "refs": [payload.get("receipt_id"), payload.get("receipt_hash")],
            },
            RECENT_RECEIPTS_MAX,
        )
    elif etype == "CSM_CHANGE_REQUESTED":
        s["activity"]["csm"]["changes_requested"] += 1
        s["activity"]["csm"]["last_change_id"] = payload.get("change_id")
    elif etype == "CSM_CHANGE_CLASSIFIED":
        s["activity"]["csm"]["classified"] += 1
    elif etype == "CSM_POLICY_EVALUATED":
        s["activity"]["csm"]["policy_evaluations"] += 1
        s["activity"]["csm"]["last_decision_hash"] = payload.get("decision_hash")
    elif etype == "CSM_CHANGE_ALLOWED":
        s["activity"]["csm"]["allowed"] += 1
    elif etype == "CSM_CHANGE_REFUSED":
        s["activity"]["csm"]["refused"] += 1
        reason = str(payload.get("reason_code", "unknown"))
        counts = s["activity"]["csm"]["refusal_counts_by_reason"]
        counts[reason] = counts.get(reason, 0) + 1
    elif etype == "CSM_APPROVAL_REQUIRED":
        s["activity"]["csm"]["approval_required"] += 1
    elif etype == "CSM_HIGH_RISK_CONFIRMATION_REQUIRED":
        s["activity"]["csm"]["high_risk_confirmation_required"] += 1
    elif etype == "CSM_LIFECYCLE_TRANSITION_REFUSED":
        s["activity"]["csm"]["transition_refusals"] += 1
    elif etype == "MEL_RECORD_APPENDED":
        s["activity"]["mel"]["records_appended"] += 1
        s["activity"]["mel"]["ledger_head_hash"] = payload.get("record_hash")
    elif etype == "MEL_RECEIPT_RECORDED":
        s["activity"]["mel"]["receipts_recorded"] += 1
        s["activity"]["mel"]["ledger_head_hash"] = payload.get("record_hash")
    elif etype == "MEL_CHAIN_VERIFIED":
        s["activity"]["mel"]["chains_verified"] += 1
        s["activity"]["mel"]["chain_status"] = "verified"
        s["activity"]["mel"]["ledger_head_hash"] = payload.get("head_hash")
    elif etype == "MEL_CHAIN_BROKEN":
        s["activity"]["mel"]["chains_broken"] += 1
        s["activity"]["mel"]["chain_status"] = "broken"
    elif etype == "SRP_DRIFT_OBSERVED":
        s["activity"]["srp"]["drifts_observed"] += 1
    elif etype == "SRP_TEST_FAILURE_OBSERVED":
        s["activity"]["srp"]["test_failures_observed"] += 1
    elif etype == "SRP_AUDIT_FINDING_OBSERVED":
        s["activity"]["srp"]["audit_findings_observed"] += 1
    elif etype == "SRP_PROPOSAL_BUNDLE_CREATED":
        s["activity"]["srp"]["bundles_created"] += 1
        s["activity"]["srp"]["proposals"] += 1
    elif etype == "SRP_PROPOSAL_BUNDLE_HASHED":
        pass
    elif etype == "SRP_HUMAN_SIGNATURE_REQUIRED":
        s["activity"]["srp"]["signatures_required"] += 1
    elif etype == "SRP_HUMAN_SIGNATURE_RECORDED":
        s["activity"]["srp"]["signatures_recorded"] += 1
    elif etype == "SRP_APPLY_REFUSED":
        s["activity"]["srp"]["apply_refusals"] += 1
    elif etype == "SRP_APPLY_REQUESTED":
        s["activity"]["srp"]["apply_requests"] += 1
    elif etype == "SRP_APPROVAL_VERIFIED":
        s["activity"]["srp"]["approvals_verified"] += 1
    elif etype == "SRP_APPROVAL_REJECTED":
        s["activity"]["srp"]["approvals_rejected"] += 1
    elif etype == "SRP_APPLY_SANDBOX_PREPARED":
        s["activity"]["srp"]["sandboxes_prepared"] += 1
    elif etype == "SRP_PATCH_APPLIED":
        s["activity"]["srp"]["patches_applied"] += 1
    elif etype == "SRP_APPLY_TESTS_PASSED":
        s["activity"]["srp"]["apply_tests_passed"] += 1
    elif etype == "SRP_APPLY_TESTS_FAILED":
        s["activity"]["srp"]["apply_tests_failed"] += 1
    elif etype == "SRP_REVIEW_ARTIFACT_CREATED":
        s["activity"]["srp"]["review_artifacts_created"] += 1
    elif etype == "SRP_FINAL_CONFIRMATION_REQUIRED":
        pass
    elif etype == "SRP_MERGE_READY":
        s["activity"]["srp"]["merge_ready_marked"] += 1
    elif etype == "SRP_APPLY_REJECTED":
        s["activity"]["srp"]["apply_rejected"] += 1
    elif etype == "SRP_APPLY_CLOSED":
        s["activity"]["srp"]["apply_closed"] += 1
    elif etype in ("SRP_TEST_COMMAND_STARTED", "SRP_TEST_COMMAND_COMPLETED"):
        pass
    elif etype == "SRP_FINAL_CONFIRMATION_VERIFIED":
        s["activity"]["srp"]["final_confirmations_verified"] += 1
    elif etype == "SRP_PROTECTED_BASE_VERIFIED":
        s["activity"]["srp"]["protected_base_verified"] += 1
    elif etype == "SRP_SELF_EDIT_STARTED":
        s["activity"]["srp"]["self_edit_started"] += 1
    elif etype == "SRP_SELF_EDIT_RECEIPT_RECORDED":
        s["activity"]["srp"]["self_edit_completed"] += 1
    elif etype in ("SRP_SELF_EDIT_AUTHORIZATION_REJECTED", "SRP_FINAL_CONFIRMATION_REJECTED", "SRP_PROTECTED_BASE_REJECTED"):
        s["activity"]["srp"]["self_edit_rejected"] += 1
    elif etype == "SRP_SELF_EDIT_LOCKDOWN":
        s["activity"]["srp"]["self_edit_lockdowns"] += 1
    elif etype == "SRP_SELF_EDIT_ROLLBACK_COMPLETED":
        s["activity"]["srp"]["self_edit_rollbacks"] += 1
    elif etype.startswith("SRP_SELF_EDIT_") or etype.startswith("SRP_POST_MERGE_") or etype.startswith("SRP_FINAL_CONFIRMATION_") or etype.startswith("SRP_PROTECTED_BASE_"):
        pass
    elif etype == "SRP_EXTERNAL_TOOL_HANDOFF_CREATED":
        s["activity"]["srp"]["handoffs_created"] += 1
    elif etype == "SRP_MAINTENANCE_OUTCOME_RECORDED":
        s["activity"]["srp"]["outcomes_recorded"] += 1
    elif etype == "MAX_AUTO_RUN_REQUESTED":
        s["activity"]["max_auto"]["runs_requested"] += 1
        s["activity"]["max_auto"]["last_run_id"] = payload.get("run_id")
        s["activity"]["max_auto"]["last_state"] = "RUN_REQUESTED"
    elif etype == "MAX_AUTO_OBSERVATION_RECORDED":
        s["activity"]["max_auto"]["observations_recorded"] += 1
    elif etype == "MAX_AUTO_BUNDLE_CREATED":
        s["activity"]["max_auto"]["bundles_created"] += 1
        s["activity"]["max_auto"]["last_bundle_hash"] = payload.get("bundle_hash")
    elif etype == "MAX_AUTO_SCOPE_APPROVED":
        s["activity"]["max_auto"]["scope_approved"] += 1
    elif etype == "MAX_AUTO_SCOPE_REJECTED":
        s["activity"]["max_auto"]["scope_rejected"] += 1
    elif etype == "MAX_AUTO_WORKTREE_PREPARED":
        s["activity"]["max_auto"]["worktrees_prepared"] += 1
    elif etype == "MAX_AUTO_PATCH_COMPLETED":
        s["activity"]["max_auto"]["patches_completed"] += 1
    elif etype == "MAX_AUTO_TEST_COMPLETED":
        s["activity"]["max_auto"]["tests_completed"] += 1
    elif etype == "MAX_AUTO_LOCAL_COMMIT_CREATED":
        s["activity"]["max_auto"]["local_commits_created"] += 1
        s["activity"]["max_auto"]["last_commit_sha"] = payload.get("commit_sha")
    elif etype == "MAX_AUTO_LOCKDOWN_ENTERED":
        s["activity"]["max_auto"]["lockdowns"] += 1
    elif etype == "MAX_AUTO_RUN_COMPLETED":
        s["activity"]["max_auto"]["runs_completed"] += 1
        s["activity"]["max_auto"]["last_verdict"] = payload.get("verdict")
        s["activity"]["max_auto"]["last_state"] = "COMPLETED"
    elif etype == "MAX_AUTO_RUN_FAILED":
        s["activity"]["max_auto"]["runs_failed"] += 1
        s["activity"]["max_auto"]["last_state"] = "FAILED"
    elif etype == "MAX_AUTO_RUN_REFUSED":
        s["activity"]["max_auto"]["runs_refused"] += 1
        s["activity"]["max_auto"]["last_state"] = "REFUSED"
    elif etype == "SRP_REPAIR_PROPOSED":
        if payload.get("bundle_id") is None:
            s["activity"]["srp"]["proposals"] += 1
        s["goals"]["pending_tasks"] = _push(
            s["goals"]["pending_tasks"],
            {
                "event_id": eid,
                "ref": payload.get("proposal_id") or payload.get("bundle_id"),
                "bundle_hash": payload.get("bundle_hash"),
                "status": payload.get("status", "PROPOSED"),
                "signature_required": payload.get("signature_required", True),
            },
            PENDING_META_MAX,
        )
    elif etype == "GAP_DETECTED":
        s["goals"]["gaps"] = _push(
            s["goals"]["gaps"], {"event_id": eid, "ref": payload.get("gap_id")}, PENDING_META_MAX
        )
    elif etype == "TASK_PROPOSED":
        s["activity"]["srp"]["proposals"] += 1
        s["goals"]["pending_tasks"] = _push(
            s["goals"]["pending_tasks"],
            {"event_id": eid, "ref": payload.get("proposal_id"), "bundle_hash": payload.get("bundle_hash")},
            PENDING_META_MAX,
        )
    elif etype == "CHANGE_APPROVED":
        pass  # SRP (Track 16) consumes these; world state only witnesses them
    elif etype == "EVENTS_DROPPED":
        s["environment"]["health"]["events_dropped"] += int(payload.get("total", 0))
    elif etype == "HANDLER_FAILED":
        s["environment"]["health"]["handler_failures"] += 1
    else:
        # Future registry additions stay deterministic: counted, never crashed on.
        counts = s["meta"]["unhandled_types"]
        counts[etype] = counts.get(etype, 0) + 1

    s["meta"]["last_seq"] = event["seq"]
    s["meta"]["events_applied"] += 1
    return s


def apply_many(state: Mapping[str, Any], events) -> Dict[str, Any]:
    s: Dict[str, Any] = state if isinstance(state, dict) else json.loads(json.dumps(state))
    for event in events:
        s = apply(s, event)
    return s


def state_hash(state: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_dumps(state)).hexdigest()


# ---------------------------------------------------------------------------
# Snapshots (boot = nearest snapshot + tail replay)
# ---------------------------------------------------------------------------


def write_snapshot(state: Mapping[str, Any], directory: Path) -> Path:
    """Atomic snapshot write, named by last applied seq."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    seq = state["meta"]["last_seq"]
    record = {"state": state, "state_hash": state_hash(state), "last_seq": seq}
    path = directory / f"snapshot-{seq:012d}.json"
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return path


def load_latest_snapshot(directory: Path):
    """Return (state, last_seq) from the newest valid snapshot, or (None, -1)."""
    directory = Path(directory)
    if not directory.exists():
        return None, -1
    for path in sorted(directory.glob("snapshot-*.json"), reverse=True):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            if state_hash(record["state"]) == record["state_hash"]:
                return record["state"], int(record["last_seq"])
        except (json.JSONDecodeError, KeyError, OSError):
            continue  # corrupt snapshot is skipped, not trusted
    return None, -1


__all__ = [
    "initial_state",
    "apply",
    "apply_many",
    "state_hash",
    "write_snapshot",
    "load_latest_snapshot",
]
