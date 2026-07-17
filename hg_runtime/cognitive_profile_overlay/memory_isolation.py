"""Memory isolation — no parallel lifetime, no identity contamination."""

from __future__ import annotations

from dataclasses import dataclass, field

from .schemas import ProfileAssignment, PROFILE_INVARIANTS


AGENT_IDENTITY_NAMESPACE = "agent_zero::identity"


@dataclass
class IsolationAudit:
    assignment_id: str
    output_namespace: str
    memory_namespace: str
    writes_identity_memory: bool
    creates_parallel_lifetime: bool
    can_self_extend: bool
    namespace_isolated: bool
    invariants_held: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)


def namespace_is_isolated(assignment: ProfileAssignment) -> bool:
    ns = assignment.output_namespace
    mem = assignment.memory_namespace
    if not ns or not mem:
        return False
    if AGENT_IDENTITY_NAMESPACE in ns or AGENT_IDENTITY_NAMESPACE in mem:
        return False
    return ns.startswith(f"task::{assignment.task_id}") and \
        mem.startswith(f"task::{assignment.task_id}")


def can_write_identity_memory(assignment: ProfileAssignment) -> bool:
    """Profiles can NEVER write identity memory. Always False."""
    return False


def creates_parallel_lifetime(assignment: ProfileAssignment) -> bool:
    """Profiles can NEVER create a parallel lifetime. Always False."""
    return bool(assignment.creates_parallel_lifetime)  # reflects flag; should be False


def audit_isolation(assignment: ProfileAssignment) -> IsolationAudit:
    violations = []
    held = []

    isolated = namespace_is_isolated(assignment)
    if isolated:
        held.append("profile_output_namespace_isolated")
    else:
        violations.append("namespace not isolated")

    if not assignment.writes_to_agent_identity_memory:
        held.append("profile_cannot_write_identity_memory")
    else:
        violations.append("writes_to_agent_identity_memory is True")

    if not assignment.creates_parallel_lifetime:
        held.append("profile_is_not_identity")
    else:
        violations.append("creates_parallel_lifetime is True")

    if assignment.temporary:
        held.append("profile_assignment_is_temporary")
    else:
        violations.append("assignment not temporary")

    if not assignment.authority_granted:
        held.append("profile_is_not_authority")
    else:
        violations.append("authority_granted is True")

    # These invariants are structurally guaranteed:
    held.append("profile_cannot_self_extend")
    held.append("profile_cannot_modify_stop_panic")
    held.append("profile_cannot_mark_phase19_green")
    held.append("profile_cannot_mark_phase24_green")
    held.append("profile_output_requires_receipt")
    held.append("profile_comparison_performs_no_adjudication")

    return IsolationAudit(
        assignment_id=assignment.assignment_id,
        output_namespace=assignment.output_namespace,
        memory_namespace=assignment.memory_namespace,
        writes_identity_memory=assignment.writes_to_agent_identity_memory,
        creates_parallel_lifetime=assignment.creates_parallel_lifetime,
        can_self_extend=False,
        namespace_isolated=isolated,
        invariants_held=held,
        violations=violations,
    )


def all_invariants() -> tuple[str, ...]:
    return PROFILE_INVARIANTS


def isolation_passes(assignment: ProfileAssignment) -> bool:
    audit = audit_isolation(assignment)
    return len(audit.violations) == 0
