"""EGI build request and operator approval packet builders."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

from hg_core.egi.detector import FIXTURE_CLOCK
from hg_core.egi.errors import (
    DENIED_EXPIRED_APPROVAL,
    DENIED_MISSING_APPROVAL,
    DENIED_PENDING_APPROVAL,
    DENIED_REJECTED_APPROVAL,
    DENIED_SELF_APPROVAL,
    EGIRoutingDenied,
)
from hg_core.egi.schemas import (
    BuildRequest,
    InfrastructureProposal,
    OperatorApprovalPacket,
    OperatorDecision,
)

_DEFAULT_TTL_HOURS = 24


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _format_ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def create_build_request(proposal: InfrastructureProposal, *, now: str | None = None) -> BuildRequest:
    _ = now or FIXTURE_CLOCK
    return BuildRequest(
        build_request_id=f"egi_build_{proposal.proposal_id}",
        proposal_ref=proposal.proposal_id,
        requested_by="EGI",
        target_repo="workspace",
        target_paths=(f"hg_core/egi/{proposal.proposal_type}/",),
        allowed_file_patterns=("hg_core/egi/**", "tests/egi/**", "scripts/evals/egi_*"),
        forbidden_file_patterns=("hg_runtime/**", "hg_gpp/**", "hg_ueak/**", "hg_hal/**", "hg_soar/**"),
        required_tests=proposal.required_tests,
        required_gate=proposal.required_proof_gate,
        required_report_path="docs/reports/phases/EGI_FIRST_SAFE_SLICE_REPORT.md",
        expected_commit_prefix="feat(egi):",
        human_approval_required=True,
        approval_ref=None,
        status="awaiting_operator_review",
    )


def create_operator_approval_packet(
    build_request: BuildRequest,
    *,
    now: str | None = None,
    ttl_hours: float = _DEFAULT_TTL_HOURS,
) -> OperatorApprovalPacket:
    tick = now or FIXTURE_CLOCK
    issued = _parse_ts(tick)
    expiration = _format_ts(issued + timedelta(hours=ttl_hours))
    return OperatorApprovalPacket(
        approval_packet_id=f"egi_appr_{build_request.build_request_id}",
        build_request_ref=build_request.build_request_id,
        summary=f"Review infrastructure build request {build_request.build_request_id}",
        risk_summary="EGI proposal only — no authority granted by packet creation",
        files_expected_to_change=build_request.target_paths,
        tests_expected_to_run=build_request.required_tests,
        proof_gate_expected=build_request.required_gate,
        rollback_plan="revert scoped commit; no deploy",
        expiration=expiration,
        operator_decision="pending",
        operator_ref=None,
        decision_time=None,
    )


def approve_packet(
    packet: OperatorApprovalPacket,
    *,
    operator_ref: str,
    decision_time: str | None = None,
) -> OperatorApprovalPacket:
    if operator_ref.strip().lower().startswith(("egi:", "agent:", "model:")):
        raise EGIRoutingDenied((DENIED_SELF_APPROVAL,), detail="EGI cannot approve its own build request")
    return replace(
        packet,
        operator_decision="approved",
        operator_ref=operator_ref,
        decision_time=decision_time or FIXTURE_CLOCK,
    )


def reject_packet(
    packet: OperatorApprovalPacket,
    *,
    operator_ref: str,
    decision_time: str | None = None,
) -> OperatorApprovalPacket:
    return replace(
        packet,
        operator_decision="rejected",
        operator_ref=operator_ref,
        decision_time=decision_time or FIXTURE_CLOCK,
    )


def validate_routing(
    build_request: BuildRequest,
    packet: OperatorApprovalPacket,
    *,
    now: str | None = None,
) -> None:
    """Fail closed unless human approval is current and approved."""
    codes: list[str] = []
    if build_request.human_approval_required and packet.operator_decision != "approved":
        if packet.operator_decision == "pending":
            codes.append(DENIED_PENDING_APPROVAL)
        elif packet.operator_decision == "rejected":
            codes.append(DENIED_REJECTED_APPROVAL)
        elif packet.operator_decision == "expired":
            codes.append(DENIED_EXPIRED_APPROVAL)
        else:
            codes.append(DENIED_MISSING_APPROVAL)
    if packet.operator_decision == "approved":
        tick = _parse_ts(now or FIXTURE_CLOCK)
        if tick >= _parse_ts(packet.expiration):
            codes.append(DENIED_EXPIRED_APPROVAL)
    if build_request.requested_by == "EGI" and packet.operator_ref and packet.operator_ref.startswith("egi:"):
        codes.append(DENIED_SELF_APPROVAL)
    if codes:
        raise EGIRoutingDenied(tuple(dict.fromkeys(codes)))


__all__ = [
    "approve_packet",
    "create_build_request",
    "create_operator_approval_packet",
    "reject_packet",
    "validate_routing",
]
