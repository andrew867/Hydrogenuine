"""Governed work envelopes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.governed_work_loop.schema import (
    ALLOWED_WORK_TYPES,
    BLOCKED_WORK_TYPES,
    STORE_ROOT,
    load_governed_work_policy,
    new_id,
    now_iso,
)

ENVELOPE_DIR = STORE_ROOT / "envelopes"
EXT_ENVELOPE_DIR = STORE_ROOT / "external_envelopes"


@dataclass
class AllowedWorkScope:
    scope_id: str
    label: str


@dataclass
class GovernedWorkEnvelope:
    envelope_id: str
    agent_id: str
    objective_universe_ref: str
    allowed_work_scopes: tuple[str, ...]
    blocked_work_scopes: tuple[str, ...]
    allowed_internal_actions: tuple[str, ...]
    allowed_external_candidate_types: tuple[str, ...]
    allowed_live_external_actions: tuple[str, ...]
    external_action_quota_ref: str
    external_write_policy_ref: str
    status: str
    created_at: str
    provider_policy_ref: str | None = None
    live_read_policy_ref: str | None = None
    expires_at: str | None = None
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "envelope_id": self.envelope_id,
            "agent_id": self.agent_id,
            "objective_universe_ref": self.objective_universe_ref,
            "allowed_work_scopes": list(self.allowed_work_scopes),
            "blocked_work_scopes": list(self.blocked_work_scopes),
            "allowed_internal_actions": list(self.allowed_internal_actions),
            "allowed_external_candidate_types": list(self.allowed_external_candidate_types),
            "allowed_live_external_actions": list(self.allowed_live_external_actions),
            "external_action_quota_ref": self.external_action_quota_ref,
            "provider_policy_ref": self.provider_policy_ref,
            "live_read_policy_ref": self.live_read_policy_ref,
            "external_write_policy_ref": self.external_write_policy_ref,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "hash": self.hash,
        }

    def with_hash(self) -> GovernedWorkEnvelope:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return GovernedWorkEnvelope(**{**self.__dict__, "hash": compute_record_hash(body)})

    def scope_allowed(self, scope: str) -> bool:
        if scope in self.blocked_work_scopes:
            return False
        return scope in self.allowed_work_scopes

    def work_type_allowed(self, work_type: str) -> bool:
        if work_type in BLOCKED_WORK_TYPES:
            return False
        return work_type in ALLOWED_WORK_TYPES


@dataclass
class ExternalActionEnvelope:
    external_envelope_id: str
    platform: str
    allowed_action_types: tuple[str, ...]
    max_candidates: int
    max_dry_dispatches: int
    max_live_dispatches: int
    requires_phase18_live_permit: bool
    requires_platform_proof: bool
    requires_operator_prearm: bool
    status: str
    created_at: str
    expires_at: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "external_envelope_id": self.external_envelope_id,
            "platform": self.platform,
            "allowed_action_types": list(self.allowed_action_types),
            "max_candidates": self.max_candidates,
            "max_dry_dispatches": self.max_dry_dispatches,
            "max_live_dispatches": self.max_live_dispatches,
            "requires_phase18_live_permit": self.requires_phase18_live_permit,
            "requires_platform_proof": self.requires_platform_proof,
            "requires_operator_prearm": self.requires_operator_prearm,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "hash": self.hash,
        }

    def with_hash(self) -> ExternalActionEnvelope:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return ExternalActionEnvelope(**{**self.__dict__, "hash": compute_record_hash(body)})

    @property
    def live_dispatch_allowed(self) -> bool:
        return self.max_live_dispatches > 0 and self.status == "armed"


def create_demo_envelope(*, agent_id: str = "zero", universe_ref: str = "") -> tuple[GovernedWorkEnvelope, ExternalActionEnvelope]:
    policy = load_governed_work_policy()
    scopes = (
        "internal:artifacts",
        "internal:receipts",
        "internal:queue",
        "internal:external_write_candidate",
        "platform:moltbook:draft-only",
    )
    work_env = GovernedWorkEnvelope(
        envelope_id=new_id("gov-envelope"),
        agent_id=agent_id,
        objective_universe_ref=universe_ref or "demo-universe",
        allowed_work_scopes=scopes,
        blocked_work_scopes=("external:live_unscoped", "mass:message"),
        allowed_internal_actions=tuple(ALLOWED_WORK_TYPES - {"dry_run_external_dispatch", "request_external_authority"}),
        allowed_external_candidate_types=("publish_post",),
        allowed_live_external_actions=(),
        external_action_quota_ref="configs/agent_zero/governed_work_loop_policy.json",
        external_write_policy_ref="configs/agent_zero/external_write_authority_policy.json",
        status="active",
        created_at=now_iso(),
        expires_at=(datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
    ).with_hash()

    ext_env = ExternalActionEnvelope(
        external_envelope_id=new_id("ext-envelope"),
        platform="moltbook",
        allowed_action_types=("publish_post",),
        max_candidates=int(policy.get("max_candidates_default", 5)),
        max_dry_dispatches=int(policy.get("max_dry_dispatches_default", 5)),
        max_live_dispatches=int(policy.get("max_live_dispatches_default", 0)),
        requires_phase18_live_permit=True,
        requires_platform_proof=True,
        requires_operator_prearm=True,
        status="inactive",
        created_at=now_iso(),
        expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    ).with_hash()

    ENVELOPE_DIR.mkdir(parents=True, exist_ok=True)
    EXT_ENVELOPE_DIR.mkdir(parents=True, exist_ok=True)
    (ENVELOPE_DIR / f"{work_env.envelope_id}.json").write_text(json.dumps(work_env.to_payload(), indent=2) + "\n", encoding="utf-8")
    (EXT_ENVELOPE_DIR / f"{ext_env.external_envelope_id}.json").write_text(json.dumps(ext_env.to_payload(), indent=2) + "\n", encoding="utf-8")
    (STORE_ROOT / "demo_external_envelope_ref.json").write_text(
        json.dumps({"work_envelope_id": work_env.envelope_id, "external_envelope_id": ext_env.external_envelope_id}, indent=2) + "\n",
        encoding="utf-8",
    )
    return work_env, ext_env


def load_work_envelope(envelope_id: str) -> GovernedWorkEnvelope | None:
    path = ENVELOPE_DIR / f"{envelope_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return GovernedWorkEnvelope(
        envelope_id=data["envelope_id"],
        agent_id=data["agent_id"],
        objective_universe_ref=data["objective_universe_ref"],
        allowed_work_scopes=tuple(data.get("allowed_work_scopes") or ()),
        blocked_work_scopes=tuple(data.get("blocked_work_scopes") or ()),
        allowed_internal_actions=tuple(data.get("allowed_internal_actions") or ()),
        allowed_external_candidate_types=tuple(data.get("allowed_external_candidate_types") or ()),
        allowed_live_external_actions=tuple(data.get("allowed_live_external_actions") or ()),
        external_action_quota_ref=data.get("external_action_quota_ref", ""),
        provider_policy_ref=data.get("provider_policy_ref"),
        live_read_policy_ref=data.get("live_read_policy_ref"),
        external_write_policy_ref=data.get("external_write_policy_ref", ""),
        status=data.get("status", "active"),
        created_at=data["created_at"],
        expires_at=data.get("expires_at"),
        hash=data.get("hash"),
    )


def load_external_envelope(external_envelope_id: str) -> ExternalActionEnvelope | None:
    path = EXT_ENVELOPE_DIR / f"{external_envelope_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ExternalActionEnvelope(
        external_envelope_id=data["external_envelope_id"],
        platform=data["platform"],
        allowed_action_types=tuple(data.get("allowed_action_types") or ()),
        max_candidates=int(data.get("max_candidates", 0)),
        max_dry_dispatches=int(data.get("max_dry_dispatches", 0)),
        max_live_dispatches=int(data.get("max_live_dispatches", 0)),
        requires_phase18_live_permit=bool(data.get("requires_phase18_live_permit", True)),
        requires_platform_proof=bool(data.get("requires_platform_proof", True)),
        requires_operator_prearm=bool(data.get("requires_operator_prearm", True)),
        status=data.get("status", "inactive"),
        created_at=data["created_at"],
        expires_at=data["expires_at"],
        hash=data.get("hash"),
    )


def load_demo_external_envelope() -> ExternalActionEnvelope | None:
    ref_path = STORE_ROOT / "demo_external_envelope_ref.json"
    if not ref_path.is_file():
        return None
    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    return load_external_envelope(ref["external_envelope_id"])
