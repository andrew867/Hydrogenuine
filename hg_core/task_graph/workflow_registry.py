"""
Primary workflow registry and acceptance checks.

Single authoritative registry of primary workflows with declarations (purpose,
success criteria, acceptance checks, readiness). Baseline acceptance check runner
and readiness enforcement. See hg_core/task_graph/docs/primary_workflow_registry_spec.md.
"""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

WORKFLOW_REGISTRY_PATH = "memory/automation/workflow_registry.json"

# Primary workflow IDs per spec (4claw, moltbook, moltstack, knowledge-task-45min)
PRIMARY_WORKFLOW_IDS = [
    "social-media",
    "fourclaw-auto-post",
    "moltbook-auto-post",
    "moltstack-draft",
    "knowledge-research-auto",
]

DECLARED_WORKFLOW_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "social-media": {
        "workflow_id": "social-media",
        "display_name": "Unified Social Media Cadence",
        "category": "engage",
        "coordination_style": "end_to_end",
        "side_effects": "external_write",
        "success_criteria": [
            "One wake chooses the next social surface or explicitly chooses no social action",
            "Trace exists and links chooser, dispatch, notification, and sleep outputs",
        ],
        "acceptance_checks": [
            {"id": "trace_exists", "description": "Trace exists and links outputs", "severity": "must", "evaluation": "machine"},
            {"id": "safety_gate", "description": "Safety gate executed for external actions", "severity": "must", "evaluation": "machine"},
        ],
        "destinations": ["multi_social"],
        "degraded_mode_rules": ["draft_only", "skip_external_write", "sleep_longer"],
        "idempotency": {"required": False, "strategy": "delegated_child_workflow"},
        "budgets": {"per_run": {"tokens": 60000}, "per_day": {"tokens": 250000}},
        "strict_blacklist_categories": ["destructive_write", "unknown_destination"],
        "approvals_policy": {"mode": "human_review_before_write", "strict_blacklist_categories": ["destructive_write", "unknown_destination"]},
        "sla_targets": {"reliability_target": 0.95, "duplicate_side_effects": "zero"},
        "retention_class": "medium",
        "readiness": "supervised",
    },
    "fourclaw-auto-post": {
        "workflow_id": "fourclaw-auto-post",
        "display_name": "4claw Auto Post",
        "category": "publish",
        "coordination_style": "end_to_end",
        "side_effects": "external_write",
        "success_criteria": [
            "Post draft generated and approval recorded before external submission",
            "Trace exists and links outputs",
        ],
        "acceptance_checks": [
            {"id": "trace_exists", "description": "Trace exists and links outputs", "severity": "must", "evaluation": "machine"},
            {"id": "safety_gate", "description": "Safety gate executed for external actions", "severity": "must", "evaluation": "machine"},
            {"id": "idempotency", "description": "Idempotency ledger updated for external actions", "severity": "must", "evaluation": "machine"},
        ],
        "destinations": ["fourclaw"],
        "degraded_mode_rules": ["draft_only", "skip_external_write"],
        "idempotency": {"required": True, "strategy": "goal_hash"},
        "budgets": {"per_run": {"tokens": 50000}, "per_day": {"tokens": 200000}},
        "strict_blacklist_categories": ["destructive_write", "unknown_destination"],
        "approvals_policy": {"mode": "human_review_before_write", "strict_blacklist_categories": ["destructive_write", "unknown_destination"]},
        "sla_targets": {"reliability_target": 0.95, "duplicate_side_effects": "zero"},
        "retention_class": "medium",
        "readiness": "supervised",
    },
    "fourclaw-engage": {
        "workflow_id": "fourclaw-engage",
        "display_name": "4claw Engage",
        "category": "engage",
        "coordination_style": "end_to_end",
        "side_effects": "external_write",
        "success_criteria": [
            "Reply draft generated and approval recorded before external submission",
            "Trace exists and links outputs",
        ],
        "acceptance_checks": [
            {"id": "trace_exists", "description": "Trace exists and links outputs", "severity": "must", "evaluation": "machine"},
            {"id": "safety_gate", "description": "Safety gate executed for external actions", "severity": "must", "evaluation": "machine"},
            {"id": "idempotency", "description": "Idempotency ledger updated for external actions", "severity": "must", "evaluation": "machine"},
        ],
        "destinations": ["fourclaw"],
        "degraded_mode_rules": ["draft_only", "skip_external_write"],
        "idempotency": {"required": True, "strategy": "thread_hash"},
        "budgets": {"per_run": {"tokens": 50000}, "per_day": {"tokens": 200000}},
        "strict_blacklist_categories": ["destructive_write", "unknown_destination"],
        "approvals_policy": {"mode": "human_review_before_write", "strict_blacklist_categories": ["destructive_write", "unknown_destination"]},
        "sla_targets": {"reliability_target": 0.95, "duplicate_side_effects": "zero"},
        "retention_class": "medium",
        "readiness": "supervised",
    },
    "moltbook-auto-post": {
        "workflow_id": "moltbook-auto-post",
        "display_name": "Moltbook Auto Post",
        "category": "publish",
        "coordination_style": "end_to_end",
        "side_effects": "external_write",
        "success_criteria": [
            "Post draft generated and approval recorded before external submission",
            "Trace exists and links outputs",
        ],
        "acceptance_checks": [
            {"id": "trace_exists", "description": "Trace exists and links outputs", "severity": "must", "evaluation": "machine"},
            {"id": "safety_gate", "description": "Safety gate executed for external actions", "severity": "must", "evaluation": "machine"},
            {"id": "idempotency", "description": "Idempotency ledger updated for external actions", "severity": "must", "evaluation": "machine"},
        ],
        "destinations": ["moltbook"],
        "degraded_mode_rules": ["draft_only", "skip_external_write"],
        "idempotency": {"required": True, "strategy": "topic_hash"},
        "budgets": {"per_run": {"tokens": 50000}, "per_day": {"tokens": 200000}},
        "strict_blacklist_categories": ["destructive_write", "unknown_destination"],
        "approvals_policy": {"mode": "human_review_before_write", "strict_blacklist_categories": ["destructive_write", "unknown_destination"]},
        "sla_targets": {"reliability_target": 0.95, "duplicate_side_effects": "zero"},
        "retention_class": "medium",
        "readiness": "supervised",
    },
    "moltbook-engage": {
        "workflow_id": "moltbook-engage",
        "display_name": "Moltbook Engage",
        "category": "engage",
        "coordination_style": "end_to_end",
        "side_effects": "external_write",
        "success_criteria": [
            "Reply draft generated and approval recorded before external submission",
            "Trace exists and links outputs",
        ],
        "acceptance_checks": [
            {"id": "trace_exists", "description": "Trace exists and links outputs", "severity": "must", "evaluation": "machine"},
            {"id": "safety_gate", "description": "Safety gate executed for external actions", "severity": "must", "evaluation": "machine"},
            {"id": "idempotency", "description": "Idempotency ledger updated for external actions", "severity": "must", "evaluation": "machine"},
        ],
        "destinations": ["moltbook"],
        "degraded_mode_rules": ["draft_only", "skip_external_write"],
        "idempotency": {"required": True, "strategy": "thread_hash"},
        "budgets": {"per_run": {"tokens": 50000}, "per_day": {"tokens": 200000}},
        "strict_blacklist_categories": ["destructive_write", "unknown_destination"],
        "approvals_policy": {"mode": "human_review_before_write", "strict_blacklist_categories": ["destructive_write", "unknown_destination"]},
        "sla_targets": {"reliability_target": 0.95, "duplicate_side_effects": "zero"},
        "retention_class": "medium",
        "readiness": "supervised",
    },
    "aichan-engage": {
        "workflow_id": "aichan-engage",
        "display_name": "Aichan Engage",
        "category": "engage",
        "coordination_style": "end_to_end",
        "side_effects": "external_write",
        "success_criteria": [
            "Reply draft generated and approval recorded before external submission",
            "Trace exists and links outputs",
        ],
        "acceptance_checks": [
            {"id": "trace_exists", "description": "Trace exists and links outputs", "severity": "must", "evaluation": "machine"},
            {"id": "safety_gate", "description": "Safety gate executed for external actions", "severity": "must", "evaluation": "machine"},
            {"id": "idempotency", "description": "Idempotency ledger updated for external actions", "severity": "must", "evaluation": "machine"},
        ],
        "destinations": ["aichan"],
        "degraded_mode_rules": ["draft_only", "skip_external_write"],
        "idempotency": {"required": True, "strategy": "thread_hash"},
        "budgets": {"per_run": {"tokens": 50000}, "per_day": {"tokens": 200000}},
        "strict_blacklist_categories": ["destructive_write", "unknown_destination"],
        "approvals_policy": {"mode": "human_review_before_write", "strict_blacklist_categories": ["destructive_write", "unknown_destination"]},
        "sla_targets": {"reliability_target": 0.95, "duplicate_side_effects": "zero"},
        "retention_class": "medium",
        "readiness": "supervised",
    },
    "agentchan-engage": {
        "workflow_id": "agentchan-engage",
        "display_name": "Agentchan Engage",
        "category": "engage",
        "coordination_style": "end_to_end",
        "side_effects": "external_write",
        "success_criteria": [
            "Reply draft generated and approval recorded before external submission",
            "Trace exists and links outputs",
        ],
        "acceptance_checks": [
            {"id": "trace_exists", "description": "Trace exists and links outputs", "severity": "must", "evaluation": "machine"},
            {"id": "safety_gate", "description": "Safety gate executed for external actions", "severity": "must", "evaluation": "machine"},
            {"id": "idempotency", "description": "Idempotency ledger updated for external actions", "severity": "must", "evaluation": "machine"},
        ],
        "destinations": ["agentchan"],
        "degraded_mode_rules": ["draft_only", "skip_external_write"],
        "idempotency": {"required": True, "strategy": "thread_hash"},
        "budgets": {"per_run": {"tokens": 50000}, "per_day": {"tokens": 200000}},
        "strict_blacklist_categories": ["destructive_write", "unknown_destination"],
        "approvals_policy": {"mode": "human_review_before_write", "strict_blacklist_categories": ["destructive_write", "unknown_destination"]},
        "sla_targets": {"reliability_target": 0.95, "duplicate_side_effects": "zero"},
        "retention_class": "medium",
        "readiness": "supervised",
    },
    "moltx-engage": {
        "workflow_id": "moltx-engage",
        "display_name": "Moltx Engage",
        "category": "engage",
        "coordination_style": "end_to_end",
        "side_effects": "external_write",
        "success_criteria": [
            "Reply draft generated and approval recorded before external submission",
            "Trace exists and links outputs",
        ],
        "acceptance_checks": [
            {"id": "trace_exists", "description": "Trace exists and links outputs", "severity": "must", "evaluation": "machine"},
            {"id": "safety_gate", "description": "Safety gate executed for external actions", "severity": "must", "evaluation": "machine"},
            {"id": "idempotency", "description": "Idempotency ledger updated for external actions", "severity": "must", "evaluation": "machine"},
        ],
        "destinations": ["moltx"],
        "degraded_mode_rules": ["draft_only", "skip_external_write"],
        "idempotency": {"required": True, "strategy": "thread_hash"},
        "budgets": {"per_run": {"tokens": 50000}, "per_day": {"tokens": 200000}},
        "strict_blacklist_categories": ["destructive_write", "unknown_destination"],
        "approvals_policy": {"mode": "human_review_before_write", "strict_blacklist_categories": ["destructive_write", "unknown_destination"]},
        "sla_targets": {"reliability_target": 0.95, "duplicate_side_effects": "zero"},
        "retention_class": "medium",
        "readiness": "supervised",
    },
    "moltstack-draft": {
        "workflow_id": "moltstack-draft",
        "display_name": "Moltstack Draft",
        "category": "publish",
        "coordination_style": "baton",
        "side_effects": "internal_write",
        "checkpoints": ["draft_ready"],
        "success_criteria": ["Draft written to queue", "Trace exists and links outputs"],
        "acceptance_checks": [
            {"id": "trace_exists", "description": "Trace exists and links outputs", "severity": "must", "evaluation": "machine"},
            {"id": "checkpoints", "description": "No missing required checkpoints", "severity": "must", "evaluation": "machine"},
        ],
        "destinations": ["queue"],
        "degraded_mode_rules": ["skip"],
        "idempotency": {"required": False, "strategy": "none"},
        "budgets": {"per_run": {"tokens": 30000}, "per_day": {"tokens": 100000}},
        "strict_blacklist_categories": [],
        "approvals_policy": {"mode": "default_approve", "strict_blacklist_categories": []},
        "sla_targets": {"reliability_target": 0.95, "duplicate_side_effects": "zero"},
        "retention_class": "medium",
        "readiness": "supervised",
    },
    "moltstack-publish": {
        "workflow_id": "moltstack-publish",
        "display_name": "Moltstack Publish",
        "category": "publish",
        "coordination_style": "baton",
        "side_effects": "external_write",
        "checkpoints": ["draft_ready", "publish_ready"],
        "success_criteria": ["Publish approval is recorded before external submission", "Trace exists and links outputs"],
        "acceptance_checks": [
            {"id": "trace_exists", "description": "Trace exists and links outputs", "severity": "must", "evaluation": "machine"},
            {"id": "checkpoints", "description": "No missing required checkpoints", "severity": "must", "evaluation": "machine"},
            {"id": "safety_gate", "description": "Safety gate executed for external actions", "severity": "must", "evaluation": "machine"},
        ],
        "destinations": ["moltstack"],
        "degraded_mode_rules": ["skip_external_write"],
        "idempotency": {"required": True, "strategy": "draft_hash"},
        "budgets": {"per_run": {"tokens": 50000}, "per_day": {"tokens": 150000}},
        "strict_blacklist_categories": ["destructive_write", "unknown_destination"],
        "approvals_policy": {"mode": "human_review_before_write", "strict_blacklist_categories": ["destructive_write", "unknown_destination"]},
        "sla_targets": {"reliability_target": 0.95, "duplicate_side_effects": "zero"},
        "retention_class": "medium",
        "readiness": "supervised",
    },
    "knowledge-research-auto": {
        "workflow_id": "knowledge-research-auto",
        "display_name": "Knowledge Research (45min task)",
        "category": "knowledge",
        "coordination_style": "end_to_end",
        "side_effects": "internal_write",
        "success_criteria": ["Topics researched and recorded", "Trace exists and links outputs"],
        "acceptance_checks": [
            {"id": "trace_exists", "description": "Trace exists and links outputs", "severity": "must", "evaluation": "machine"},
            {"id": "budget", "description": "Budget not exceeded or degraded/skip recorded", "severity": "must", "evaluation": "machine"},
        ],
        "destinations": ["knowledge_store"],
        "degraded_mode_rules": ["reduce_topics", "skip"],
        "idempotency": {"required": False, "strategy": "none"},
        "budgets": {"per_run": {"tokens": 100000}, "per_day": {"tokens": 300000}},
        "strict_blacklist_categories": [],
        "approvals_policy": {"mode": "default_approve", "strict_blacklist_categories": []},
        "sla_targets": {"reliability_target": 0.95, "duplicate_side_effects": "zero"},
        "retention_class": "long",
        "readiness": "supervised",
    },
    "knowledge-research-auto-v2": {
        "workflow_id": "knowledge-research-auto-v2",
        "display_name": "Knowledge Research v2 (record all news)",
        "category": "knowledge",
        "coordination_style": "end_to_end",
        "side_effects": "internal_write",
        "success_criteria": ["More topics per cycle, briefs and knowledge files written", "Dedupe by URL/title", "Trace exists and links outputs"],
        "acceptance_checks": [
            {"id": "trace_exists", "description": "Trace exists and links outputs", "severity": "must", "evaluation": "machine"},
            {"id": "budget", "description": "Budget not exceeded or degraded/skip recorded", "severity": "must", "evaluation": "machine"},
        ],
        "destinations": ["knowledge_store"],
        "degraded_mode_rules": ["reduce_topics", "skip"],
        "idempotency": {"required": False, "strategy": "none"},
        "budgets": {"per_run": {"tokens": 120000}, "per_day": {"tokens": 400000}},
        "strict_blacklist_categories": [],
        "approvals_policy": {"mode": "default_approve", "strict_blacklist_categories": []},
        "sla_targets": {"reliability_target": 0.95, "duplicate_side_effects": "zero"},
        "retention_class": "long",
        "readiness": "supervised",
    },
    "memory-maintenance": {
        "workflow_id": "memory-maintenance",
        "display_name": "Memory Maintenance",
        "category": "maintenance",
        "coordination_style": "end_to_end",
        "side_effects": "internal_write",
        "success_criteria": ["Memory promotion/pruning completes without data loss", "Trace exists and links outputs"],
        "acceptance_checks": [
            {"id": "trace_exists", "description": "Trace exists and links outputs", "severity": "must", "evaluation": "machine"},
            {"id": "budget", "description": "Budget not exceeded or degraded/skip recorded", "severity": "must", "evaluation": "machine"},
        ],
        "destinations": ["memory_store"],
        "degraded_mode_rules": ["skip_when_lock_present"],
        "idempotency": {"required": False, "strategy": "none"},
        "budgets": {"per_run": {"dispatch_attempts": 10}, "per_day": {"dispatch_attempts": 240}},
        "strict_blacklist_categories": [],
        "approvals_policy": {"mode": "default_approve", "strict_blacklist_categories": []},
        "sla_targets": {"reliability_target": 0.99, "duplicate_side_effects": "zero"},
        "retention_class": "long",
        "readiness": "supervised",
    },
    "overseer-monitor": {
        "workflow_id": "overseer-monitor",
        "display_name": "Overseer Monitor",
        "category": "maintenance",
        "coordination_style": "end_to_end",
        "side_effects": "internal_write",
        "success_criteria": ["PNG/PDF dashboards generated when data exists", "Trace exists and links outputs"],
        "acceptance_checks": [
            {"id": "trace_exists", "description": "Trace exists and links outputs", "severity": "must", "evaluation": "machine"},
            {"id": "budget", "description": "Budget not exceeded or degraded/skip recorded", "severity": "must", "evaluation": "machine"},
        ],
        "destinations": ["overseer_dashboard"],
        "degraded_mode_rules": ["emit_partial_dashboard", "skip_notification"],
        "idempotency": {"required": False, "strategy": "none"},
        "budgets": {"per_run": {"dispatch_attempts": 10}, "per_day": {"dispatch_attempts": 240}},
        "strict_blacklist_categories": [],
        "approvals_policy": {"mode": "default_approve", "strict_blacklist_categories": []},
        "sla_targets": {"reliability_target": 0.99, "duplicate_side_effects": "zero"},
        "retention_class": "medium",
        "readiness": "supervised",
    },
}


