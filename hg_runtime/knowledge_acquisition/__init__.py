"""Phase 30 governed Knowledge Acquisition Loop.

Learn unfamiliar domains from local sources and tests: ingest source artifacts,
extract concepts, build a glossary, identify claims (defaulting unsupported ones
to TBD), create and audit a bounded mini-task, and promote knowledge into Phase
26 memory only after citation, audit, and receipt. Acquisition proposes and
records; it never grants authority, treats a source as truth, self-merges, uses
the network by default, reads credentials, or creates live side effects.
"""

from hg_runtime.knowledge_acquisition.audit import audit_mini_task_result, trust_result
from hg_runtime.knowledge_acquisition.citations import create_citation
from hg_runtime.knowledge_acquisition.claims import create_claim_record, detect_contradictions
from hg_runtime.knowledge_acquisition.concepts import extract_concept
from hg_runtime.knowledge_acquisition.evidence import link_evidence
from hg_runtime.knowledge_acquisition.gate import (
    evaluate_phase30_gate,
    validate_phase30_proof_bundle,
)
from hg_runtime.knowledge_acquisition.glossary import create_glossary_entry
from hg_runtime.knowledge_acquisition.mini_tasks import define_mini_task
from hg_runtime.knowledge_acquisition.promotion import (
    build_acquisition_outcome_receipt,
    build_domain_readiness_record,
    build_skill_candidate,
    promote_to_memory,
    request_memory_promotion,
)
from hg_runtime.knowledge_acquisition.replay import (
    AcquisitionReplayResult,
    KnowledgeAcquisitionLog,
)
from hg_runtime.knowledge_acquisition.schemas import (
    ACQUISITION_CLAIM_BOUNDARY,
    CLAIM_RECORD_SCHEMA,
    CONCEPT_RECORD_SCHEMA,
    DOMAIN_READINESS_RECORD_SCHEMA,
    EVIDENCE_LINK_SCHEMA,
    GLOSSARY_ENTRY_SCHEMA,
    KNOWLEDGE_ACQUISITION_RECEIPT_SCHEMA,
    MEMORY_PROMOTION_REQUEST_SCHEMA,
    MINI_TASK_AUDIT_SCHEMA,
    MINI_TASK_SCHEMA,
    SOURCE_ARTIFACT_SCHEMA,
    SOURCE_CITATION_SCHEMA,
    SOURCE_FRESHNESS_REVIEW_SCHEMA,
    KnowledgeAcquisitionError,
)
from hg_runtime.knowledge_acquisition.sources import (
    ingest_source,
    require_review_if_stale,
    review_freshness,
    source_quality_is_advisory,
)

__all__ = [
    "ACQUISITION_CLAIM_BOUNDARY",
    "AcquisitionReplayResult",
    "CLAIM_RECORD_SCHEMA",
    "CONCEPT_RECORD_SCHEMA",
    "DOMAIN_READINESS_RECORD_SCHEMA",
    "EVIDENCE_LINK_SCHEMA",
    "GLOSSARY_ENTRY_SCHEMA",
    "KNOWLEDGE_ACQUISITION_RECEIPT_SCHEMA",
    "KnowledgeAcquisitionError",
    "KnowledgeAcquisitionLog",
    "MEMORY_PROMOTION_REQUEST_SCHEMA",
    "MINI_TASK_AUDIT_SCHEMA",
    "MINI_TASK_SCHEMA",
    "SOURCE_ARTIFACT_SCHEMA",
    "SOURCE_CITATION_SCHEMA",
    "SOURCE_FRESHNESS_REVIEW_SCHEMA",
    "audit_mini_task_result",
    "build_acquisition_outcome_receipt",
    "build_domain_readiness_record",
    "build_skill_candidate",
    "create_citation",
    "create_claim_record",
    "create_glossary_entry",
    "detect_contradictions",
    "define_mini_task",
    "evaluate_phase30_gate",
    "extract_concept",
    "ingest_source",
    "link_evidence",
    "promote_to_memory",
    "request_memory_promotion",
    "require_review_if_stale",
    "review_freshness",
    "source_quality_is_advisory",
    "trust_result",
    "validate_phase30_proof_bundle",
]
