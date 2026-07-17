"""TEP fixtures — deterministic envelopes, operators, and fake authority consumers."""

from __future__ import annotations

from typing import Any

from hg_runtime.translation_envelope_protocol.types import (
    FIXTURE_CLOCK,
    AuthoritySemantics,
    Claim,
    ClaimType,
    LossCertificate,
    ObservationEnvelope,
    ReferenceCondition,
    TranslationEnvelope,
    TranslationOperator,
    UncertaintySemantics,
)

FIXTURE_OBSERVATION = ObservationEnvelope(
    observed_context="fixture:arb-route",
    visible_inputs=("signal:1",),
    hidden_or_unavailable_inputs=(),
    sampling_conditions="single-pass",
    threshold_conditions="default",
    operational_constraints="static-fixture-only",
    model_or_rule_version="tep-fixture-1.0",
    tool_access=(),
    memory_access="none",
    context_window="fixture",
    retry_policy="none",
    inference_budget="fixture",
    scaffold_or_runtime="hg_runtime/translation_envelope_protocol/fixtures",
    judge_or_evaluator="none",
    safety_filters="default",
    human_intervention="none",
    trace_depth="shallow",
    failure_recovery_semantics="fail-closed",
    uncertainty_sources=("sampling",),
    missingness="none",
    known_limitations=("fixture-only",),
)

FIXTURE_OBSERVATION_PEER = ObservationEnvelope(
    observed_context="fixture:arb-route",
    visible_inputs=("signal:1",),
    hidden_or_unavailable_inputs=(),
    sampling_conditions="single-pass",
    threshold_conditions="default",
    operational_constraints="static-fixture-only",
    model_or_rule_version="tep-fixture-1.0",
    tool_access=(),
    memory_access="none",
    context_window="fixture",
    retry_policy="none",
    inference_budget="fixture",
    scaffold_or_runtime="hg_runtime/translation_envelope_protocol/fixtures",
    judge_or_evaluator="none",
    safety_filters="default",
    human_intervention="none",
    trace_depth="shallow",
    failure_recovery_semantics="fail-closed",
    uncertainty_sources=("sampling",),
    missingness="none",
    known_limitations=("fixture-only",),
)

FIXTURE_OBSERVATION_DIFFERENT = ObservationEnvelope(
    observed_context="fixture:imb-mediation",
    visible_inputs=("conflict:1",),
    hidden_or_unavailable_inputs=("private-notes",),
    sampling_conditions="multi-party",
    threshold_conditions="consensus",
    operational_constraints="static-fixture-only",
    model_or_rule_version="tep-fixture-1.0",
    tool_access=(),
    memory_access="read-only",
    context_window="fixture",
    retry_policy="none",
    inference_budget="fixture",
    scaffold_or_runtime="hg_runtime/translation_envelope_protocol/fixtures",
    judge_or_evaluator="mediator",
    safety_filters="default",
    human_intervention="optional",
    trace_depth="medium",
    failure_recovery_semantics="fail-closed",
    uncertainty_sources=("party-disagreement",),
    missingness="partial",
    known_limitations=("fixture-only",),
)

ADVISORY_AUTHORITY = AuthoritySemantics(
    authority_type="ADVISORY",
    may_authorize_execution=False,
    may_mint_permit=False,
    may_call_oea_ter=False,
    may_grant_tools=False,
    may_grant_memory=False,
    may_grant_context=False,
    may_publish=False,
    downstream_allowed_uses=("prioritization", "observation"),
    downstream_forbidden_uses=("permit evidence", "execution input"),
    required_authority_chain_refs=(),
)

REVIEW_RECEIPT_AUTHORITY = AuthoritySemantics(
    authority_type="OPERATOR_REVIEW_RECEIPT",
    may_authorize_execution=False,
    may_mint_permit=False,
    may_call_oea_ter=False,
    may_grant_tools=False,
    may_grant_memory=False,
    may_grant_context=False,
    may_publish=False,
    downstream_allowed_uses=("review record",),
    downstream_forbidden_uses=("permit evidence", "execution input"),
    required_authority_chain_refs=(),
)

