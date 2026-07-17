"""Document verifier — extracts text and checks sections/claims/secrets.

Rendered document existence is NOT truth. Verification checks content, not visuals.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .schemas import RenderManifest, VerificationReport
from .extractor import extract_markdown, extract_docx, extract_pdf


_FORBIDDEN_CLAIM_PATTERNS = [
    r"\bis\s+agi\b",
    r"\bis\s+conscious\b",
    r"\bis\s+sovereign\b",
    r"\bdeployment\s+ready\b",
    r"\bfield\s+ready\b",
    r"\bfully\s+autonomous\b",
    r"\bproduction\s+ready\b",
]

_SECRET_PATTERNS = [
    r"sk-[a-zA-Z0-9]{16,}",
    r"api[_-]?key\s*[:=]\s*['\"]?[a-zA-Z0-9]{16,}",
    r"bearer\s+[a-zA-Z0-9._-]{20,}",
    r"password\s*[:=]\s*['\"]?\S{6,}",
]


def _find_forbidden_claims(text: str) -> list[str]:
    found = []
    low = text.lower()
    for pat in _FORBIDDEN_CLAIM_PATTERNS:
        if re.search(pat, low):
            found.append(pat)
    return found


def _find_secrets(text: str) -> list[str]:
    found = []
    for pat in _SECRET_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            found.append(pat)
    return found


def verify_document(
    manifest: RenderManifest,
    required_sections: list[str],
    required_boundary_phrases: list[str] | None = None,
) -> VerificationReport:
    required_boundary_phrases = required_boundary_phrases or []

    md_text, md_method = extract_markdown(manifest.md_path)

    report = VerificationReport(
        document_id=manifest.document_id,
        source_markdown=manifest.source_markdown,
        docx_path=manifest.docx_path,
        pdf_path=manifest.pdf_path,
        render_attempted=manifest.render_attempted,
        docx_rendered=manifest.docx_rendered,
        pdf_rendered=manifest.pdf_rendered,
        extraction_method=md_method,
        toolchain_available=dict(manifest.toolchain_available),
        toolchain_missing_reasons=dict(manifest.toolchain_missing_reasons),
        source_hash=manifest.source_hash,
        docx_hash=manifest.docx_hash,
        pdf_hash=manifest.pdf_hash,
    )

    # Required sections (checked against the canonical markdown source).
    present, missing = [], []
    for sec in required_sections:
        if sec.lower() in md_text.lower():
            present.append(sec)
        else:
            missing.append(sec)
    report.required_sections_present = present
    report.required_sections_missing = missing

    # Boundary phrases must be present.
    for phrase in required_boundary_phrases:
        if phrase.lower() not in md_text.lower():
            missing.append(f"boundary:{phrase}")
    report.required_sections_missing = missing

    # Forbidden claims / secrets.
    report.forbidden_claims_found = _find_forbidden_claims(md_text)
    report.secret_patterns_found = _find_secrets(md_text)

    # Verify DOCX/PDF content matches source where rendered.
    if manifest.docx_rendered and manifest.docx_path:
        docx_text, _ = extract_docx(manifest.docx_path)
        report.docx_verified = bool(docx_text) and _content_overlaps(md_text, docx_text)
    if manifest.pdf_rendered and manifest.pdf_path:
        pdf_text, _ = extract_pdf(manifest.pdf_path)
        report.pdf_verified = bool(pdf_text) and _content_overlaps(md_text, pdf_text)

    # Hash check: re-hash source bytes and compare to manifest (byte-exact,
    # matching the renderer's _hash_file which hashes raw file bytes).
    actual_source_hash = ""
    p = Path(manifest.md_path)
    if p.exists():
        actual_source_hash = hashlib.sha256(p.read_bytes()).hexdigest()
    hash_ok = (actual_source_hash == manifest.md_hash) if manifest.md_hash else True

    report.verification_passed = (
        len(missing) == 0
        and len(report.forbidden_claims_found) == 0
        and len(report.secret_patterns_found) == 0
        and hash_ok
    )
    report.verifier_receipt_hash = hashlib.sha256(
        f"{manifest.document_id}:{report.verification_passed}".encode("utf-8")).hexdigest()
    return report


def _content_overlaps(source: str, extracted: str) -> bool:
    """Cheap overlap check: a few source tokens appear in extracted text."""
    src_tokens = [t for t in re.findall(r"[A-Za-z]{5,}", source)][:20]
    if not src_tokens:
        return True
    hits = sum(1 for t in src_tokens if t.lower() in extracted.lower())
    return hits >= max(1, len(src_tokens) // 4)
