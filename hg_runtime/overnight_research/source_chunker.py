"""Source text chunking with keyword-aware selection.

Compression is lossy and must be receipted. Source excerpt is not
source truth. No promotion. Operator review required.
"""

from __future__ import annotations

import hashlib

TOPIC_KEYWORDS = (
    "theorem", "proof", "axiom", "definition", "equation", "formal",
    "grammar", "syntax", "semantics", "self-reference", "fixed point",
    "cognition", "information", "consciousness", "teleology", "telic",
    "metaphysical", "ontological", "reality", "universe", "language",
)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def chunk_source(
    text: str,
    *,
    max_chars: int = 1200,
    question: str = "",
) -> tuple[str, dict]:
    if not text:
        receipt = {
            "original_chars": 0,
            "selected_chars": 0,
            "compression_ratio": 1.0,
            "selection_strategy": "empty_source",
            "selected_offsets": [],
            "excerpt_hash": _hash_text(""),
            "compression_is_lossy": False,
            "excerpt_is_not_full_source": False,
            "promotion_allowed": False,
        }
        return "", receipt

    if len(text) <= max_chars:
        receipt = {
            "original_chars": len(text),
            "selected_chars": len(text),
            "compression_ratio": 1.0,
            "selection_strategy": "full_text_fits",
            "selected_offsets": [[0, len(text)]],
            "excerpt_hash": _hash_text(text),
            "compression_is_lossy": False,
            "excerpt_is_not_full_source": False,
            "promotion_allowed": False,
        }
        return text, receipt

    lines = text.split("\n")

    header_budget = max(max_chars // 4, 200)
    keyword_budget = max_chars - header_budget

    header_lines = []
    header_chars = 0
    for line in lines[:20]:
        if header_chars + len(line) + 1 > header_budget:
            break
        header_lines.append(line)
        header_chars += len(line) + 1

    q_words = set()
    if question:
        q_words = {w.lower() for w in question.split() if len(w) > 3}
    all_keywords = set(TOPIC_KEYWORDS) | q_words

    scored = []
    for i, line in enumerate(lines):
        if i < len(header_lines):
            continue
        lower = line.lower()
        score = sum(1 for kw in all_keywords if kw in lower)
        if score > 0:
            scored.append((score, i, line))

    scored.sort(key=lambda x: (-x[0], x[1]))

    keyword_lines = []
    keyword_chars = 0
    selected_indices = set()
    for score, idx, line in scored:
        if keyword_chars + len(line) + 1 > keyword_budget:
            break
        keyword_lines.append((idx, line))
        keyword_chars += len(line) + 1
        selected_indices.add(idx)

    keyword_lines.sort(key=lambda x: x[0])

    parts = []
    offsets = []

    if header_lines:
        h_text = "\n".join(header_lines)
        parts.append(h_text)
        offsets.append([0, header_chars])

    if keyword_lines:
        if header_lines:
            parts.append("\n[...]\n")
        k_text = "\n".join(line for _, line in keyword_lines)
        parts.append(k_text)
        for idx, line in keyword_lines:
            char_offset = sum(len(lines[j]) + 1 for j in range(idx))
            offsets.append([char_offset, char_offset + len(line)])

    result = "\n".join(parts) if not keyword_lines else parts[0] + (parts[1] if len(parts) > 1 else "") + (parts[2] if len(parts) > 2 else "")

    if len(result) > max_chars:
        result = result[:max_chars]

    receipt = {
        "original_chars": len(text),
        "selected_chars": len(result),
        "compression_ratio": round(len(result) / len(text), 3) if text else 1.0,
        "selection_strategy": "header_plus_keyword",
        "selected_offsets": offsets,
        "excerpt_hash": _hash_text(result),
        "compression_is_lossy": True,
        "excerpt_is_not_full_source": True,
        "promotion_allowed": False,
    }

    return result, receipt
