"""Temporary profile assignment — bounded, expiring, identity-isolated."""

from __future__ import annotations

from .schemas import ProfileAssignment, CognitiveProfile, ASSIGNMENT_SCOPES
from .profile_loader import load_profile_by_id


_DEFAULT_SAFETY_BOUNDARIES = [
    "profile_is_not_identity",
    "profile_is_not_authority",
    "profile_is_not_truth",
    "profile_assignment_is_temporary",
    "profile_cannot_authorize_tools",
    "profile_cannot_modify_stop_panic",
    "operator_review_required",
]


def assign_profile(
    *,
    task_id: str,
    profile_id: str,
    assignment_scope: str,
    applied_at: str,
    expires_at: str | None = None,
    max_turns: int | None = None,
) -> ProfileAssignment | None:
    profile = load_profile_by_id(profile_id)
    if profile is None:
        return None

    if assignment_scope not in ASSIGNMENT_SCOPES:
        assignment_scope = "other"

    # An assignment MUST be bounded: require either an expiry or a turn cap.
    if expires_at is None and max_turns is None:
        max_turns = 8  # safe default bound; never unbounded

    assignment = ProfileAssignment(
        assignment_id=f"asgn_{task_id}_{profile_id}",
        task_id=task_id,
        profile_id=profile.profile_id,
        profile_name=profile.profile_name,
        profile_kind=profile.profile_kind,
        profile_source_path=profile.source_path,
        assignment_scope=assignment_scope,
        applied_at=applied_at,
        expires_at=expires_at,
        max_turns=max_turns,
        temporary=True,
        profile_is_identity=False,
        creates_parallel_lifetime=False,
        writes_to_agent_identity_memory=False,
        writes_to_profile_memory=False,
        memory_namespace=f"task::{task_id}::profile::{profile_id}",
        output_namespace=f"task::{task_id}::output::{profile_id}",
        authority_granted=False,
        tools_authorized=False,
        live_effects_authorized=False,
        operator_review_required=True,
        profile_parameters=dict(profile.profile_parameters),
        prompt_style_hints=list(profile.prompt_style_hints),
        safety_boundaries=list(_DEFAULT_SAFETY_BOUNDARIES),
    )
    assignment.receipt_hash = assignment.compute_hash()
    return assignment


def assignment_is_bounded(assignment: ProfileAssignment) -> bool:
    return assignment.expires_at is not None or assignment.max_turns is not None


def assignment_is_safe(assignment: ProfileAssignment) -> tuple[bool, list[str]]:
    violations = []
    if assignment.profile_is_identity:
        violations.append("profile_is_identity must be False")
    if assignment.creates_parallel_lifetime:
        violations.append("creates_parallel_lifetime must be False")
    if assignment.writes_to_agent_identity_memory:
        violations.append("writes_to_agent_identity_memory must be False")
    if assignment.authority_granted:
        violations.append("authority_granted must be False")
    if assignment.tools_authorized:
        violations.append("tools_authorized must be False")
    if assignment.live_effects_authorized:
        violations.append("live_effects_authorized must be False")
    if not assignment.operator_review_required:
        violations.append("operator_review_required must be True")
    if not assignment.temporary:
        violations.append("temporary must be True")
    if not assignment_is_bounded(assignment):
        violations.append("assignment must have expires_at or max_turns")
    return len(violations) == 0, violations


def attempt_self_extend(assignment: ProfileAssignment) -> bool:
    """Profiles cannot self-extend. Always returns False (extension denied)."""
    return False
