"""Citation extractor — DOI, arXiv, URL, reference patterns.

Citation is not proof. DOI/arXiv metadata is not truth.
No paywall bypass. No login. No promotion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

DOI_PATTERN = re.compile(r'10\.\d{4,}/[^\s,;"\'>}\]\)]+')
ARXIV_NEW_PATTERN = re.compile(r'(?:arXiv:?\s*)?(\d{4}\.\d{4,5}(?:v\d+)?)', re.IGNORECASE)
ARXIV_OLD_PATTERN = re.compile(r'arXiv:?\s*([a-z-]+/\d{7}(?:v\d+)?)', re.IGNORECASE)
URL_PATTERN = re.compile(r'https?://[^\s,;"\'>}\]]+')


@dataclass
class CitationCandidate:
    raw_text: str
    detected_type: str  # doi | arxiv | url | reference_line
    normalized_id: str
    candidate_url: str = ""
    line_number: int = 0
    safe_for_read: bool = True
    rejection_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "raw_text": self.raw_text[:200],
            "detected_type": self.detected_type,
            "normalized_id": self.normalized_id,
            "candidate_url": self.candidate_url,
            "line_number": self.line_number,
            "safe_for_read": self.safe_for_read,
            "rejection_reason": self.rejection_reason,
            "citation_is_not_proof": True,
            "promotion_allowed": False,
            "operator_review_required": True,
        }


def _normalize_doi(doi: str) -> str:
    return doi.lower().strip().rstrip(".")


def _normalize_arxiv(arxiv_id: str) -> str:
    return arxiv_id.strip()


def _is_url_safe(url: str) -> tuple[bool, str]:
    try:
        from hg_runtime.source_grounding.read_only_web_retriever import is_url_safe_for_read
        return is_url_safe_for_read(url)
    except ImportError:
        lower = url.lower()
        if any(x in lower for x in ["127.0.0.1", "localhost", "192.168.", "10.", "172.16."]):
            return False, "private/internal URL"
        if any(x in lower for x in ["/login", "/signin", "/auth", "/register"]):
            return False, "login/auth URL"
        return True, ""


def extract_citations(text: str) -> list[CitationCandidate]:
    candidates = []
    seen_ids: set[str] = set()

    for i, line in enumerate(text.split("\n"), 1):
        for match in DOI_PATTERN.finditer(line):
            doi = _normalize_doi(match.group())
            if doi in seen_ids:
                continue
            seen_ids.add(doi)
            candidates.append(CitationCandidate(
                raw_text=match.group(),
                detected_type="doi",
                normalized_id=doi,
                candidate_url=f"https://doi.org/{doi}",
                line_number=i,
            ))

        for pattern in (ARXIV_NEW_PATTERN, ARXIV_OLD_PATTERN):
            for match in pattern.finditer(line):
                arxiv_id = _normalize_arxiv(match.group(1))
                if arxiv_id in seen_ids:
                    continue
                seen_ids.add(arxiv_id)
                candidates.append(CitationCandidate(
                    raw_text=match.group(),
                    detected_type="arxiv",
                    normalized_id=arxiv_id,
                    candidate_url=f"https://arxiv.org/abs/{arxiv_id}",
                    line_number=i,
                ))

        for match in URL_PATTERN.finditer(line):
            url = match.group().rstrip(".")
            if url in seen_ids:
                continue
            if "doi.org" in url or "arxiv.org" in url:
                continue
            seen_ids.add(url)
            safe, reason = _is_url_safe(url)
            candidates.append(CitationCandidate(
                raw_text=url,
                detected_type="url",
                normalized_id=url,
                candidate_url=url,
                line_number=i,
                safe_for_read=safe,
                rejection_reason=reason,
            ))

    return candidates
