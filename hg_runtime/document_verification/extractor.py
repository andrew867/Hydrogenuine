"""Text extraction from Markdown, DOCX, and PDF."""

from __future__ import annotations

from pathlib import Path


def extract_markdown(md_path: str) -> tuple[str, str]:
    p = Path(md_path)
    if not p.exists():
        return "", "missing"
    return p.read_text(encoding="utf-8", errors="replace"), "markdown-direct"


def extract_docx(docx_path: str) -> tuple[str, str]:
    p = Path(docx_path)
    if not p.exists():
        return "", "missing"
    try:
        import docx
        doc = docx.Document(str(p))
        text = "\n".join(para.text for para in doc.paragraphs)
        return text, "python-docx"
    except Exception:
        return "", "python-docx unavailable"


def extract_pdf(pdf_path: str) -> tuple[str, str]:
    p = Path(pdf_path)
    if not p.exists():
        return "", "missing"
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(p))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        return text, "pypdf"
    except Exception:
        pass
    try:
        from PyPDF2 import PdfReader  # type: ignore
        reader = PdfReader(str(p))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        return text, "PyPDF2"
    except Exception:
        return "", "pdf text extractor unavailable"