APPROVAL_EVIDENCE_AUTHORITY = AuthoritySemantics(
    authority_type="OPERATOR_APPROVAL_EVIDENCE",
    may_authorize_execution=False,
    may_mint_permit=False,
    may_call_oea_ter=False,
    may_grant_tools=False,
    may_grant_memory=False,
    may_grant_context=False,
    may_publish=False,
    downstream_allowed_uses=("operator evidence",),
    downstream_forbidden_uses=("permit evidence", "execution input"),
    required_authority_chain_refs=(),
)

PROOF_EVIDENCE_AUTHORITY = AuthoritySemantics(
    authority_type="PROOF_EVIDENCE",
    may_authorize_execution=False,
    may_mint_permit=False,
    may_call_oea_ter=False,
    may_grant_tools=False,
    may_grant_memory=False,
    may_grant_context=False,
    may_publish=False,
    downstream_allowed_uses=("proof review",),
    downstream_forbidden_uses=("permit evidence", "execution input"),
    required_authority_chain_refs=(),
)

HEURISTIC_UNCERTAINTY = UncertaintySemantics(
    uncertainty_type="HEURISTIC_SCORE",
    ambiguity="low",
    missingness="none",
    unsupported_regions=(),
    stale_regions=(),
)

PROBABILITY_UNCERTAINTY = UncertaintySemantics(
    uncertainty_type="PROBABILITY",
    ambiguity="low",
    missingness="none",
    unsupported_regions=(),
    stale_regions=(),
)

CALIBRATION_UNCERTAINTY = UncertaintySemantics(
    uncertainty_type="CALIBRATION",
    ambiguity="low",
    missingness="none",
    unsupported_regions=(),
    stale_regions=(),
)

PROOF_UNCERTAINTY = UncertaintySemantics(
    uncertainty_type="PROOF_STATUS",
    ambiguity="low",
    missingness="none",
    unsupported_regions=(),
    stale_regions=(),
)

RISK_REFERENCE = ReferenceCondition(
    reference_id="ref:risk-posture",
    target_decision_frame="RISK_POSTURE",
    comparison_scope="route-level",
    expected_units_or_semantics="risk-score-0-1",
    required_translation_inputs=(
        "observed_context",
        "sampling_conditions",
        "model_or_rule_version",
        "tool_access",
    ),
    authority_required="NONE",
    freshness_required=False,
    identity_required=False,
    scope_required=False,
)

PRIORITY_REFERENCE = ReferenceCondition(
    reference_id="ref:priority",
    target_decision_frame="PRIORITIZATION",
    comparison_scope="queue-level",
    expected_units_or_semantics="priority-score-0-1",
    required_translation_inputs=(
        "observed_context",
        "sampling_conditions",
        "model_or_rule_version",
        "tool_access",
    ),
    authority_required="NONE",
    freshness_required=False,
    identity_required=False,
    scope_required=False,
)

PERMIT_REFERENCE = ReferenceCondition(
    reference_id="ref:permit-authority",
    target_decision_frame="PERMIT_AUTHORITY",
    comparison_scope="gpp-evidence",
    expected_units_or_semantics="governed-permit-evidence",
    required_translation_inputs=("observed_context", "model_or_rule_version"),
    authority_required="GPP_PERMIT",
    freshness_required=True,
    identity_required=True,
    scope_required=True,
)

EXECUTION_REFERENCE = ReferenceCondition(
    reference_id="ref:execution-authority",
    target_decision_frame="EXECUTION_AUTHORITY",
    comparison_scope="ueak-admission",
    expected_units_or_semantics="governed-admission-evidence",
    required_translation_inputs=("observed_context", "model_or_rule_version"),
    authority_required="UEAK_ADMISSION",
    freshness_required=True,
    identity_required=True,
    scope_required=True,
)

REVIEW_REFERENCE = ReferenceCondition(
    reference_id="ref:review",
    target_decision_frame="REVIEW",
    comparison_scope="operator-review",
    expected_units_or_semantics="review-receipt",
    required_translation_inputs=("observed_context", "human_intervention"),
    authority_required="REVIEW_ONLY",
    freshness_required=False,
    identity_required=True,
    scope_required=True,
)

POSTURE_REFERENCE = ReferenceCondition(
    reference_id="ref:operating-posture",
    target_decision_frame="RISK_POSTURE",
    comparison_scope="control-cluster",
    expected_units_or_semantics="operating-posture",
    required_translation_inputs=("observed_context", "operational_constraints"),
    authority_required="NONE",
    freshness_required=False,
    identity_required=False,
    scope_required=False,
)

