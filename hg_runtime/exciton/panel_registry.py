"""EXCITON Phase 0 panel registry — the 19 allowed status panels.

Each panel declares its data source, safe fields, hidden fields, and degraded behavior.
The registry is the single source of truth for ``REQUIRED_PANELS`` (presence checks) and
``FORBIDDEN_FIELDS`` (secret-exposure scrub). EXCITON displays only these panels and never
exposes a forbidden field.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PanelContract:
    panel_id: str
    title: str
    source: str
    safe_fields: tuple[str, ...]
    hidden_fields: tuple[str, ...]
    allowed_controls: tuple[str, ...]
    forbidden_controls: tuple[str, ...]
    degraded_reason: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "panel_id": self.panel_id,
            "title": self.title,
            "source": self.source,
            "safe_fields": list(self.safe_fields),
            "hidden_fields": list(self.hidden_fields),
            "allowed_controls": list(self.allowed_controls),
            "forbidden_controls": list(self.forbidden_controls),
            "degraded_reason": self.degraded_reason,
        }


# Controls every panel forbids (the dangerous set). Centralised here for the contracts.
_FORBIDDEN = (
    "publish_social",
    "send_email",
    "create_account",
    "login_form_submit",
    "mutate_memory",
    "mutate_source",
    "push_github_anchor",
    "delete_proof_bundle",
    "start_oea",
    "start_ter",
    "apply_srp",
    "enable_live_mic",
    "enable_playback",
    "start_soak",
    "start_autonomous_loop",
)

_READ = ("refresh_status", "open_proof_link", "copy_safe_summary", "request_proof_recheck")


PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract("OverviewPanel", "Overview", "status_aggregator",
                  ("identity", "boot_id", "run_id", "overall_verdict", "dangerous_actions_disabled"),
                  (), _READ, _FORBIDDEN, "identity unknown"),
    PanelContract("TemporalPanel", "Temporal (CHRONO)", "chrono",
                  ("current_time", "chrono_ref", "lock_state", "boot_epoch"),
                  (), _READ, _FORBIDDEN, "CHRONO unavailable"),
    PanelContract("WakeRefreshPanel", "Wake / Refresh (WRR)", "wrr",
                  ("wake_status", "last_reconcile"), ("internal_scratch",),
                  _READ, _FORBIDDEN, "WRR unavailable"),
    PanelContract("ExternalAnchorPanel", "External + Signed Anchor", "anchor",
                  ("anchor_present", "signed_status", "witness_ref"),
                  ("private_key", "credentials", "anchor_seed"),
                  _READ, _FORBIDDEN, "anchor unavailable"),
    PanelContract("WitnessJournalPanel", "Witness Journal (EWJ)", "ewj",
                  ("latest_event_meta", "chain_status", "chain_length"),
                  ("raw_private_payload",), _READ, _FORBIDDEN, "EWJ unavailable"),
    PanelContract("SelfMirrorPanel", "Self Mirror", "self_mirror",
                  ("summary", "continuity_status"),
                  ("raw_memory", "chain_of_thought"),
                  _READ + ("request_self_mirror_query",), _FORBIDDEN, "self mirror unavailable"),
    PanelContract("WillPanel", "WILL", "will",
                  ("summary", "advisory_hypotheses_count"),
                  ("private_deliberation",), _READ, _FORBIDDEN, "WILL unavailable"),
    PanelContract("TrustBoundaryPanel", "Trust Boundary", "trust_boundary",
                  ("status", "quarantine_count"), ("raw_quarantined_content",),
                  _READ, _FORBIDDEN, "trust boundary unavailable"),
    PanelContract("PowerBoundaryPanel", "Power Boundary (OPB/IPB)", "power_boundary",
                  ("opb_state", "ipb_state", "silence_state", "mission_state", "resource_state"),
                  (), _READ, _FORBIDDEN, "power boundaries unavailable"),
    PanelContract("StorageProofPanel", "Storage / Proof", "storage",
                  ("storage_verdict", "proof_count"), ("secrets", "dumps"),
                  _READ, _FORBIDDEN, "storage status unavailable"),
    PanelContract("ProviderPanel", "Provider / OpenVINO", "provider",
                  ("provider_status", "openvino_present", "cloud_disabled"),
                  ("api_keys",), _READ, _FORBIDDEN, "provider unavailable"),
    PanelContract("ToolCapabilityPanel", "Tool Capability", "tool_capability",
                  ("capabilities", "dangerous_actions_disabled"), ("secrets",),
                  _READ, _FORBIDDEN, "tool manifest unavailable"),
    PanelContract("OrganPanel", "Organs", "organ",
                  ("organ_ids", "heartbeats", "states"), (),
                  _READ, _FORBIDDEN, "organ manifest unavailable"),
    PanelContract("AudioPanel", "Audio I/O", "audio",
                  ("capture_mode", "stt_verdict", "tts_verdict", "live_mic_enabled", "playback_enabled"),
                  ("raw_audio", "wav_bytes"), _READ, _FORBIDDEN, "audio deps missing"),
    PanelContract("WeatherVoicePanel", "Weather Voice", "weather_voice",
                  ("source", "retrieved_time", "artifact_hash", "char_count"),
                  ("wav_bytes", "raw_audio_path"), _READ, _FORBIDDEN, "no weather-voice artifact"),
    PanelContract("ProofBundlePanel", "Proof Bundles", "proof_index",
                  ("stage_a", "stage_b", "stage_c", "bundles"), ("secrets",),
                  _READ, _FORBIDDEN, "no proof bundles"),
    PanelContract("QueuePanel", "Queues", "queue",
                  ("outstanding_requests",), ("secrets",),
                  _READ + ("request_anchor_queue_review",), _FORBIDDEN, "queue unavailable"),
    PanelContract("StopPanicPanel", "Stop / Panic", "control_boundary",
                  ("stop_available", "panic_available", "stop_state"), (),
                  ("stop_agent", "panic_stop"), _FORBIDDEN, "control boundary unavailable"),
    PanelContract("OperatorNotesPanel", "Operator Notes", "operator_notes",
                  ("notes",), (), ("add_operator_note",), _FORBIDDEN, "notes unavailable"),
)

# Phase 1 — social soak panels (8 additional; Phase 0 REQUIRED_PANELS unchanged at 19).
_SOCIAL_READ = ("refresh_social_status", "run_social_read_fixture", "run_social_read_live")
_SOCIAL_DRAFT = ("generate_social_draft", "queue_social_draft", "deny_social_draft")
_SOCIAL_PUBLISH = ("approve_social_publish",)  # operator-only; never direct publish
_SOAK_CTL = ("stop_soak", "panic_stop")

PHASE_1_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract("SocialStatusPanel", "Social Status", "social_capability",
                  ("credential_status", "live_read_enabled", "live_publish_enabled", "max_posts"),
                  ("token", "api_key", "credentials"),
                  _SOCIAL_READ, _FORBIDDEN, "social capability unavailable"),
    PanelContract("SocialReadPanel", "Social Read", "social_read",
                  ("surface", "items_count", "trust_disposition", "last_read_at"),
                  ("raw_cookie", "session_token"),
                  _SOCIAL_READ, _FORBIDDEN, "social read unavailable"),
    PanelContract("SocialDraftPanel", "Social Draft", "social_draft",
                  ("draft_id", "body_preview", "confidence", "trust_ok", "opb_ok"),
                  ("token",),
                  _SOCIAL_DRAFT, _FORBIDDEN, "no draft"),
    PanelContract("SocialApprovalQueuePanel", "Social Approval Queue", "social_queue",
                  ("queued_count", "pending_drafts", "operator_approval_required"),
                  (),
                  _SOCIAL_DRAFT + ("approve_social_publish", "deny_social_draft"),
                  _FORBIDDEN, "queue empty"),
    PanelContract("SocialPublishReceiptPanel", "Social Publish Receipts", "social_receipts",
                  ("receipt_count", "last_decision", "last_receipt_id"),
                  ("token", "secret"),
                  _READ, _FORBIDDEN, "no receipts"),
    PanelContract("SoakSupervisorPanel", "Soak Supervisor", "bounded_soak",
                  ("supervisor_state", "duration_minutes", "elapsed_minutes", "verdict"),
                  (),
                  _SOAK_CTL + ("refresh_status",), _FORBIDDEN, "soak supervisor unavailable"),
    PanelContract("SoakTaskPanel", "Soak Tasks", "soak_tasks",
                  ("task_kinds", "tasks_completed", "tasks_remaining"),
                  (),
                  _READ + _SOAK_CTL, _FORBIDDEN, "no soak tasks"),
    PanelContract("SoakTimelinePanel", "Soak Timeline", "soak_timeline",
                  ("events", "ewj_refs", "rate_limit_status"),
                  (),
                  _READ, _FORBIDDEN, "no soak timeline"),
)

PHASE_1_REQUIRED_PANELS: tuple[str, ...] = tuple(c.panel_id for c in PHASE_1_PANEL_CONTRACTS)

_WATCH_READ = ("refresh_status", "open_proof_link", "copy_safe_summary", "request_proof_recheck")
_WATCH_CONFIRM = ("confirm_publish_after_observation",)

PHASE_2_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract(
        "LiveActivityPanel", "Live Activity Trace", "live_activity",
        (
            "current_loop_state", "current_task", "current_provider", "model_id",
            "trust_boundary_result", "permit_decision", "last_output_summary",
            "last_receipt_hash", "observer_verdict", "data_tier",
        ),
        ("chain_of_thought", "raw_prompt", "token", "secret"),
        _WATCH_READ, _FORBIDDEN, "no live activity",
    ),
    PanelContract(
        "SoakWatchtowerPanel", "Soak Watchtower", "soak_watchtower",
        (
            "run_id", "run_dir", "elapsed_minutes", "remaining_minutes", "current_phase",
            "publish_enabled", "operator_confirmation_required", "observer_verdict",
            "observer_heartbeat_age_seconds", "next_cycle_eta_seconds", "data_tier",
        ),
        ("token", "secret", "credentials"),
        _WATCH_READ + _WATCH_CONFIRM + _SOAK_CTL, _FORBIDDEN, "soak watchtower unavailable",
    ),
    PanelContract(
        "NightWatchPanel", "Night Watch", "night_watch",
        (
            "safe_to_step_away", "safe_blockers", "observer_verdict", "publish_enabled",
            "continuity_status", "stop_available", "panic_available", "data_tier",
        ),
        ("token", "secret"),
        _WATCH_READ + _WATCH_CONFIRM + _SOAK_CTL, _FORBIDDEN, "night watch unavailable",
    ),
)

PHASE_2_REQUIRED_PANELS: tuple[str, ...] = tuple(c.panel_id for c in PHASE_2_PANEL_CONTRACTS)

_REVIEW_CTL = ("approve_queue_item", "deny_queue_item", "enable_publish_approved_only")

PHASE_3_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract(
        "SocialReviewQueuePanel", "Social Review Queue", "social_review_queue",
        (
            "queued_count", "approved_count", "denied_count", "published_count",
            "live_publish_paused", "approved_only_mode", "unreviewed_publish_path",
            "legacy_incident_recorded", "items_summary",
        ),
        ("token", "secret", "credentials", "chain_of_thought"),
        _WATCH_READ + _REVIEW_CTL, _FORBIDDEN + ("approve_all", "direct_publish"),
        "review queue unavailable",
    ),
    PanelContract(
        "SocialDraftPreviewPanel", "Social Draft Preview", "social_review_queue",
        (
            "queue_item_id", "draft_id", "draft_hash", "sanitized_preview",
            "trust_boundary_verdict", "opb_verdict", "publish_eligible", "status",
        ),
        ("token", "secret", "chain_of_thought", "raw_prompt"),
        _WATCH_READ, _FORBIDDEN + ("approve_all", "direct_publish"),
        "no draft selected",
    ),
    PanelContract(
        "SocialApprovalDecisionPanel", "Social Approval Decision", "social_review_queue",
        (
            "selected_queue_item_id", "approve_available", "deny_available",
            "approve_all_available", "direct_publish_available", "live_publish_mode",
        ),
        ("token", "secret"),
        _REVIEW_CTL, _FORBIDDEN + ("approve_all", "direct_publish", "publish_social"),
        "decision panel idle",
    ),
)

PHASE_3_REQUIRED_PANELS: tuple[str, ...] = tuple(c.panel_id for c in PHASE_3_PANEL_CONTRACTS)

_INFERENCE_READ = ("refresh_status", "open_proof_link", "copy_safe_summary")

INFERENCE_WATCHTOWER_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract(
        "InferenceWatchtowerPanel",
        "Inference Watchtower",
        "openvino_watchtower",
        (
            "provider_status",
            "provider_mode",
            "openvino_present",
            "openvino_runtime_version",
            "model_id",
            "model_loaded",
            "device",
            "active_inference_count",
            "active_organ",
            "active_task",
            "elapsed_ms",
            "chunk_count",
            "token_count",
            "tokens_per_second",
            "queue_depths",
            "organ_activity_summary",
            "freshness_verdict",
            "freshness_age_ms",
            "request_count",
            "error_count",
            "rolling_latency_ms",
            "process_metrics",
            "gpu_metrics",
            "redaction_active",
            "raw_prompt_disabled",
            "hidden_cot_disabled",
            "safe_to_step_away",
            "data_tier",
            "performance_verdict",
            "replay_session_count",
            "last_incident_id",
            "current_blocker",
            "watchtower_standalone_path",
            "organ_trace_verdict",
        ),
        ("chain_of_thought", "raw_prompt", "raw_completion", "token", "secret", "api_key"),
        _INFERENCE_READ,
        _FORBIDDEN,
        "watchtower contact lost",
    ),
)

INFERENCE_WATCHTOWER_REQUIRED_PANELS: tuple[str, ...] = tuple(
    c.panel_id for c in INFERENCE_WATCHTOWER_PANEL_CONTRACTS
)

_CONSOLE_READ = ("refresh_status", "copy_safe_summary")

AGENT_ZERO_CONSOLE_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract(
        "AgentZeroConsolePanel", "Agent Zero Console", "agent_zero_console",
        ("chat_enabled", "status_synthesis", "context_grant_count", "proposed_action_count",
         "receipt_count", "chat_can_execute", "chat_can_send", "stale_source_count", "data_tier"),
        ("chain_of_thought", "raw_prompt", "secret"), _CONSOLE_READ, _FORBIDDEN,
        "console unavailable",
    ),
    PanelContract(
        "MessageCenterPanel", "Message Center", "message_center",
        ("message_count", "live_import_disabled", "live_send_disabled", "cargo_boundary", "data_tier"),
        ("chain_of_thought", "raw_prompt", "secret", "token"), _CONSOLE_READ, _FORBIDDEN,
        "message center unavailable",
    ),
)

AGENT_ZERO_CONSOLE_REQUIRED_PANELS: tuple[str, ...] = tuple(
    c.panel_id for c in AGENT_ZERO_CONSOLE_PANEL_CONTRACTS
)

_AGENT_ZERO_REVIEW_READ = ("refresh_status", "copy_safe_summary")

AGENT_ZERO_REVIEW_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract(
        "AgentZeroReviewQueuePanel", "Agent Zero Review Queue", "agent_zero_operator_review",
        (
            "run_id", "item_count", "items_summary", "queue_verdict", "freshness_status",
            "source_refs", "source_ref_count", "truth_state", "generated_at", "expires_at",
            "verdict", "data_tier", "direct_external_actions_allowed", "approve_available",
            "publish_available", "send_available",
        ),
        ("chain_of_thought", "raw_prompt", "secret", "token"),
        _AGENT_ZERO_REVIEW_READ,
        _FORBIDDEN + ("approve", "publish", "send", "reply_live", "comment_live"),
        "review queue unavailable",
    ),
    PanelContract(
        "AgentZeroTurnTracePanel", "Agent Zero Turn Trace", "agent_zero_turn_engine",
        (
            "run_id", "turn_receipt_ref", "observe_snapshot_ref", "capability_menu_ref",
            "reasoning_result_ref", "reasoning_failure_ref", "broker_decision_ref",
            "artifact_refs", "output_quality_ref", "replay_status", "freshness_status",
            "source_refs", "truth_state", "generated_at", "expires_at", "verdict", "data_tier",
        ),
        ("chain_of_thought", "raw_prompt", "secret", "token"),
        _AGENT_ZERO_REVIEW_READ,
        _FORBIDDEN,
        "turn trace unavailable",
    ),
    PanelContract(
        "AgentZeroArtifactQualityPanel", "Agent Zero Artifact Quality", "agent_zero_output_artifacts",
        (
            "run_id", "artifact_count", "artifacts_preview", "freshness_status", "source_refs",
            "source_ref_count", "truth_state", "generated_at", "expires_at", "verdict", "data_tier",
        ),
        ("chain_of_thought", "raw_prompt", "secret", "token"),
        _AGENT_ZERO_REVIEW_READ,
        _FORBIDDEN + ("approve", "publish", "send"),
        "artifact quality unavailable",
    ),
)

AGENT_ZERO_REVIEW_REQUIRED_PANELS: tuple[str, ...] = tuple(
    c.panel_id for c in AGENT_ZERO_REVIEW_PANEL_CONTRACTS
)

AGENT_ZERO_REHEARSAL_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract(
        "AgentZeroRehearsalMonitorPanel", "Agent Zero Rehearsal Monitor", "supervised_rehearsal",
        (
            "run_id", "lock_state", "turn_count", "last_heartbeat", "freshness_status",
            "stop_available", "panic_available", "last_turn_verdict", "artifact_count",
            "review_candidate_count", "run_status", "source_refs", "truth_state",
            "generated_at", "expires_at", "verdict", "data_tier",
            "direct_external_actions_allowed", "approve_available", "publish_available", "send_available",
        ),
        ("chain_of_thought", "raw_prompt", "secret", "token"),
        _AGENT_ZERO_REVIEW_READ,
        _FORBIDDEN + ("approve", "publish", "send"),
        "rehearsal monitor unavailable",
    ),
)

AGENT_ZERO_REHEARSAL_REQUIRED_PANELS: tuple[str, ...] = tuple(
    c.panel_id for c in AGENT_ZERO_REHEARSAL_PANEL_CONTRACTS
)

AGENT_ZERO_DRY_SOAK_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract(
        "AgentZeroDrySoakMonitorPanel", "Agent Zero Dry Soak Monitor", "dry_soak",
        (
            "run_id", "run_status", "turn_count", "elapsed_seconds", "lock_state",
            "stop_available", "panic_available", "last_heartbeat", "freshness_status",
            "provider_status", "live_read_status", "artifact_count", "review_queue_count",
            "duplicate_body_hash_rate", "resource_verdict", "failure_budget_verdict",
            "source_refs", "truth_state", "generated_at", "expires_at", "verdict",
            "direct_external_actions_allowed", "approve_available", "publish_available", "send_available",
        ),
        ("chain_of_thought", "raw_prompt", "secret", "token"),
        _AGENT_ZERO_REVIEW_READ,
        _FORBIDDEN + ("approve", "publish", "send"),
        "dry soak monitor unavailable",
    ),
)

AGENT_ZERO_DRY_SOAK_REQUIRED_PANELS: tuple[str, ...] = tuple(
    c.panel_id for c in AGENT_ZERO_DRY_SOAK_PANEL_CONTRACTS
)

AGENT_ZERO_DRY_AUTONOMOUS_LOOP_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract(
        "AgentZeroDryAutonomousLoopMonitorPanel", "Agent Zero Dry Autonomous Loop Monitor", "dry_autonomous_loop",
        (
            "run_id", "status", "iteration_count", "max_iterations", "elapsed_seconds", "max_duration_seconds",
            "lock_state", "stop_available", "panic_available", "last_heartbeat", "freshness_status",
            "provider_status", "live_read_status", "artifact_count", "review_queue_count",
            "failure_budget_status", "last_turn_verdict", "truth_state", "verdict",
            "direct_external_actions_allowed", "approve_available", "publish_available", "send_available",
        ),
        ("chain_of_thought", "raw_prompt", "secret", "token"),
        _AGENT_ZERO_REVIEW_READ,
        _FORBIDDEN + ("approve", "publish", "send"),
        "dry autonomous loop monitor unavailable",
    ),
)

AGENT_ZERO_DRY_AUTONOMOUS_LOOP_REQUIRED_PANELS: tuple[str, ...] = tuple(
    c.panel_id for c in AGENT_ZERO_DRY_AUTONOMOUS_LOOP_PANEL_CONTRACTS
)

AGENT_ZERO_EXTENDED_DRY_AUTONOMY_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract(
        "AgentZeroExtendedDryAutonomyMonitorPanel", "Agent Zero Extended Dry Autonomy Monitor", "extended_dry_autonomy",
        (
            "run_id", "status", "iteration_count", "max_iterations", "elapsed_seconds", "max_duration_seconds",
            "lock_state", "stop_available", "panic_available", "pause_state", "checkpoint_status",
            "last_heartbeat", "freshness_status", "provider_status", "live_read_status",
            "artifact_count", "review_queue_count", "duplication_status", "resource_status",
            "endurance_budget_status", "remote_anchor_status", "last_turn_verdict", "truth_state", "verdict",
            "direct_external_actions_allowed", "approve_available", "publish_available", "send_available",
        ),
        ("chain_of_thought", "raw_prompt", "secret", "token"),
        _AGENT_ZERO_REVIEW_READ,
        _FORBIDDEN + ("approve", "publish", "send"),
        "extended dry autonomy monitor unavailable",
    ),
)

AGENT_ZERO_EXTENDED_DRY_AUTONOMY_REQUIRED_PANELS: tuple[str, ...] = tuple(
    c.panel_id for c in AGENT_ZERO_EXTENDED_DRY_AUTONOMY_PANEL_CONTRACTS
)

AGENT_ZERO_PROVIDER_MONITOR_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract(
        "AgentZeroProviderMonitorPanel", "Agent Zero Provider Monitor", "live_provider",
        (
            "provider_kind", "provider_status", "provider_id", "model_id", "quant_id", "context_length",
            "backend", "device", "last_health_check", "last_health_receipt", "last_provider_receipt",
            "last_latency_ms", "json_validity", "schema_validity", "unavailable_reason", "freshness_status",
            "truth_state", "verdict", "direct_external_actions_allowed", "publish_available", "send_available",
        ),
        ("api_key", "secret", "token", "chain_of_thought", "raw_prompt"),
        _AGENT_ZERO_REVIEW_READ,
        _FORBIDDEN + ("approve", "publish", "send"),
        "provider monitor unavailable",
    ),
)

AGENT_ZERO_PROVIDER_MONITOR_REQUIRED_PANELS: tuple[str, ...] = tuple(
    c.panel_id for c in AGENT_ZERO_PROVIDER_MONITOR_PANEL_CONTRACTS
)

AGENT_ZERO_LIVE_READ_MONITOR_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract(
        "AgentZeroLiveReadMonitorPanel", "Agent Zero Live Read Monitor", "live_read_endurance",
        (
            "source_kind", "source_name", "credential_scope_status", "read_only_status",
            "write_scope_detected", "last_read_receipt", "item_count", "freshness",
            "source_refs_count", "data_tier", "fixture_label", "provider_status",
            "last_observe_snapshot_ref", "verdict", "truth_state",
            "direct_external_actions_allowed", "publish_available", "send_available",
        ),
        ("api_key", "secret", "token", "chain_of_thought", "raw_prompt"),
        _AGENT_ZERO_REVIEW_READ,
        _FORBIDDEN + ("approve", "publish", "send", "reply_live", "comment_live"),
        "live read monitor unavailable",
    ),
)

AGENT_ZERO_LIVE_READ_MONITOR_REQUIRED_PANELS: tuple[str, ...] = tuple(
    c.panel_id for c in AGENT_ZERO_LIVE_READ_MONITOR_PANEL_CONTRACTS
)

AGENT_ZERO_EXTERNAL_WRITE_AUTHORITY_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract(
        "AgentZeroExternalWriteAuthorityMonitorPanel",
        "Agent Zero External Write Authority Monitor",
        "external_write_authority",
        (
            "candidate_count", "pending_candidates", "refused_candidates", "dry_run_dispatches",
            "expired_candidates", "revoked_permits", "dry_run_only", "live_dispatch_allowed",
            "last_refusal_reason", "freshness", "verdict", "truth_state", "items",
            "direct_external_actions_allowed", "publish_available", "send_available",
            "reply_available", "comment_available", "browser_available", "live_write_buttons",
        ),
        ("api_key", "secret", "token", "chain_of_thought", "raw_prompt"),
        _AGENT_ZERO_REVIEW_READ,
        _FORBIDDEN + ("approve", "publish", "send", "reply_live", "comment_live", "dry_dispatch_live"),
        "external write authority monitor unavailable",
    ),
)

AGENT_ZERO_EXTERNAL_WRITE_AUTHORITY_REQUIRED_PANELS: tuple[str, ...] = tuple(
    c.panel_id for c in AGENT_ZERO_EXTERNAL_WRITE_AUTHORITY_PANEL_CONTRACTS
)

AGENT_ZERO_PHASE18_LIVE_SMOKE_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract(
        "AgentZeroPhase18LiveSmokeMonitorPanel",
        "Agent Zero Phase 18 Live Smoke Monitor",
        "phase18_live_smoke",
        (
            "live_scope_status", "platform", "action_type", "content_hash", "candidate_ref",
            "dry_permit_ref", "live_permit_ref", "operator_confirmation_ref", "dispatch_status",
            "external_side_effect_count", "platform_proof", "rollback_plan", "stop_panic_active",
            "dry_run_only_default", "exciton_is_approval", "live_write_buttons", "verdict", "truth_state",
            "direct_external_actions_allowed", "publish_available",
        ),
        ("api_key", "secret", "token", "chain_of_thought", "raw_prompt"),
        _AGENT_ZERO_REVIEW_READ,
        _FORBIDDEN + ("approve", "publish", "send", "dispatch_live", "live_write"),
        "phase 18 live smoke monitor unavailable",
    ),
)

AGENT_ZERO_PHASE18_LIVE_SMOKE_REQUIRED_PANELS: tuple[str, ...] = tuple(
    c.panel_id for c in AGENT_ZERO_PHASE18_LIVE_SMOKE_PANEL_CONTRACTS
)

AGENT_ZERO_PHASE19_INCIDENT_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract(
        "AgentZeroPhase19IncidentMonitorPanel",
        "Agent Zero External Action Audit / Incident Monitor",
        "phase19_incident_audit",
        (
            "phase18_live_proof_exists", "live_action_count", "ledger_entry_count",
            "platform_proof_status", "reverification_status", "rollback_plan_count",
            "incident_report_ref", "duplicate_dispatch_detected", "bypass_drill_passed",
            "freshness", "verdict", "truth_state", "exciton_is_approval", "live_rollback_buttons",
            "direct_external_actions_allowed", "publish_available",
        ),
        ("api_key", "secret", "token", "chain_of_thought", "raw_prompt"),
        _AGENT_ZERO_REVIEW_READ,
        _FORBIDDEN + ("approve", "publish", "send", "rollback_live", "dispatch_live"),
        "phase 19 incident monitor unavailable",
    ),
)

AGENT_ZERO_PHASE19_INCIDENT_REQUIRED_PANELS: tuple[str, ...] = tuple(
    c.panel_id for c in AGENT_ZERO_PHASE19_INCIDENT_PANEL_CONTRACTS
)

AGENT_ZERO_TASK_SELECTION_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract(
        "AgentZeroTaskSelectionMonitorPanel",
        "Agent Zero Task Selection Monitor",
        "task_selection",
        (
            "objective_universe_status", "universe_id", "allowed_scopes", "candidate_count",
            "selected_task", "refused_tasks", "deferred_tasks", "idle_reflection",
            "authority_boundary_ref", "broker_decision_refs", "task_receipt_refs",
            "freshness", "verdict", "external_action_autonomous_green", "policy_phase",
            "live_writes_allowed", "direct_external_actions_allowed", "publish_available",
            "live_write_buttons",
        ),
        ("api_key", "secret", "token", "chain_of_thought", "raw_prompt"),
        _AGENT_ZERO_REVIEW_READ,
        _FORBIDDEN + ("approve", "publish", "send", "reply_live", "comment_live", "dispatch_live", "live_write"),
        "task selection monitor unavailable",
    ),
)

AGENT_ZERO_TASK_SELECTION_REQUIRED_PANELS: tuple[str, ...] = tuple(
    c.panel_id for c in AGENT_ZERO_TASK_SELECTION_PANEL_CONTRACTS
)

AGENT_ZERO_HANDS_OFF_SESSION_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract(
        "AgentZeroHandsOffSessionMonitorPanel",
        "Agent Zero Hands-Off Session Monitor",
        "hands_off_session",
        (
            "session_id", "pid", "foreground_status", "scheduler_allowed", "daemon_allowed",
            "service_allowed", "cron_allowed", "fixed_turn_cap", "fixed_duration_cap",
            "turn_count", "selected_task_count", "idle_count", "last_selected_task",
            "last_task_receipt", "last_turn_receipt", "last_broker_decision",
            "heartbeat_freshness", "heartbeat_stale", "stop_status", "panic_status",
            "resource_budget", "failure_budget", "external_side_effect_count", "verdict",
            "external_action_autonomous_green", "policy_phase", "live_writes_allowed",
            "direct_external_actions_allowed", "publish_available", "live_write_buttons",
        ),
        ("api_key", "secret", "token", "chain_of_thought", "raw_prompt"),
        _AGENT_ZERO_REVIEW_READ,
        _FORBIDDEN + ("approve", "publish", "send", "reply_live", "comment_live", "dispatch_live", "live_write"),
        "hands-off session monitor unavailable",
    ),
)

AGENT_ZERO_HANDS_OFF_SESSION_REQUIRED_PANELS: tuple[str, ...] = tuple(
    c.panel_id for c in AGENT_ZERO_HANDS_OFF_SESSION_PANEL_CONTRACTS
)

AGENT_ZERO_GOVERNED_WORK_LOOP_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract(
        "AgentZeroGovernedWorkLoopMonitorPanel",
        "Agent Zero Governed Work Loop Monitor",
        "governed_work_loop",
        (
            "envelope_id", "allowed_work_scopes", "external_action_quota_ref", "live_dispatch_allowed",
            "selected_task", "work_item", "work_receipt", "broker_decision", "external_candidate_refs",
            "dry_dispatch_refs", "live_dispatch_refs", "refusal_reasons", "stop_status", "panic_status",
            "external_side_effect_count", "verdict", "external_action_autonomous_green", "dry_run_only",
            "exciton_is_approval", "policy_phase", "direct_external_actions_allowed", "publish_available",
            "live_write_buttons",
        ),
        ("api_key", "secret", "token", "chain_of_thought", "raw_prompt"),
        _AGENT_ZERO_REVIEW_READ,
        _FORBIDDEN + ("approve", "publish", "send", "reply_live", "comment_live", "dispatch_live", "live_write"),
        "governed work loop monitor unavailable",
    ),
)

AGENT_ZERO_GOVERNED_WORK_LOOP_REQUIRED_PANELS: tuple[str, ...] = tuple(
    c.panel_id for c in AGENT_ZERO_GOVERNED_WORK_LOOP_PANEL_CONTRACTS
)

AGENT_ZERO_OVERNIGHT_FIELD_RUN_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract(
        "AgentZeroOvernightFieldRunMonitorPanel",
        "Agent Zero Overnight Field Run Monitor",
        "overnight_field_run",
        (
            "field_run_id", "mode", "pid", "foreground_status", "started_at", "turn_count",
            "task_selection_count", "governed_work_count", "internal_work_count",
            "external_candidate_count", "dry_dispatch_count", "live_dispatch_count",
            "refusal_count", "idle_count", "last_selected_task", "last_work_item_ref",
            "last_turn_receipt_ref", "heartbeat_freshness", "checkpoint_freshness",
            "stop_status", "panic_status", "continuity_audit_status", "wake_report_status",
            "external_side_effect_count", "infrastructure_only", "overnight_green_eligible",
            "verdict", "live_action_buttons", "publish_available",
        ),
        ("api_key", "secret", "token", "chain_of_thought", "raw_prompt"),
        _AGENT_ZERO_REVIEW_READ,
        _FORBIDDEN + ("approve", "publish", "send", "reply_live", "comment_live", "dispatch_live", "live_write", "start_overnight"),
        "overnight field run monitor unavailable",
    ),
)

AGENT_ZERO_OVERNIGHT_FIELD_RUN_REQUIRED_PANELS: tuple[str, ...] = tuple(
    c.panel_id for c in AGENT_ZERO_OVERNIGHT_FIELD_RUN_PANEL_CONTRACTS
)

AGENT_ZERO_REAL_SOAK_LAUNCH_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract(
        "AgentZeroRealSoakLaunchMonitorPanel",
        "Agent Zero Real Soak Launch Monitor",
        "real_soak_launch",
        (
            "soak_id", "phase24_infrastructure_status", "field_run_status", "moltbook_envelope_status",
            "live_posts_allowed", "max_live_posts", "live_posts_used", "envelope_valid_until",
            "platform_proof_status", "ledger_status", "stop_status", "panic_status",
            "external_side_effect_count", "preflight_ok", "dry_run_only_default", "verdict",
            "live_action_buttons",
        ),
        ("api_key", "secret", "token", "chain_of_thought", "raw_prompt"),
        _AGENT_ZERO_REVIEW_READ,
        _FORBIDDEN + ("approve", "publish", "send", "reply_live", "comment_live", "arm_envelope_live", "live_write"),
        "real soak launch monitor unavailable",
    ),
)

AGENT_ZERO_REAL_SOAK_LAUNCH_REQUIRED_PANELS: tuple[str, ...] = tuple(
    c.panel_id for c in AGENT_ZERO_REAL_SOAK_LAUNCH_PANEL_CONTRACTS
)

# Situational-awareness panels (7). Live-mode staleness/alerts can still go RED; the offline
# fixture snapshot evaluates them deterministically (fixture reference time) so it is never
# fake-green and never spuriously RED.
_SITUATIONAL_READ = ("refresh_status", "open_proof_link", "copy_safe_summary")

SITUATIONAL_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PanelContract(
        "DataFreshnessPanel", "Data Freshness", "situational_awareness",
        ("state", "age_seconds", "last_updated_ago", "approvals_disabled",
         "warning_threshold_seconds", "hard_stale_threshold_seconds", "data_updated_at", "data_tier"),
        (), _SITUATIONAL_READ, _FORBIDDEN, "freshness unavailable",
    ),
    PanelContract(
        "AwayDigestPanel", "While You Were Away", "situational_awareness",
        ("since", "drafts_queued", "pending_approvals", "posts_published", "incidents",
         "observer_gaps", "active_run_state", "pressure_to_approve", "data_tier"),
        ("chain_of_thought", "raw_prompt"), _SITUATIONAL_READ, _FORBIDDEN, "digest unavailable",
    ),
    PanelContract(
        "OperatorAlertsPanel", "Operator Alerts", "situational_awareness",
        ("alerts", "highest_severity", "can_approve", "pressure_to_approve", "data_tier"),
        (), _SITUATIONAL_READ, _FORBIDDEN, "alerts unavailable",
    ),
    PanelContract(
        "DecisionTimelinePanel", "Decision Timeline", "situational_awareness",
        ("event_count", "events", "data_tier"),
        ("chain_of_thought", "raw_prompt", "token", "secret"), _SITUATIONAL_READ, _FORBIDDEN,
        "timeline unavailable",
    ),
    PanelContract(
        "ChronoConfidencePanel", "CHRONO Time Confidence", "situational_awareness",
        ("time_uncertain", "confidence", "human_message", "chrono_ref", "data_tier"),
        (), _SITUATIONAL_READ, _FORBIDDEN, "chrono unavailable",
    ),
    PanelContract(
        "StopPanicSemanticsPanel", "Stop / Panic Semantics", "situational_awareness",
        ("stop_active", "panic_active", "stop_semantics", "panic_semantics", "data_tier"),
        (), _SITUATIONAL_READ + ("stop_agent", "panic_stop"), _FORBIDDEN, "stop/panic unavailable",
    ),
    PanelContract(
        "UIStateModelPanel", "UI State Model", "situational_awareness",
        ("cockpit_home", "states", "data_tier"),
        (), _SITUATIONAL_READ, _FORBIDDEN, "ui state unavailable",
    ),
)

SITUATIONAL_REQUIRED_PANELS: tuple[str, ...] = tuple(c.panel_id for c in SITUATIONAL_PANEL_CONTRACTS)

ALL_PANEL_CONTRACTS: tuple[PanelContract, ...] = (
    PANEL_CONTRACTS
    + PHASE_1_PANEL_CONTRACTS
    + PHASE_2_PANEL_CONTRACTS
    + PHASE_3_PANEL_CONTRACTS
    + INFERENCE_WATCHTOWER_PANEL_CONTRACTS
    + AGENT_ZERO_CONSOLE_PANEL_CONTRACTS
    + AGENT_ZERO_REVIEW_PANEL_CONTRACTS
    + AGENT_ZERO_REHEARSAL_PANEL_CONTRACTS
    + AGENT_ZERO_DRY_SOAK_PANEL_CONTRACTS
    + AGENT_ZERO_DRY_AUTONOMOUS_LOOP_PANEL_CONTRACTS
    + AGENT_ZERO_EXTENDED_DRY_AUTONOMY_PANEL_CONTRACTS
    + AGENT_ZERO_PROVIDER_MONITOR_PANEL_CONTRACTS
    + AGENT_ZERO_LIVE_READ_MONITOR_PANEL_CONTRACTS
    + AGENT_ZERO_EXTERNAL_WRITE_AUTHORITY_PANEL_CONTRACTS
    + AGENT_ZERO_PHASE18_LIVE_SMOKE_PANEL_CONTRACTS
    + AGENT_ZERO_PHASE19_INCIDENT_PANEL_CONTRACTS
    + AGENT_ZERO_TASK_SELECTION_PANEL_CONTRACTS
    + AGENT_ZERO_HANDS_OFF_SESSION_PANEL_CONTRACTS
    + AGENT_ZERO_GOVERNED_WORK_LOOP_PANEL_CONTRACTS
    + AGENT_ZERO_OVERNIGHT_FIELD_RUN_PANEL_CONTRACTS
    + AGENT_ZERO_REAL_SOAK_LAUNCH_PANEL_CONTRACTS
    + SITUATIONAL_PANEL_CONTRACTS
)

REQUIRED_PANELS: tuple[str, ...] = tuple(c.panel_id for c in PANEL_CONTRACTS)

CONTRACT_BY_ID: dict[str, PanelContract] = {c.panel_id: c for c in ALL_PANEL_CONTRACTS}

# Forbidden field name fragments — no panel field key or value path may carry these.
FORBIDDEN_FIELDS: frozenset[str] = frozenset(
    {
        "token",
        "api_key",
        "apikey",
        "secret",
        "password",
        "passwd",
        "private_key",
        "privatekey",
        "ssh_key",
        "ssh_private",
        "signing_key",
        "signing_private",
        "anchor_seed",
        "anchor_private",
        "cookie",
        "session_token",
        "raw_memory",
        "raw_session",
        "raw_cookie",
        "chain_of_thought",
        "cot",
        "wav_bytes",
        "raw_audio",
        "credentials",
        "bearer",
    }
)


def missing_required_panels(panel_ids: list[str] | tuple[str, ...]) -> list[str]:
    present = set(panel_ids)
    return [p for p in REQUIRED_PANELS if p not in present]


# Exact field-key allowlist: telemetry/flag names that contain a forbidden *substring* but are
# provably not secrets (counters, throughput metrics, and the hidden-CoT *disabled* safety flag).
# Exact-match only — a real secret-bearing key (api_token, access_token, auth_cot_key, ...) is still
# flagged. This removes blunt false positives without weakening secret detection.
SAFE_FIELD_KEYS: frozenset[str] = frozenset(
    {
        "token_count",
        "tokens_per_second",
        "prompt_token_count",
        "completion_token_count",
        "hidden_cot_disabled",
    }
)


def field_key_is_forbidden(key: str) -> bool:
    low = key.lower()
    if low in SAFE_FIELD_KEYS:
        return False
    return any(frag in low for frag in FORBIDDEN_FIELDS)


def scrub_fields(fields: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Drop any field whose key matches a forbidden fragment. Returns (clean, removed)."""
    clean: dict[str, Any] = {}
    removed: list[str] = []
    for k, v in fields.items():
        if field_key_is_forbidden(k):
            removed.append(k)
            continue
        clean[k] = v
    return clean, removed


