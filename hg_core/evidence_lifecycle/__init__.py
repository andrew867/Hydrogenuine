"""Evidence retention and artifact lifecycle (CT-10 RET)."""

from hg_core.evidence_lifecycle.policy import (
    ArtifactClassPolicy,
    RetentionPolicy,
    default_policy_path,
    load_policy,
    policy_hash,
)
from hg_core.evidence_lifecycle.lifecycle import (
    DeletionDecision,
    ArtifactDescriptor,
    classify_path,
    evaluate_deletion,
    is_temp_expired,
)
from hg_core.evidence_lifecycle.export import export_bundle
from hg_core.evidence_lifecycle.proof_bundle import validate_retained_proof_bundle

__all__ = [
    "ArtifactClassPolicy",
    "ArtifactDescriptor",
    "DeletionDecision",
    "RetentionPolicy",
    "classify_path",
    "default_policy_path",
    "evaluate_deletion",
    "export_bundle",
    "is_temp_expired",
    "load_policy",
    "policy_hash",
    "validate_retained_proof_bundle",
]
