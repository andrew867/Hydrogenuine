"""Evidence summarizer — turn redacted content into a source-attributed digest.

Every external claim entering an AdvisoryObject is source/evidence-labelled.
The summary carries no imperative content: it describes, it never directs.
"""

from __future__ import annotations

import re

from hg_runtime.trust_boundary.schema import EvidenceClaim, EvidenceSummary

# Imperative-mood lead verbs that must not survive into a summary as commands.
_IMPERATIVE_LEAD = re.compile(
    r"(?im)^\s*(ignore|disregard|send|post|publish|create|delete|execute|run|call|email|buy|transfer|reveal|print)\b"
)


def neutralize_imperatives(text: str) -> str:
    """Re-frame imperative lines as reported content, not commands."""
    out_lines = []
    for line in text.splitlines():
        if _IMPERATIVE_LEAD.match(line):
            out_lines.append(f"(reported text) {line.strip()}")
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


def summarize_as_evidence(content: str, *, source: str, max_chars: int = 600) -> EvidenceSummary:
    neutral = neutralize_imperatives(content).strip()
    digest = neutral[:max_chars]
    claim = EvidenceClaim(claim=digest, source=source)
    summary_text = f"According to {source}: {digest}"
    return EvidenceSummary(summary=summary_text, claims=[claim])


__all__ = ["neutralize_imperatives", "summarize_as_evidence"]