__all__ = [
    "AGENT_ZERO_CONSOLE_PANEL_CONTRACTS",
    "AGENT_ZERO_CONSOLE_REQUIRED_PANELS",
    "AGENT_ZERO_DRY_AUTONOMOUS_LOOP_PANEL_CONTRACTS",
    "AGENT_ZERO_DRY_AUTONOMOUS_LOOP_REQUIRED_PANELS",
    "AGENT_ZERO_DRY_SOAK_PANEL_CONTRACTS",
    "AGENT_ZERO_DRY_SOAK_REQUIRED_PANELS",
    "AGENT_ZERO_REHEARSAL_PANEL_CONTRACTS",
    "AGENT_ZERO_REHEARSAL_REQUIRED_PANELS",
    "AGENT_ZERO_REVIEW_PANEL_CONTRACTS",
    "AGENT_ZERO_REVIEW_REQUIRED_PANELS",
    "ALL_PANEL_CONTRACTS",
    "CONTRACT_BY_ID",
    "FORBIDDEN_FIELDS",
    "INFERENCE_WATCHTOWER_PANEL_CONTRACTS",
    "INFERENCE_WATCHTOWER_REQUIRED_PANELS",
    "PANEL_CONTRACTS",
    "PHASE_1_PANEL_CONTRACTS",
    "PHASE_1_REQUIRED_PANELS",
    "PHASE_2_PANEL_CONTRACTS",
    "PHASE_2_REQUIRED_PANELS",
    "PHASE_3_PANEL_CONTRACTS",
    "PHASE_3_REQUIRED_PANELS",
    "SITUATIONAL_PANEL_CONTRACTS",
    "SITUATIONAL_REQUIRED_PANELS",
    "REQUIRED_PANELS",
    "PanelContract",
    "field_key_is_forbidden",
    "missing_required_panels",
    "scrub_fields",
]