RISK_TO_PRIORITY_OPERATOR = TranslationOperator(
    operator_id="op:risk-to-priority-v1",
    from_claim_type="RISK_SCORE",
    to_reference_condition=PRIORITY_REFERENCE.reference_id,
    required_input_fields=("observed_context", "sampling_conditions"),
    supported_envelope_conditions=("fixture:arb-route",),
    unsupported_conditions=("fixture:imb-mediation",),
    transformation_description="Map risk score into prioritization frame",
    deterministic=True,
    lossiness="LOSSLESS",
    validation_refs=("proof:tep-operator-risk-priority",),
    proof_refs=("proof:tep-operator-risk-priority",),
    version="1.0",
)

TRUST_TO_CALIBRATION_OPERATOR = TranslationOperator(
    operator_id="op:trust-to-calibration-v1",
    from_claim_type="TRUST_SCORE",
    to_reference_condition="ref:trust-calibration",
    required_input_fields=("observed_context", "model_or_rule_version"),
    supported_envelope_conditions=("fixture:arb-route",),
    unsupported_conditions=(),
    transformation_description="Approximate trust into calibration frame",
    deterministic=True,
    lossiness="LOSSY_DISCLOSED",
    validation_refs=("proof:tep-operator-trust-calibration",),
    proof_refs=("proof:tep-operator-trust-calibration",),
    version="1.0",
)

TRUST_CALIBRATION_REFERENCE = ReferenceCondition(
    reference_id="ref:trust-calibration",
    target_decision_frame="TRUST_CALIBRATION",
    comparison_scope="calibration",
    expected_units_or_semantics="calibration-score-0-1",
    required_translation_inputs=("observed_context", "model_or_rule_version"),
    authority_required="NONE",
    freshness_required=False,
    identity_required=False,
    scope_required=False,
)

DEFAULT_OPERATORS: tuple[TranslationOperator, ...] = (
    RISK_TO_PRIORITY_OPERATOR,
    TRUST_TO_CALIBRATION_OPERATOR,
)


def fixture_loss_certificate(**overrides: Any) -> LossCertificate:
    base = dict(
        loss_certificate_id="loss:fixture-1",
        compression_method="field-prune-v1",
        fields_preserved=("observed_context", "model_or_rule_version"),
        fields_discarded=("trace_depth",),
        expected_effect="shallower trace may bias risk comparison",
        invalid_comparisons=("deep-trace risk compare", "cross-organ trace-depth rank"),
        audit_ref="audit:tep-fixture",
    )
    base.update(overrides)
    return LossCertificate(**base)


def fixture_claim(
    claim_type: ClaimType = "RISK_SCORE",
    *,
    claim_id: str = "claim:fixture-1",
    scalar_value: float = 0.8,
    structured_value: dict[str, Any] | None = None,
) -> Claim:
    return Claim(
        claim_id=claim_id,
        claim_type=claim_type,
        scalar_value=scalar_value,
        structured_value=structured_value,
    )


def fixture_envelope(
    claim: Claim | None = None,
    *,
    envelope_id: str = "env:fixture-1",
    producer_module: str = "ARB",
    reference_condition: ReferenceCondition | None = None,
    observation_envelope: ObservationEnvelope | None = None,
    uncertainty_semantics: UncertaintySemantics | None = None,
    authority_semantics: AuthoritySemantics | None = None,
    translation_status: str = "DIRECTLY_COMPARABLE",
    compression_method: str = "",
    loss_certificate: LossCertificate | None = None,
    identity_ref: str = "",
    scope_ref: str = "",
    freshness_ref: str = "",
    expires_at: str = "",
    not_translatable_reason: str = "",
) -> TranslationEnvelope:
    claim = claim or fixture_claim()
    if compression_method and loss_certificate is None:
        loss_certificate = fixture_loss_certificate(compression_method=compression_method)
    return TranslationEnvelope(
        envelope_id=envelope_id,
        claim_id=claim.claim_id,
        claim_type=claim.claim_type,
        producer_ref=f"trace:{envelope_id}",
        producer_module=producer_module,
        producer_role="fixture",
        scalar_value=claim.scalar_value,
        structured_value=claim.structured_value,
        reference_condition=reference_condition or RISK_REFERENCE,
        observation_envelope=observation_envelope or FIXTURE_OBSERVATION,
        uncertainty_semantics=uncertainty_semantics or HEURISTIC_UNCERTAINTY,
        authority_semantics=authority_semantics or ADVISORY_AUTHORITY,
        trace_pointer=f"trace:{claim.claim_id}",
        proof_refs=("proof:tep-fixture",),
        translation_status=translation_status,  # type: ignore[arg-type]
        created_at=FIXTURE_CLOCK,
        compression_method=compression_method,
        loss_certificate=loss_certificate,
        not_translatable_reason=not_translatable_reason,
        identity_ref=identity_ref,
        scope_ref=scope_ref,
        freshness_ref=freshness_ref,
        expires_at=expires_at,
    )


