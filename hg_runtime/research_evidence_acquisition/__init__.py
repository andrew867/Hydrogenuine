"""RES research / evidence acquisition — offline records only."""

from hg_runtime.research_evidence_acquisition.policy import evaluate_research_request
from hg_runtime.research_evidence_acquisition.records import record_from_provided_file
from hg_runtime.research_evidence_acquisition.types import EvidenceRecord, ResearchRequest

__all__ = [
    "EvidenceRecord",
    "ResearchRequest",
    "evaluate_research_request",
    "record_from_provided_file",
]
