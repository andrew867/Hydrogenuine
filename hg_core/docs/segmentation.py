from __future__ import annotations

from typing import Any, Dict, List


def build_segment_groups(
    chunks: List[Any],
    *,
    requested_count: int | None = None,
) -> List[Dict[str, Any]]:
    if not chunks:
        return []
    by_section = _group_by_section(chunks)
    if len(by_section) >= 2:
        return by_section
    return _group_by_ranges(chunks, requested_count=requested_count)


def _group_by_section(chunks: List[Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    current: Dict[str, Any] | None = None
    for chunk in chunks:
        provenance = getattr(chunk, "provenance", None) or {}
        section = str(provenance.get("section") or "").strip()
        if not section:
            return []
        if current is None or current["label"] != section:
            if current is not None:
                out.append(current)
            current = _new_group(chunks[0].document_id, section)
        _append_chunk(current, chunk)
    if current is not None:
        out.append(current)
    return _finalize_groups(out)


def _group_by_ranges(chunks: List[Any], *, requested_count: int | None) -> List[Dict[str, Any]]:
    count = max(1, min(requested_count or len(chunks), len(chunks)))
    base = len(chunks) // count
    extra = len(chunks) % count
    groups: List[Dict[str, Any]] = []
    cursor = 0
    for idx in range(count):
        take = base + (1 if idx < extra else 0)
        selected = chunks[cursor : cursor + take]
        cursor += take
        if not selected:
            continue
        label = f"Segment {idx + 1}"
        group = _new_group(selected[0].document_id, label)
        for chunk in selected:
            _append_chunk(group, chunk)
        groups.append(group)
    return _finalize_groups(groups)


def _new_group(document_id: str, label: str) -> Dict[str, Any]:
    return {
        "segment_id": "",
        "document_id": document_id,
        "label": label,
        "chunk_ids": [],
        "chunk_count": 0,
        "page_start": None,
        "page_end": None,
    }


def _append_chunk(group: Dict[str, Any], chunk: Any) -> None:
    group["chunk_ids"].append(chunk.chunk_id)
    group["chunk_count"] += 1
    start = getattr(chunk, "page_start", None)
    end = getattr(chunk, "page_end", None)
    if group["page_start"] is None or (start is not None and start < group["page_start"]):
        group["page_start"] = start
    if group["page_end"] is None or (end is not None and end > group["page_end"]):
        group["page_end"] = end


def _finalize_groups(groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for idx, group in enumerate(groups, start=1):
        group["segment_id"] = f"segment_{idx}"
    return groups