def naked_scalar_fixture(claim_type: ClaimType = "RISK_SCORE", *, value: float = 0.8) -> Claim:
    return fixture_claim(claim_type=claim_type, claim_id=f"naked:{claim_type.lower()}", scalar_value=value)


def compressed_without_certificate_fixture() -> tuple[Claim, TranslationEnvelope]:
    claim = fixture_claim(claim_id="claim:compressed-naked")
    envelope = TranslationEnvelope(
        envelope_id="env:compressed-naked",
        claim_id=claim.claim_id,
        claim_type=claim.claim_type,
        producer_ref="trace:compressed-naked",
        producer_module="RPB",
        producer_role="fixture",
        scalar_value=claim.scalar_value,
        reference_condition=RISK_REFERENCE,
        observation_envelope=FIXTURE_OBSERVATION,
        uncertainty_semantics=HEURISTIC_UNCERTAINTY,
        authority_semantics=ADVISORY_AUTHORITY,
        trace_pointer="trace:compressed-naked",
        proof_refs=(),
        translation_status="APPROXIMATE_LOSSY",
        created_at=FIXTURE_CLOCK,
        compression_method="field-prune-v1",
        loss_certificate=None,
    )
    return claim, envelope


def false_comparability_pair() -> tuple[Claim, TranslationEnvelope, Claim, TranslationEnvelope]:
    risk_claim = fixture_claim(claim_type="RISK_SCORE", claim_id="claim:risk-08", scalar_value=0.8)
    risk_env = fixture_envelope(risk_claim, envelope_id="env:risk-08")
    conf_claim = fixture_claim(claim_type="MODEL_CONFIDENCE", claim_id="claim:conf-08", scalar_value=0.8)
    conf_env = fixture_envelope(
        conf_claim,
        envelope_id="env:conf-08",
        uncertainty_semantics=PROBABILITY_UNCERTAINTY,
    )
    return risk_claim, risk_env, conf_claim, conf_env


def ori_review_receipt_fixture(*, approved: bool = True) -> tuple[Claim, TranslationEnvelope]:
    claim = fixture_claim(
        claim_type="OPERATOR_REVIEW_RECEIPT",
        claim_id="claim:ori-review",
        structured_value={"operator_action": "approved" if approved else "deferred"},
    )
    envelope = fixture_envelope(
        claim,
        envelope_id="env:ori-review",
        producer_module="ORI",
        reference_condition=REVIEW_REFERENCE,
        authority_semantics=REVIEW_RECEIPT_AUTHORITY,
        identity_ref="iam:op:local" if approved else "",
        scope_ref="approve_change" if approved else "",
    )
    return claim, envelope


def proof_summary_fixture() -> tuple[Claim, TranslationEnvelope]:
    claim = fixture_claim(
        claim_type="PROOF_SUMMARY",
        claim_id="claim:proof-summary",
        structured_value={"status": "passed"},
    )
    envelope = fixture_envelope(
        claim,
        envelope_id="env:proof-summary",
        producer_module="OBT",
        uncertainty_semantics=PROOF_UNCERTAINTY,
        authority_semantics=PROOF_EVIDENCE_AUTHORITY,
    )
    return claim, envelope


def simulation_result_fixture() -> tuple[Claim, TranslationEnvelope]:
    claim = fixture_claim(
        claim_type="SIMULATION_RESULT",
        claim_id="claim:sim-success",
        structured_value={"outcome": "success"},
    )
    envelope = fixture_envelope(
        claim,
        envelope_id="env:sim-success",
        producer_module="SIM",
        authority_semantics=ADVISORY_AUTHORITY,
        not_translatable_reason="simulation is not execution history",
        translation_status="NOT_TRANSLATABLE",
    )
    return claim, envelope