def _generic_acceptance_checks(*, external_write: bool, internal_write: bool = False) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = [
        {"id": "trace_exists", "description": "Trace exists and links outputs", "severity": "must", "evaluation": "machine"},
    ]
    if external_write:
        checks.extend(
            [
                {"id": "safety_gate", "description": "Safety gate executed for external actions", "severity": "must", "evaluation": "machine"},
                {"id": "idempotency", "description": "Idempotency ledger updated for external actions", "severity": "must", "evaluation": "machine"},
            ]
        )
    elif internal_write:
        checks.append(
            {"id": "budget", "description": "Budget not exceeded or degraded/skip recorded", "severity": "must", "evaluation": "machine"}
        )
    return checks


def _auto_declare_from_job_registry() -> None:
    from hg_core.job_registry import get_registry

    registry = get_registry()
    for workflow_id, info in registry.items():
        if workflow_id in DECLARED_WORKFLOW_DEFAULTS:
            continue
        platform = info.get("platform")
        mode = str(info.get("mode") or "").strip()
        if mode in {"auto-post", "publish"}:
            category = "publish"
        elif mode == "engage":
            category = "engage"
        elif mode == "research":
            category = "knowledge"
        else:
            category = "maintenance"

        external_write = mode in {"auto-post", "engage", "publish"}
        internal_write = mode in {"draft", "research", "maintenance", "utility"} or not external_write
        destinations = [platform] if isinstance(platform, str) and platform and platform != "dynamic" else []
        if not destinations and mode:
            destinations = [mode]

        DECLARED_WORKFLOW_DEFAULTS[workflow_id] = {
            "workflow_id": workflow_id,
            "display_name": workflow_id.replace("-", " ").title(),
            "category": category,
            "coordination_style": "baton" if mode == "draft" else "end_to_end",
            "side_effects": "external_write" if external_write else ("internal_write" if internal_write else "none"),
            "success_criteria": [
                "Trace exists and links outputs",
                "Approval recorded before external submission" if external_write else "Run completes without policy violations",
            ],
            "acceptance_checks": _generic_acceptance_checks(external_write=external_write, internal_write=internal_write),
            "destinations": destinations,
            "degraded_mode_rules": ["draft_only", "skip_external_write"] if external_write else ["skip"],
            "idempotency": {"required": external_write, "strategy": "goal_hash" if external_write else "none"},
            "budgets": {"per_run": {"dispatch_attempts": 10}, "per_day": {"dispatch_attempts": 240}},
            "strict_blacklist_categories": ["destructive_write", "unknown_destination"] if external_write else [],
            "approvals_policy": {
                "mode": "human_review_before_write" if external_write else "default_approve",
                "strict_blacklist_categories": ["destructive_write", "unknown_destination"] if external_write else [],
            },
            "sla_targets": {"reliability_target": 0.95, "duplicate_side_effects": "zero"},
            "retention_class": "medium",
            "readiness": "supervised",
        }


