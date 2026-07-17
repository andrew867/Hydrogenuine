"""Schemas for document rendering and verification."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RenderManifest:
    document_id: str
    source_markdown: str
    md_path: str = ""
    docx_path: str = ""
    pdf_path: str = ""
    render_attempted: bool = False
    md_rendered: bool = False
    docx_rendered: bool = False
    pdf_rendered: bool = False
    toolchain_used: dict = field(default_factory=dict)
    toolchain_available: dict = field(default_factory=dict)
    toolchain_missing_reasons: dict = field(default_factory=dict)
    source_hash: str = ""
    md_hash: str = ""
    docx_hash: str = ""
    pdf_hash: str = ""


@dataclass
class VerificationReport:
    document_id: str
    source_markdown: str
    docx_path: str = ""
    pdf_path: str = ""
    render_attempted: bool = False
    docx_rendered: bool = False
    pdf_rendered: bool = False
    docx_verified: bool = False
    pdf_verified: bool = False
    verification_passed: bool = False
    required_sections_present: list[str] = field(default_factory=list)
    required_sections_missing: list[str] = field(default_factory=list)
    forbidden_claims_found: list[str] = field(default_factory=list)
    secret_patterns_found: list[str] = field(default_factory=list)
    extraction_method: str = ""
    toolchain_available: dict = field(default_factory=dict)
    toolchain_missing_reasons: dict = field(default_factory=dict)
    source_hash: str = ""
    docx_hash: str = ""
    pdf_hash: str = ""
    verifier_receipt_hash: str = ""