def lossy_accepted_fixture() -> tuple[Claim, TranslationEnvelope]:
    claim = fixture_claim(claim_type="RISK_SCORE", claim_id="claim:lossy", scalar_value=0.7)
    certificate = fixture_loss_certificate()
    envelope = fixture_envelope(
        claim,
        envelope_id="env:lossy",
        translation_status="APPROXIMATE_LOSSY",
        compression_method="field-prune-v1",
        loss_certificate=certificate,
    )
    return claim, envelope


def authority_field_discard_certificate() -> LossCertificate:
    return LossCertificate(
        loss_certificate_id="loss:bad-authority",
        compression_method="field-prune-v1",
        fields_preserved=("observed_context",),
        fields_discarded=("authority_semantics",),
        expected_effect="would hide authority",
        invalid_comparisons=("any authority compare",),
        audit_ref="audit:tep-bad",
    )


def gpp_permit_evidence_fixture(*, naked: bool = False) -> dict[str, Any]:
    if naked:
        return {
            "request_id": "gpp-req:naked",
            "evidence_claim_id": "naked:risk_score",
            "envelope": None,
        }
    claim = fixture_claim(claim_id="claim:gpp-evidence")
    envelope = fixture_envelope(
        claim,
        envelope_id="env:gpp-evidence",
        producer_module="OBT",
        authority_semantics=PROOF_EVIDENCE_AUTHORITY,
        freshness_ref="fresh:gpp-evidence",
        identity_ref="iam:op:local",
        scope_ref="approve_change",
        expires_at="2099-01-01T00:00:00.000000Z",
    )
    return {
        "request_id": "gpp-req:valid",
        "evidence_claim_id": claim.claim_id,
        "envelope": envelope,
    }


def ueak_admission_evidence_fixture(*, naked: bool = False) -> dict[str, Any]:
    if naked:
        return {
            "request_id": "ueak-req:naked",
            "permit_ref": "permit:fixture",
            "support_claim_id": "naked:trust_score",
            "envelope": None,
        }
    claim = fixture_claim(claim_type="TRUST_SCORE", claim_id="claim:ueak-support")
    envelope = fixture_envelope(
        claim,
        envelope_id="env:ueak-support",
        producer_module="TRB",
        authority_semantics=ADVISORY_AUTHORITY,
        freshness_ref="fresh:ueak-support",
        identity_ref="iam:op:local",
        scope_ref="execute:fixture",
        expires_at="2099-01-01T00:00:00.000000Z",
    )
    return {
        "request_id": "ueak-req:valid",
        "permit_ref": "permit:fixture",
        "support_claim_id": claim.claim_id,
        "envelope": envelope,
    }


__all__ = [
    "ADVISORY_AUTHORITY",
    "APPROVAL_EVIDENCE_AUTHORITY",
    "DEFAULT_OPERATORS",
    "EXECUTION_REFERENCE",
    "FIXTURE_OBSERVATION",
    "FIXTURE_OBSERVATION_DIFFERENT",
    "FIXTURE_OBSERVATION_PEER",
    "PERMIT_REFERENCE",
    "POSTURE_REFERENCE",
    "PRIORITY_REFERENCE",
    "PROOF_EVIDENCE_AUTHORITY",
    "REVIEW_REFERENCE",
    "REVIEW_RECEIPT_AUTHORITY",
    "RISK_REFERENCE",
    "RISK_TO_PRIORITY_OPERATOR",
    "TRUST_CALIBRATION_REFERENCE",
    "TRUST_TO_CALIBRATION_OPERATOR",
    "authority_field_discard_certificate",
    "compressed_without_certificate_fixture",
    "false_comparability_pair",
    "fixture_claim",
    "fixture_envelope",
    "fixture_loss_certificate",
    "gpp_permit_evidence_fixture",
    "lossy_accepted_fixture",
    "naked_scalar_fixture",
    "ori_review_receipt_fixture",
    "proof_summary_fixture",
    "simulation_result_fixture",
    "ueak_admission_evidence_fixture",
]
