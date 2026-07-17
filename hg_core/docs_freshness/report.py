"""Claim-check report builder (CT-17 DOC)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hg_core.docs_freshness.claims import ClaimFinding


@dataclass
class ClaimCheckReport:
    ok: bool
    head: str
    docs_scanned: int
    findings: list[ClaimFinding] = field(default_factory=list)
    todos: list[str] = field(default_factory=list)
    deferred: list[str] = field(default_factory=list)
    checks: list[dict[str, Any]] = field(default_factory=list)
    proof_topics: dict[str, bool] = field(default_factory=dict)
    timeline: dict[str, Any] = field(default_factory=dict)
    phase_reports: dict[str, str] = field(default_factory=dict)
    citation_lint: dict[str, Any] = field(default_factory=dict)

    def critical_findings(self) -> list[ClaimFinding]:
        return [f for f in self.findings if f.severity == "critical"]

    def to_payload(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "head": self.head,
            "docs_scanned": self.docs_scanned,
            "findings": [f.to_payload() for f in self.findings],
            "todos": self.todos,
            "deferred": self.deferred,
            "checks": self.checks,
            "proof_topics": self.proof_topics,
            "timeline": self.timeline,
            "phase_reports": self.phase_reports,
            "citation_lint": self.citation_lint,
            "critical_count": len(self.critical_findings()),
        }


def build_status_markdown(report: ClaimCheckReport, *, title: str = "CT-17 DOC claim check") -> str:
    lines = [
        f"# {title}",
        "",
        f"**HEAD:** `{report.head}`",
        f"**Verdict:** {'GREEN' if report.ok else 'RED'}",
        f"**Docs scanned:** {report.docs_scanned}",
        "",
        "## Checks",
    ]
    for check in report.checks:
        verdict = check.get("verdict", "unknown")
        name = check.get("check", "unknown")
        lines.append(f"- `{name}`: {verdict}")
    lines.extend(["", "## Proof topics"])
    for topic, proven in sorted(report.proof_topics.items()):
        lines.append(f"- `{topic}`: {'proven' if proven else 'not_proven'}")
    lines.extend(["", "## TODOs"])
    if report.todos:
        lines.extend(f"- {item}" for item in report.todos)
    else:
        lines.append("- none")
    lines.extend(["", "## Deferred / not proven"])
    if report.deferred:
        lines.extend(f"- {item}" for item in report.deferred)
    else:
        lines.append("- none")
    if report.findings:
        lines.extend(["", "## Findings"])
        for finding in report.findings[:50]:
            lines.append(
                f"- `{finding.file}:{finding.line}` [{finding.severity}] {finding.check}: {finding.detail}"
            )
        if len(report.findings) > 50:
            lines.append(f"- … and {len(report.findings) - 50} more")
    return "\n".join(lines) + "\n"


__all__ = ["ClaimCheckReport", "build_status_markdown"]