_auto_declare_from_job_registry()

POLICY_DEFAULTS: Dict[str, Any] = {
    "destinations": [],
    "degraded_mode_rules": [],
    "idempotency": {"required": False, "strategy": "none"},
    "budgets": {"per_run": {}, "per_day": {}},
    "strict_blacklist_categories": [],
}


def _get_workspace_root(workspace_root: Optional[Path] = None) -> Optional[Path]:
    try:
        from hg_lib.config import get_workspace_root as _get_root
        return workspace_root or _get_root()
    except Exception:
        return None


def get_primary_workflow_ids() -> List[str]:
    """Return the list of primary workflow IDs (4claw, moltbook, moltstack, knowledge-task-45min)."""
    return list(PRIMARY_WORKFLOW_IDS)


def get_declared_workflow_ids() -> List[str]:
    """Return all workflow IDs that should exist in the runtime registry."""
    return list(DECLARED_WORKFLOW_DEFAULTS.keys())


def load_workflow_registry(workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load the workflow registry from disk. Returns dict workflow_id -> declaration.

    Behavior:
    - prefer `memory/automation/workflow_registry.json`
    - bootstrap that file when missing/invalid
    - apply policy defaults to declarations and log missing sections
    """
    root = _get_workspace_root(workspace_root)
    if not root:
        logger.warning("Workspace root unavailable; using in-memory workflow bootstrap")
        return _build_bootstrap_registry()
    registry_file = root / WORKFLOW_REGISTRY_PATH
    should_write = False

    data: Dict[str, Any]
    if not registry_file.exists():
        logger.warning("Workflow registry not found: %s; bootstrapping defaults", registry_file)
        data = _build_bootstrap_registry()
        should_write = True
    else:
        try:
            with open(registry_file, encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                data = loaded
            else:
                logger.warning(
                    "Workflow registry at %s is not a JSON object; bootstrapping defaults",
                    registry_file,
                )
                data = _build_bootstrap_registry()
                should_write = True
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                "Could not load workflow_registry %s: %s; bootstrapping defaults",
                registry_file,
                e,
            )
            data = _build_bootstrap_registry()
            should_write = True

    out: Dict[str, Any] = {}
    for wid, value in data.items():
        if not isinstance(value, dict):
            logger.warning(
                "Workflow declaration for %s is not an object; replacing with bootstrap defaults",
                wid,
            )
            out[str(wid)] = _minimal_declaration(str(wid))
            should_write = True
            continue
        out[str(wid)] = dict(value)

    for wid in get_declared_workflow_ids():
        if wid not in out:
            out[wid] = deepcopy(DECLARED_WORKFLOW_DEFAULTS.get(wid, _minimal_declaration(wid)))
            should_write = True

    if _ensure_policy_defaults(out):
        should_write = True

    if should_write:
        _write_registry_file(registry_file, out)
    return out


def _write_registry_file(registry_file: Path, data: Dict[str, Any]) -> None:
    try:
        registry_file.parent.mkdir(parents=True, exist_ok=True)
        registry_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError as e:
        logger.warning("Could not persist workflow registry bootstrap %s: %s", registry_file, e)


def _build_bootstrap_registry() -> Dict[str, Any]:
    return {wid: deepcopy(DECLARED_WORKFLOW_DEFAULTS.get(wid, _minimal_declaration(wid))) for wid in get_declared_workflow_ids()}


def _ensure_policy_defaults(registry: Dict[str, Any]) -> bool:
    changed = False
    for wid, decl in registry.items():
        if not isinstance(decl, dict):
            continue
        missing_fields: List[str] = []
        for field, default in POLICY_DEFAULTS.items():
            if field not in decl:
                decl[field] = deepcopy(default)
                missing_fields.append(field)
                changed = True
        approvals = decl.get("approvals_policy")
        if not isinstance(approvals, dict):
            decl["approvals_policy"] = {
                "mode": "default_approve",
                "strict_blacklist_categories": [],
            }
            approvals = decl["approvals_policy"]
            missing_fields.append("approvals_policy")
            changed = True
        if "strict_blacklist_categories" not in approvals:
            approvals["strict_blacklist_categories"] = list(
                decl.get("strict_blacklist_categories") or []
            )
            missing_fields.append("approvals_policy.strict_blacklist_categories")
            changed = True
        if decl.get("side_effects") == "external_write" and approvals.get("mode") != "human_review_before_write":
            approvals["mode"] = "human_review_before_write"
            missing_fields.append("approvals_policy.mode")
            changed = True
        if decl.get("side_effects") == "external_write" and not approvals.get("strict_blacklist_categories"):
            approvals["strict_blacklist_categories"] = list(
                decl.get("strict_blacklist_categories") or ["destructive_write", "unknown_destination"]
            )
            missing_fields.append("approvals_policy.strict_blacklist_categories")
            changed = True
        if missing_fields:
            logger.warning(
                "Workflow %s missing policy fields: %s; defaults applied",
                wid,
                ", ".join(sorted(set(missing_fields))),
            )
    return changed


def _minimal_declaration(workflow_id: str) -> Dict[str, Any]:
    """Minimal declaration so required fields exist when registry file is missing."""
    return {
        "workflow_id": workflow_id,
        "display_name": workflow_id,
        "category": "maintenance",
        "coordination_style": "end_to_end",
        "side_effects": "none",
        "success_criteria": [],
        "acceptance_checks": [
            {"id": "trace_exists", "description": "Trace exists and links outputs", "severity": "must", "evaluation": "machine"},
        ],
        "sla_targets": {"reliability_target": 0.95, "duplicate_side_effects": "zero"},
        "approvals_policy": {"mode": "default_approve", "strict_blacklist_categories": []},
        "destinations": [],
        "degraded_mode_rules": [],
        "idempotency": {"required": False, "strategy": "none"},
        "budgets": {"per_run": {}, "per_day": {}},
        "strict_blacklist_categories": [],
        "retention_class": "medium",
        "readiness": "supervised",
    }


def _as_epoch(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return 0.0
        try:
            return float(text)
        except ValueError:
            pass
        try:
            normalized = text.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized).astimezone(timezone.utc).timestamp()
        except ValueError:
            return 0.0
    return 0.0


def _json_dict(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _workflow_session_target(workflow_id: str) -> str:
    return f"automation-{workflow_id}"


def _extract_external_calls(node_outputs: Dict[str, Any]) -> float:
    total = 0.0
    for value in node_outputs.values():
        if not isinstance(value, dict):
            continue
        ext = value.get("external_calls")
        if isinstance(ext, (int, float)):
            total += float(ext)
        result = value.get("result")
        if isinstance(result, dict):
            ext_result = result.get("external_calls")
            if isinstance(ext_result, (int, float)):
                total += float(ext_result)
    return total


def _find_latest_workflow_run(
    workflow_id: str,
    run_context: Optional[Dict[str, Any]],
    root: Optional[Path],
) -> Dict[str, Any]:
    if not root:
        return {}
    run_root = root / "memory" / "automation" / "dag_runs"
    if not run_root.exists():
        return {}

    wanted_run_id = ""
    if isinstance(run_context, dict):
        wanted_run_id = str(run_context.get("run_id") or "").strip()

    candidates: List[Dict[str, Any]] = []

    for summary_path in run_root.rglob("summary.json"):
        summary = _json_dict(summary_path)
        run_id = str(summary.get("run_id") or summary_path.parent.name)
        if wanted_run_id and run_id != wanted_run_id:
            continue
        graph_id = str(summary.get("graph_id") or "")
        if graph_id != workflow_id:
            continue
        state = _json_dict(summary_path.parent / "state.json")
        node_outputs = state.get("node_outputs") if isinstance(state.get("node_outputs"), dict) else {}
        run_state_state = state.get("state") if isinstance(state.get("state"), dict) else {}
        candidates.append(
            {
                "run_id": run_id,
                "workflow_id": graph_id,
                "status": summary.get("final_status") or summary.get("status"),
                "started_at": summary.get("started_at"),
                "ended_at": summary.get("ended_at"),
                "summary": summary,
                "state": state,
                "run_state": run_state_state,
                "node_states": state.get("node_states") if isinstance(state.get("node_states"), dict) else {},
                "node_outputs": node_outputs,
                "events_path": summary_path.parent / "events.jsonl",
                "run_dir": summary_path.parent,
            }
        )

    for flat_path in run_root.glob("*.json"):
        if flat_path.name in {"run-summary.json", "run-events.json", "run-budget.json", "run-external.json"}:
            continue
        record = _json_dict(flat_path)
        run_id = str(record.get("run_id") or flat_path.stem)
        if wanted_run_id and run_id != wanted_run_id:
            continue
        graph_id = str(record.get("graph_id") or "")
        if graph_id != workflow_id:
            continue
        run_state_state = record.get("state") if isinstance(record.get("state"), dict) else {}
        node_outputs = record.get("node_outputs") if isinstance(record.get("node_outputs"), dict) else {}
        run_dir = Path(str(record.get("run_dir") or ""))
        candidates.append(
            {
                "run_id": run_id,
                "workflow_id": graph_id,
                "status": record.get("final_status") or record.get("status"),
                "started_at": record.get("started_at"),
                "ended_at": record.get("updated_at") or record.get("ended_at"),
                "summary": {},
                "state": record,
                "run_state": run_state_state,
                "node_states": record.get("node_states") if isinstance(record.get("node_states"), dict) else {},
                "node_outputs": node_outputs,
                "events_path": run_dir / "events.jsonl",
                "run_dir": run_dir,
            }
        )

    if not candidates:
        return {}
    candidates.sort(key=lambda item: _as_epoch(item.get("started_at")), reverse=True)
    latest = candidates[0]
    latest["external_calls"] = _extract_external_calls(latest.get("node_outputs", {}))
    return latest


def _check_trace_exists(run_data: Dict[str, Any], check: Dict[str, Any]) -> Dict[str, Any]:
    events_path = run_data.get("events_path")
    node_outputs = run_data.get("node_outputs") if isinstance(run_data.get("node_outputs"), dict) else {}
    has_trace = isinstance(events_path, Path) and events_path.exists()
    has_outputs = bool(node_outputs)
    passed = has_trace and has_outputs
    evidence = {
        "run_id": run_data.get("run_id"),
        "events_path": str(events_path) if isinstance(events_path, Path) else None,
        "node_output_keys": sorted(node_outputs.keys())[:20],
    }
    return {
        "check_id": check.get("id", "trace_exists"),
        "severity": check.get("severity", "must"),
        "passed": passed,
        "message": "Trace and node outputs present" if passed else "Missing events trace or node outputs",
        "evidence": evidence,
    }


def _check_checkpoints(run_data: Dict[str, Any], check: Dict[str, Any], decl: Dict[str, Any]) -> Dict[str, Any]:
    required = [str(c) for c in (decl.get("checkpoints") or []) if str(c).strip()]
    if not required:
        return {
            "check_id": check.get("id", "checkpoints"),
            "severity": check.get("severity", "must"),
            "passed": True,
            "message": "No required checkpoints for this workflow",
            "evidence": {"required": [], "matched": []},
        }

    node_states = run_data.get("node_states") if isinstance(run_data.get("node_states"), dict) else {}
    node_outputs = run_data.get("node_outputs") if isinstance(run_data.get("node_outputs"), dict) else {}
    available = set(node_states.keys()) | set(node_outputs.keys())
    missing = [name for name in required if name not in available]
    return {
        "check_id": check.get("id", "checkpoints"),
        "severity": check.get("severity", "must"),
        "passed": len(missing) == 0,
        "message": "All required checkpoints found" if not missing else f"Missing checkpoints: {missing}",
        "evidence": {"required": required, "matched": sorted(available), "missing": missing},
    }


def _check_safety_gate(
    run_data: Dict[str, Any],
    check: Dict[str, Any],
    decl: Dict[str, Any],
    run_context: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if decl.get("side_effects") != "external_write":
        return {
            "check_id": check.get("id", "safety_gate"),
            "severity": check.get("severity", "must"),
            "passed": True,
            "message": "Safety gate not required for non-external workflows",
            "evidence": {"side_effects": decl.get("side_effects")},
        }

    context = run_context if isinstance(run_context, dict) else {}
    context_gate = context.get("safety_gate_executed")
    external_calls = run_data.get("external_calls", 0.0)
    run_state = run_data.get("run_state") if isinstance(run_data.get("run_state"), dict) else {}
    run_error = run_state.get("_run_error") if isinstance(run_state.get("_run_error"), dict) else {}
    failed_safety = str(run_error.get("code") or "").upper() in {"STEERING_BLOCKED", "SAFETY_BLOCKED"}
    passed = bool(context_gate) or external_calls <= 0 or failed_safety
    return {
        "check_id": check.get("id", "safety_gate"),
        "severity": check.get("severity", "must"),
        "passed": passed,
        "message": (
            "Safety gate evidence present"
            if passed
            else "External calls were attempted without explicit safety-gate evidence"
        ),
        "evidence": {
            "external_calls": external_calls,
            "run_error_code": run_error.get("code"),
            "context_safety_gate_executed": context_gate,
        },
    }


def _check_idempotency(run_data: Dict[str, Any], check: Dict[str, Any], decl: Dict[str, Any], root: Optional[Path]) -> Dict[str, Any]:
    idempotency_decl = decl.get("idempotency") if isinstance(decl.get("idempotency"), dict) else {}
    if not idempotency_decl.get("required"):
        return {
            "check_id": check.get("id", "idempotency"),
            "severity": check.get("severity", "must"),
            "passed": True,
            "message": "Idempotency not required for this workflow",
            "evidence": {"required": False},
        }

    ledger_path = None
    ledger_data: Dict[str, Any] = {}
    if root is not None:
        ledger_path = root / "memory" / "automation" / _workflow_session_target(str(decl.get("workflow_id") or "")) / "post_dedupe.json"
        if ledger_path.exists():
            ledger_data = _json_dict(ledger_path)
    entries = ledger_data.get("entries") if isinstance(ledger_data.get("entries"), dict) else {}
    passed = isinstance(entries, dict) and len(entries) > 0
    return {
        "check_id": check.get("id", "idempotency"),
        "severity": check.get("severity", "must"),
        "passed": passed,
        "message": "Idempotency ledger has entries" if passed else "Missing or empty idempotency ledger",
        "evidence": {
            "ledger_path": str(ledger_path) if ledger_path is not None else None,
            "entry_count": len(entries) if isinstance(entries, dict) else 0,
            "required": True,
            "run_id": run_data.get("run_id"),
        },
    }


def _check_budget(run_data: Dict[str, Any], check: Dict[str, Any]) -> Dict[str, Any]:
    run_state = run_data.get("run_state") if isinstance(run_data.get("run_state"), dict) else {}
    budget_used = run_state.get("budget_used") if isinstance(run_state.get("budget_used"), dict) else {}
    run_error = run_state.get("_run_error") if isinstance(run_state.get("_run_error"), dict) else {}
    budget_exceeded = str(run_error.get("code") or "").upper() == "BUDGET_EXCEEDED"
    passed = bool(budget_used) and not budget_exceeded
    return {
        "check_id": check.get("id", "budget"),
        "severity": check.get("severity", "must"),
        "passed": passed,
        "message": "Budget usage recorded within limits" if passed else "Budget evidence missing or budget exceeded",
        "evidence": {
            "budget_used": budget_used,
            "run_error_code": run_error.get("code"),
            "run_id": run_data.get("run_id"),
        },
    }


def _check_ownership_conflict(run_data: Dict[str, Any], check: Dict[str, Any]) -> Dict[str, Any]:
    run_state = run_data.get("run_state") if isinstance(run_data.get("run_state"), dict) else {}
    run_error = run_state.get("_run_error") if isinstance(run_state.get("_run_error"), dict) else {}
    code = str(run_error.get("code") or "")
    passed = code.upper() not in {"OWNERSHIP_CONFLICT", "HANDOFF_CONFLICT"}
    return {
        "check_id": check.get("id", "ownership_conflict"),
        "severity": check.get("severity", "must"),
        "passed": passed,
        "message": "No ownership conflict recorded" if passed else "Ownership conflict blocked external action",
        "evidence": {"run_error_code": code, "run_id": run_data.get("run_id")},
    }


def run_acceptance_checks(
    workflow_id: str,
    run_context: Optional[Dict[str, Any]] = None,
    workspace_root: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Run declared acceptance checks for a workflow. Returns list of
    {"check_id": str, "passed": bool, "message": str, "severity": str, "evidence": dict}.
    """
    root = _get_workspace_root(workspace_root)
    registry = load_workflow_registry(workspace_root)
    decl = registry.get(workflow_id)
    if not decl:
        return [
            {
                "check_id": "unknown",
                "severity": "must",
                "passed": False,
                "message": f"Workflow {workflow_id} not in registry",
                "evidence": {"workflow_id": workflow_id},
            }
        ]

    checks = decl.get("acceptance_checks") or []
    run_data = _find_latest_workflow_run(workflow_id, run_context, root)
    results: List[Dict[str, Any]] = []
    for c in checks:
        if not isinstance(c, dict):
            continue
        check_id = c.get("id", "unknown")
        if not run_data:
            results.append(
                {
                    "check_id": check_id,
                    "severity": c.get("severity", "must"),
                    "passed": False,
                    "message": "No run evidence found for workflow",
                    "evidence": {
                        "workflow_id": workflow_id,
                        "run_id": (run_context or {}).get("run_id") if isinstance(run_context, dict) else None,
                    },
                }
            )
            continue

        if check_id == "trace_exists":
            result = _check_trace_exists(run_data, c)
        elif check_id == "checkpoints":
            result = _check_checkpoints(run_data, c, decl)
        elif check_id == "safety_gate":
            result = _check_safety_gate(run_data, c, decl, run_context)
        elif check_id == "idempotency":
            result = _check_idempotency(run_data, c, decl, root)
        elif check_id == "budget":
            result = _check_budget(run_data, c)
        elif check_id == "ownership_conflict":
            result = _check_ownership_conflict(run_data, c)
        else:
            result = {
                "check_id": check_id,
                "severity": c.get("severity", "must"),
                "passed": False,
                "message": f"Unknown acceptance check id: {check_id}",
                "evidence": {"workflow_id": workflow_id, "run_id": run_data.get("run_id")},
            }
        results.append(result)
    return results


def get_acceptance_readiness(
    workflow_id: str,
    run_context: Optional[Dict[str, Any]] = None,
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Run acceptance checks and return readiness derived from results.
    Returns: {"ready": bool, "results": list, "blocking_checks": list of check_id for failed must-level}.
    """
    results = run_acceptance_checks(workflow_id, run_context=run_context, workspace_root=workspace_root)
    blocking = [r["check_id"] for r in results if r.get("severity") == "must" and not r.get("passed")]
    return {
        "ready": len(blocking) == 0,
        "results": results,
        "blocking_checks": blocking,
    }


def is_readiness_unattended(workflow_id: str, workspace_root: Optional[Path] = None) -> bool:
    """
    True if workflow is marked unattended in the registry. Readiness is enforced
    at run start (e.g. run_task or executor); unattended only when checks + drills
    pass (drill pass is out-of-band / operational).
    """
    registry = load_workflow_registry(workspace_root)
    decl = registry.get(workflow_id)
    if not decl:
        return False
    return decl.get("readiness") == "unattended"


def check_readiness_for_run(
    workflow_id: str,
    unattended: bool,
    workspace_root: Optional[Path] = None,
) -> bool:
    """
    Return True if a run is allowed given registry readiness. When unattended is True,
    returns True only if workflow readiness is "unattended"; when unattended is False,
    returns True unless readiness is "blocked". Call before starting a run (e.g. run_task
    or executor) to enforce registry labels.
    """
    registry = load_workflow_registry(workspace_root)
    decl = registry.get(workflow_id)
    if not decl:
        # Unknown workflow: allow when supervised, deny when unattended
        return not unattended
    readiness = decl.get("readiness", "supervised")
    if readiness == "blocked":
        return False
    if unattended:
        return readiness == "unattended"
    return True
