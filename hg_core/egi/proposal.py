"""EGI gap and proposal builders — advisory only."""

from __future__ import annotations

from hg_core.egi.detector import DEFAULT_REPEAT_THRESHOLD
from hg_core.egi.errors import DENIED_INSUFFICIENT_PATTERN, EGIValidationError
from hg_core.egi.schemas import (
    CapabilityGap,
    EmergentBehaviorObservation,
    GapType,
    InfrastructureProposal,
    ProposalType,
)

_DEFAULT_FORBIDDEN = (
    "no_self_modification",
    "no_tool_grants",
    "no_memory_grants",
    "no_database_creation",
    "no_deploy",
    "no_merge",
    "no_oea_ter",
    "no_gpp_mint",
    "no_ueak_approval",
    "no_hal_soar_bypass",
    "no_srp_apply",
    "no_generated_code_trust_before_audit",
)


def recommend_modules(observation: EmergentBehaviorObservation, *, gap: CapabilityGap | None = None) -> tuple[str, ...]:
    modules: list[str] = []
    if observation.sensitivity_class == "privacy_sensitive" or (gap and gap.privacy_risk == "high"):
        modules.extend(["SEC", "RET"])
    if gap and gap.resource_cost_estimate == "high":
        modules.append("RSC")
    elif observation.behavior_label.endswith("_heavy"):
        modules.append("RSC")
    if observation.sensitivity_class == "mission_changing":
        modules.append("MIS")
    if observation.sensitivity_class == "affect_driven":
        modules.extend(["AFC", "SIL", "DEP-BOND"])
    return tuple(dict.fromkeys(modules))


def create_capability_gap(
    observation: EmergentBehaviorObservation,
    *,
    gap_type: GapType = "missing_tool",
    threshold: int = DEFAULT_REPEAT_THRESHOLD,
) -> CapabilityGap | None:
    """Create a capability gap from an observation; None if pattern insufficient."""
    if observation.repeated_count < threshold:
        return None
    privacy_risk = "high" if observation.sensitivity_class == "privacy_sensitive" else "low"
    resource_cost = "high" if observation.behavior_label.endswith("_heavy") else "low"
    gap = CapabilityGap(
        gap_id=f"egi_gap_{observation.observation_id}",
        observation_refs=(observation.observation_id,),
        gap_type=gap_type,
        description=f"Capability gap for repeated behavior {observation.behavior_label}",
        current_cost="medium" if observation.repeated_count >= threshold + 1 else "low",
        current_risk="medium" if observation.failure_refs else "low",
        expected_benefit="reduce operator workaround burden",
        abuse_risk="medium" if gap_type == "missing_tool" else "low",
        authority_risk="low",
        privacy_risk=privacy_risk,
        operator_burden="medium",
        resource_cost_estimate=resource_cost,
        affected_tranches=("6.5",),
        recommended_owner="operator",
        recommended_modules=recommend_modules(observation),
    )
    return gap


def create_infrastructure_proposal(gap: CapabilityGap) -> InfrastructureProposal:
    proposal_type = _proposal_type_for_gap(gap.gap_type)
    risk_refs = tuple(f"risk:{mod.lower()}" for mod in gap.recommended_modules)
    redaction_checks = ("SEC", "RET") if "SEC" in gap.recommended_modules else ()
    return InfrastructureProposal(
        proposal_id=f"egi_prop_{gap.gap_id}",
        gap_refs=(gap.gap_id,),
        proposal_type=proposal_type,
        title=f"Infrastructure proposal for {gap.gap_type}",
        problem_statement=gap.description,
        proposed_capability=f"fixture capability for {gap.gap_type}",
        first_safe_slice="schemas/fixtures/fake queue only",
        required_tests=("tests/egi/",),
        required_proof_gate="scripts/evals/egi_emergent_gap_gate.py",
        required_authority_checks=("no_self_modification", "no_tool_grants", "human_approval_required"),
        required_redaction_checks=redaction_checks,
        required_retention_policy="ret:egi_fixture",
        required_operator_approval=True,
        do_not_implement_before=("authority_chain_e2e_green",),
        forbidden_behaviors=_DEFAULT_FORBIDDEN,
        risk_assessment_refs=risk_refs,
    )


def _proposal_type_for_gap(gap_type: GapType) -> ProposalType:
    mapping: dict[GapType, ProposalType] = {
        "missing_tool": "tool_request",
        "missing_schema": "schema_request",
        "missing_memory_namespace": "memory_request",
        "missing_data_store": "data_store_request",
        "missing_worker": "worker_request",
        "missing_proof_gate": "proof_gate_request",
        "missing_ui_affordance": "ui_request",
        "missing_eval": "eval_request",
        "missing_migration": "migration_request",
        "missing_documentation": "docs_request",
    }
    return mapping.get(gap_type, "unknown")


def require_capability_gap(observation: EmergentBehaviorObservation, **kwargs: object) -> CapabilityGap:
    gap = create_capability_gap(observation, **kwargs)  # type: ignore[arg-type]
    if gap is None:
        raise EGIValidationError(DENIED_INSUFFICIENT_PATTERN)
    return gap


__all__ = [
    "create_capability_gap",
    "create_infrastructure_proposal",
    "recommend_modules",
    "require_capability_gap",
]
