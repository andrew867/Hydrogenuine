"""Pack 12: Deterministic chunking with provenance (page/section range). Target 400-800 tokens (approx chars/4)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# Target chunk size in chars (approx 400-800 tokens at ~4 chars/token)
CHUNK_TARGET_CHARS = 2400
CHUNK_OVERLAP_CHARS = 200


def chunk_pages(pages: List[Tuple[int, str]]) -> List[Tuple[str, int, int, Dict[str, Any]]]:
    """Chunk a list of (page_no, text) into (text, page_start, page_end, provenance). Deterministic."""
    if not pages:
        return []
    merged = []
    for page_no, text in pages:
        merged.append((page_no, (text or "").strip()))
    return _chunk_sequence(merged, "page")


def chunk_paragraphs(paragraphs: List[Tuple[int, str, str]]) -> List[Tuple[str, int, int, Dict[str, Any]]]:
    """Chunk (paragraph_idx, section, text) into (text, page_start, page_end, provenance).

    DOCX chapter/heading boundaries matter for decomposition. Keep chunks section-local so a
    five-chapter document can become five planner-visible segments instead of one merged blob.
    """
    if not paragraphs:
        return []
    out: List[Tuple[str, int, int, Dict[str, Any]]] = []
    current_section: Optional[str] = None
    section_rows: List[Tuple[int, str, Dict[str, Any]]] = []

    def flush_section() -> None:
        nonlocal section_rows
        if not section_rows:
            return
        out.extend(_chunk_sequence(section_rows, "paragraph"))
        section_rows = []

    for para_idx, section, text in paragraphs:
        normalized_text = (text or "").strip()
        normalized_section = (section or "").strip() or "Body"
        if not normalized_text:
            continue
        if current_section is None:
            current_section = normalized_section
        elif normalized_section != current_section:
            flush_section()
            current_section = normalized_section
        section_rows.append((para_idx, normalized_text, {"section": normalized_section}))
    flush_section()
    return out


def _chunk_sequence(
    items: List[Tuple[int, str, Dict[str, Any]] | Tuple[int, str]],
    key: str,
) -> List[Tuple[str, int, int, Dict[str, Any]]]:
    """Items are (index, text). Produce chunks with overlap; each chunk has start/end index and provenance."""
    out: List[Tuple[str, int, int, Dict[str, Any]]] = []
    current: List[str] = []
    current_meta: List[Dict[str, Any]] = []
    current_len = 0
    start_idx: Optional[int] = None
    for raw in items:
        if len(raw) == 2:
            idx, text = raw
            meta = {}
        else:
            idx, text, meta = raw
        if not text:
            continue
        current.append(text)
        current_meta.append(meta)
        current_len += len(text) + 1
        if start_idx is None:
            start_idx = idx
        if current_len >= CHUNK_TARGET_CHARS:
            chunk_text = " ".join(current)
            out.append((chunk_text, start_idx, idx, _merge_provenance(current_meta, key, start_idx, idx)))
            overlap_text = []
            overlap_meta = []
            overlap_len = 0
            while current and overlap_len < CHUNK_OVERLAP_CHARS:
                t = current.pop(0)
                m = current_meta.pop(0)
                overlap_text.append(t)
                overlap_meta.append(m)
                overlap_len += len(t) + 1
            current = overlap_text
            current_meta = overlap_meta
            current_len = overlap_len
            start_idx = idx if not overlap_text else start_idx
    if current:
        chunk_text = " ".join(current)
        end_raw = items[-1] if items else None
        end_idx = end_raw[0] if end_raw else start_idx if start_idx is not None else 0
        out.append((chunk_text, start_idx or 0, end_idx, _merge_provenance(current_meta, key, start_idx or 0, end_idx)))
    return out


def _merge_provenance(meta_rows: List[Dict[str, Any]], key: str, start_idx: int, end_idx: int) -> Dict[str, Any]:
    out: Dict[str, Any] = {f"{key}_start": start_idx, f"{key}_end": end_idx}
    sections = [str((meta or {}).get("section") or "").strip() for meta in meta_rows if str((meta or {}).get("section") or "").strip()]
    if sections:
        out["section"] = sections[0]
    return out
