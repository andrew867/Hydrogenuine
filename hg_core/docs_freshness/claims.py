"""Claim scanning helpers (CT-17 DOC)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from hg_core.docs_freshness.proof_index import ProofIndex
from hg_core.docs_freshness.registry import ClaimRules


@dataclass(frozen=True)
class ClaimFinding:
    file: str
    line: int
    check: str
    severity: str
    detail: str
    category: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "file": self.file,
            "line": self.line,
            "check": self.check,
            "severity": self.severity,
            "detail": self.detail,
        }
        if self.category:
            payload["category"] = self.category
        return payload


def _line_has_qualifier(text: str, qualifiers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(q in lowered for q in qualifiers)


def _context_window(lines: list[str], index: int, *, radius: int = 2) -> str:
    start = max(0, index - radius)
    end = min(len(lines), index + radius + 1)
    return "\n".join(lines[start:end])


def scan_forbidden_complete(
    rel_path: str,
    text: str,
    *,
    rules: ClaimRules,
    proof_index: ProofIndex,
) -> list[ClaimFinding]:
    findings: list[ClaimFinding] = []
    lines = text.splitlines()
    for rule in rules.forbidden_complete:
        topic = str(rule.get("topic", "unknown"))
        rule_id = str(rule.get("id", topic))
        proof_topic = str(rule.get("proof_topic", ""))
        if proof_topic and proof_index.topic_proven(proof_topic):
            continue
        patterns = [re.compile(p, re.IGNORECASE) for p in rule.get("patterns", [])]
        for index, line in enumerate(lines, start=1):
            if not any(p.search(line) for p in patterns):
                continue
            if re.search(r"\bpytest\b|tests/[a-z_]+", line, re.IGNORECASE):
                continue
            context = _context_window(lines, index - 1, radius=3)
            if _line_has_qualifier(context, rules.complete_qualifiers):
                continue
            findings.append(
                ClaimFinding(
                    file=rel_path,
                    line=index,
                    check="unsupported_complete_claim",
                    severity="critical",
                    detail=f"{topic}: unsupported complete/passed claim without proof ({rule_id})",
                    category="unknown",
                )
            )
    return findings


def scan_head_binding(
    rel_path: str,
    text: str,
    *,
    current_head: str,
    require_binding: bool,
) -> list[ClaimFinding]:
    if not require_binding:
        return []
    from hg_core.docs_freshness.proof_index import extract_head_from_doc, has_stale_banner

    findings: list[ClaimFinding] = []
    declared = extract_head_from_doc(text)
    if declared is None:
        findings.append(
            ClaimFinding(
                file=rel_path,
                line=1,
                check="head_binding_or_banner",
                severity="fail",
                detail="claim-bearing SOTU missing HEAD declaration",
            )
        )
        return findings
    if declared.startswith(current_head) or current_head.startswith(declared):
        return findings
    if has_stale_banner(text):
        return findings
    findings.append(
        ClaimFinding(
            file=rel_path,
            line=1,
            check="head_binding_or_banner",
            severity="fail",
            detail=f"HEAD mismatch: doc={declared} current={current_head[:12]} without STALE banner",
        )
    )
    return findings


def scan_status_table_rows(
    rel_path: str,
    text: str,
    *,
    rules: ClaimRules,
) -> list[ClaimFinding]:
    findings: list[ClaimFinding] = []
    lines = text.splitlines()
    in_table = False
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("|") and "---" in stripped:
            in_table = True
            continue
        if not in_table or not stripped.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        row_text = " ".join(cells).lower()
        for hedge in rules.hedge_patterns:
            if hedge in row_text:
                findings.append(
                    ClaimFinding(
                        file=rel_path,
                        line=index,
                        check="hedge_vocabulary_in_table",
                        severity="fail",
                        detail=f"status table hedge: {hedge}",
                        category="unknown",
                    )
                )
        for word, category in rules.status_word_map.items():
            if re.search(rf"\b{re.escape(word)}\b", row_text, re.IGNORECASE):
                if category in {"future", "unknown", "scaffold", "stub", "gated"}:
                    continue
                if word in {"complete", "implemented", "real"} and _line_has_qualifier(
                    row_text, rules.complete_qualifiers
                ):
                    continue
    return findings


def scan_future_labels(
    rel_path: str,
    text: str,
    *,
    backburner_modules: tuple[str, ...] = ("M4", "GPP", "HAL", "SOAR", "UEAK", "OEA", "RTC", "SRP", "PLT", "DEP"),
) -> list[ClaimFinding]:
    """Ensure backburner modules in status tables carry future/scaffold/stub labels."""
    findings: list[ClaimFinding] = []
    allowed = re.compile(
        r"\b(future|backburner|not started|planned|deferred|stub|scaffold|gated|unknown|🔲)\b",
        re.IGNORECASE,
    )
    lines = text.splitlines()
    for index, line in enumerate(lines, start=1):
        if not line.strip().startswith("|"):
            continue
        for module in backburner_modules:
            if module not in line:
                continue
            if re.search(rf"\b{module}\b.*\b(complete|implemented|real)\b", line, re.IGNORECASE):
                if not allowed.search(line):
                    findings.append(
                        ClaimFinding(
                            file=rel_path,
                            line=index,
                            check="future_module_label",
                            severity="fail",
                            detail=f"{module} appears complete without FUTURE/scaffold/stub label",
                            category="future",
                        )
                    )
    return findings


__all__ = [
    "ClaimFinding",
    "scan_forbidden_complete",
    "scan_future_labels",
    "scan_head_binding",
    "scan_status_table_rows",
]
