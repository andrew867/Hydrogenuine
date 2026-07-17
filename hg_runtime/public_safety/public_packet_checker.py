"""Public packet safety checker.

Scans morning packets, public summaries, dashboard text, bundle README/index,
and reports for unsafe public claims.

No AGI/consciousness/sentience/sovereignty framing.
No production-ready or enterprise-ready claims.
"Artificial Governed Intelligence" is a controlled phrase — allowed only with
the exact casing and context. Bare "AGI" remains unsafe.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

UNSAFE_TERMS = [
    "agi",
    "artificial general intelligence",
    "conscious",
    "sentient",
    "sovereign",
    "truth engine",
    "self-aware",
    "autonomous authority",
    "verified knowledge",
    "self-improving ai",
    "god model",
    "manifestation proof",
    "physics proof",
    "production ready",
    "production-ready",
    "enterprise ready",
    "enterprise-ready",
]

CONTROLLED_PHRASES = [
    "artificial governed intelligence",
]

NEGATION_MARKERS = [
    "not", "no", "cannot", "does not", "is not", "never",
    "without", "nor", "isn't", "doesn't", "can't", "won't",
    "!=", "false", "prohibited", "forbidden",
]


@dataclass
class PacketFlag:
    file: str
    line_number: int
    term: str
    context: str
    is_negated: bool = False


def _is_controlled_phrase_context(line_lower: str, term: str, idx: int) -> bool:
    if term != "agi" and term != "artificial general intelligence":
        return False
    for phrase in CONTROLLED_PHRASES:
        phrase_idx = line_lower.find(phrase)
        if phrase_idx != -1 and phrase_idx <= idx <= phrase_idx + len(phrase):
            return True
    if term == "agi":
        before = line_lower[max(0, idx - 40):idx]
        if "artificial governed intelligence" in before:
            return True
        after = line_lower[idx:idx + 50]
        if after.startswith("agi") and "artificial governed intelligence" in line_lower:
            return True
    return False


def scan_text(text: str, filename: str = "") -> list[PacketFlag]:
    flags = []
    for i, line in enumerate(text.split("\n"), 1):
        lower = line.lower()
        for term in UNSAFE_TERMS:
            idx = lower.find(term)
            if idx == -1:
                continue
            if _is_controlled_phrase_context(lower, term, idx):
                continue
            prefix = lower[max(0, idx - 80):idx]
            negated = any(neg in prefix for neg in NEGATION_MARKERS)
            flags.append(PacketFlag(
                file=filename,
                line_number=i,
                term=term,
                context=line.strip()[:120],
                is_negated=negated,
            ))
    return flags


def scan_file(filepath: str) -> list[PacketFlag]:
    if not os.path.isfile(filepath):
        return []
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    return scan_text(text, os.path.basename(filepath))


def scan_proof_dir(proof_dir: str) -> list[PacketFlag]:
    targets = [
        "morning_operator_packet.md",
        "public_safe_summary.md",
        "public_packet_safety_report.md",
    ]
    all_flags = []
    for fname in targets:
        all_flags.extend(scan_file(os.path.join(proof_dir, fname)))

    for fname in os.listdir(proof_dir) if os.path.isdir(proof_dir) else []:
        if fname.endswith(".md") and fname not in targets:
            all_flags.extend(scan_file(os.path.join(proof_dir, fname)))

    return all_flags


def build_report(flags: list[PacketFlag]) -> dict:
    affirmative = [f for f in flags if not f.is_negated]
    negated = [f for f in flags if f.is_negated]

    return {
        "schema_version": "public_packet_safety_v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_flags": len(flags),
        "affirmative_flags": len(affirmative),
        "negated_boundary_flags": len(negated),
        "safe": len(affirmative) == 0,
        "flags": [
            {
                "file": f.file,
                "line": f.line_number,
                "term": f.term,
                "context": f.context,
                "is_negated": f.is_negated,
            }
            for f in flags
        ],
        "recommendation": (
            "SAFE: no affirmative unsafe terms found"
            if len(affirmative) == 0
            else f"UNSAFE: {len(affirmative)} affirmative unsafe term(s) found — rephrase or remove"
        ),
        "promotion_allowed": False,
        "operator_review_required": True,
    }


def write_report(report: dict, out_dir: str) -> tuple[str, str]:
    os.makedirs(out_dir, exist_ok=True)

    json_path = os.path.join(out_dir, "public_packet_safety_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    lines = [
        "# Public Packet Safety Report",
        "",
        f"Safe: {report['safe']}",
        f"Total flags: {report['total_flags']}",
        f"Affirmative: {report['affirmative_flags']}",
        f"Negated/boundary: {report['negated_boundary_flags']}",
        f"Recommendation: {report['recommendation']}",
        "",
    ]
    for flag in report["flags"]:
        neg = "(negated/boundary)" if flag["is_negated"] else "**AFFIRMATIVE**"
        lines.append(f"- [{flag['file']}:{flag['line']}] `{flag['term']}` {neg}")
        lines.append(f"  > {flag['context']}")
    lines.extend(["", "---", "Operator review required. No promotion."])

    md_path = os.path.join(out_dir, "public_packet_safety_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return json_path, md_path
