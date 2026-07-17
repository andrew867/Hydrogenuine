"""RES research policy — evidence acquisition is not truth."""

from __future__ import annotations

from typing import Mapping, Optional

from hg_core.runtime_context.config import res_offline_only
from hg_core.runtime_context.errors import (
    REFUSED_AUTONOMOUS_CRAWL,
    REFUSED_RESEARCH_AS_TRUTH,
    REFUSED_STALE_SOURCE,
    REFUSED_UNKNOWN_PRESERVED,
    REFUSED_UNSUPPORTED_CLAIM,
    RuntimeContextValidationError,
)
from hg_core.runtime_context.no_authority import advisory_only_marker
from hg_runtime.research_evidence_acquisition.types import EvidenceRecord, ResearchRequest, request_from_fixture


def evaluate_research_request(
    request: ResearchRequest,
    *,
    evidence: Optional[EvidenceRecord] = None,
    observed_at: Optional[str] = None,
) -> dict[str, object]:
    """Return advisory research evaluation; research is not truth."""
    if res_offline_only() and request.acquisition_mode in {"approved_web_search", "approved_api", "unknown"}:
        raise RuntimeContextValidationError(
            REFUSED_AUTONOMOUS_CRAWL,
            "offline-only mode refuses autonomous crawl acquisition modes",
        )
    if evidence is None and request.uncertainty.strip().lower() == "unknown until supported":
        return {
            **advisory_only_marker(),
            "status": "unknown_preserved",
            "reason_code": REFUSED_UNKNOWN_PRESERVED,
            "request_id": request.request_id,
            "research_is_truth": False,
        }
    if evidence is None:
        raise RuntimeContextValidationError(
            REFUSED_UNSUPPORTED_CLAIM,
            "claim without evidence record is unsupported",
        )
    if observed_at and observed_at > evidence.expires_at:
        return {
            **advisory_only_marker(),
            "status": "stale",
            "reason_code": REFUSED_STALE_SOURCE,
            "evidence_id": evidence.evidence_id,
            "research_is_truth": False,
        }
    if evidence.support_level in {"contradicted", "unknown"}:
        return {
            **advisory_only_marker(),
            "status": "unsupported",
            "reason_code": REFUSED_UNSUPPORTED_CLAIM,
            "evidence_id": evidence.evidence_id,
            "research_is_truth": False,
        }
    return {
        **advisory_only_marker(),
        "status": "evidence_recorded",
        "reason_code": "res.advisory.evidence_recorded",
        "request_id": request.request_id,
        "evidence_id": evidence.evidence_id,
        "research_is_truth": False,
    }


def refuse_research_as_truth(*, treat_as_truth: bool) -> None:
    if treat_as_truth:
        raise RuntimeContextValidationError(
            REFUSED_RESEARCH_AS_TRUTH,
            "research result cannot be treated as truth or permission",
        )


def evaluate_fixture(fixture: Mapping[str, str], *, observed_at: str) -> dict[str, object]:
    request = request_from_fixture(dict(fixture))
    evidence = None
    if fixture.get("evidence_id"):
        from hg_runtime.research_evidence_acquisition.records import record_from_provided_file

        evidence = record_from_provided_file(fixture)
    return evaluate_research_request(request, evidence=evidence, observed_at=observed_at)


__all__ = ["evaluate_fixture", "evaluate_research_request", "refuse_research_as_truth"]
