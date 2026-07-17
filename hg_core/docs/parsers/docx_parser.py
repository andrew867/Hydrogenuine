"""Pack 12: DOCX paragraph extraction with section order."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

def parse_docx_paragraphs(path: Path) -> List[Tuple[int, str, str]]:
    """Extract paragraphs with (paragraph_idx, section_name, text). Section from heading or default."""
    try:
        from docx import Document
    except ImportError:
        raise ImportError("python-docx is required for DOCX parsing; install with pip install python-docx")
    doc = Document(str(path))
    out: List[Tuple[int, str, str]] = []
    section = "Body"
    for i, para in enumerate(doc.paragraphs):
        text = (para.text or "").strip()
        if not text:
            continue
        style = (para.style and para.style.name or "").lower()
        if "heading" in style:
            section = text
        out.append((i, section, text))
    return out
