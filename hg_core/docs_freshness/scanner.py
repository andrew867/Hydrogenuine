"""Docs freshness scanner orchestrator (CT-17 DOC)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from hg_core.docs_freshness.claims import (
    ClaimFinding,
    scan_forbidden_complete,
    scan_future_labels,
    scan_head_binding,
    scan_status_table_rows,
)
from hg_core.docs_freshness.proof_index import build_proof_index, extract_head_from_doc
from hg_core.docs_freshness.registry import (
    enumerate_claim_bearing_docs,
    load_claim_rules,
    load_registry,
)
from hg_core.docs_freshness.report import ClaimCheckReport
from hg_core.docs_freshness.timeline import check_master_timeline
from hg_core.parity.citations import lint_reports


def _git_head(workspace: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _collect_todos_deferred(text: str, rel_path: str) -> tuple[list[str], list[str]]:
    todos: list[str] = []
    deferred: list[str] = []
    for index, line in enumerate(text.splitlines(), start=1):
        lowered = line.lower()
        if "todo" in lowered or "- [ ]" in line:
            todos.append(f"{rel_path}:{index}: {line.strip()[:120]}")
        if any(token in lowered for token in ("deferred", "not_proven", "backburner", "future")):
            deferred.append(f"{rel_path}:{index}: {line.strip()[:120]}")
    return todos, deferred


def _phase_reports_exist(workspace: Path, mapping: dict[str, str]) -> tuple[bool, dict[str, str]]:
    status: dict[str, str] = {}
    missing = False
    for phase, rel in mapping.items():
        exists = (workspace / rel).exists()
        status[phase] = "present" if exists else "missing"
        if not exists:
            missing = True
    return not missing, status


def run_claim_check(
    workspace: Path,
    *,
    extra_paths: list[Path] | None = None,
    skip_globs: tuple[str, ...] = (),
    include_citation_lint: bool = True,
) -> ClaimCheckReport:
    registry = load_registry(workspace=workspace)
    rules = load_claim_rules(workspace=workspace)
    head = _git_head(workspace)
    proof_index = build_proof_index(workspace, rules.proof_topics)

    docs = enumerate_claim_bearing_docs(workspace, registry)
    if extra_paths:
        seen = {d.resolve() for d in docs}
        for path in extra_paths:
            resolved = path.resolve()
            if resolved not in seen and path.exists():
                docs.append(path)
                seen.add(resolved)

    findings: list[ClaimFinding] = []
    todos: list[str] = []
    deferred: list[str] = []
    head_binding_set = {p.replace("\\", "/") for p in registry.head_binding_paths}

    for doc_path in docs:
        rel = str(doc_path.relative_to(workspace)).replace("\\", "/")
        if any(Path(rel).match(pattern) for pattern in skip_globs):
            continue
        try:
            text = doc_path.read_text(encoding="utf-8")
        except OSError:
            findings.append(
                ClaimFinding(
                    file=rel,
                    line=0,
                    check="readable",
                    severity="fail",
                    detail="could not read claim-bearing doc",
                )
            )
            continue

        require_head = rel in head_binding_set or extract_head_from_doc(text) is not None
        findings.extend(scan_head_binding(rel, text, current_head=head, require_binding=require_head))
        findings.extend(scan_forbidden_complete(rel, text, rules=rules, proof_index=proof_index))
        findings.extend(scan_status_table_rows(rel, text, rules=rules))
        if "MASTER_TIMELINE" in rel or "18_MASTER" in rel:
            findings.extend(scan_future_labels(rel, text))
        doc_todos, doc_deferred = _collect_todos_deferred(text, rel)
        todos.extend(doc_todos)
        deferred.extend(doc_deferred)

    phase_ok, phase_status = _phase_reports_exist(workspace, registry.ct_phase_reports)
    if not phase_ok:
        for phase, status in phase_status.items():
            if status == "missing":
                findings.append(
                    ClaimFinding(
                        file=registry.ct_phase_reports[phase],
                        line=0,
                        check="phase_report_exists",
                        severity="fail",
                        detail=f"missing phase report for {phase}",
                    )
                )

    timeline = check_master_timeline(workspace, registry.master_timeline)
    if not timeline["ok"]:
        for item in timeline["findings"]:
            findings.append(
                ClaimFinding(
                    file=registry.master_timeline,
                    line=int(item.get("line", 0)),
                    check="master_timeline_links",
                    severity="fail",
                    detail=str(item.get("detail", "broken link")),
                )
            )

    skeleton_path = workspace / registry.sotu_skeleton
    if not skeleton_path.exists():
        findings.append(
            ClaimFinding(
                file=registry.sotu_skeleton,
                line=0,
                check="sotu_skeleton_exists",
                severity="fail",
                detail="State of the Union CT refresh skeleton missing",
            )
        )

    citation_lint: dict[str, Any] = {"ok": True, "skipped": not include_citation_lint}
    if include_citation_lint:
        citation_lint = lint_reports(workspace, report_globs=("docs/reports/phases/CT*_STATUS.md",))
        if not citation_lint.get("ok", True):
            for item in citation_lint.get("findings", []):
                findings.append(
                    ClaimFinding(
                        file=str(item.get("file", "")),
                        line=int(item.get("line", 0)),
                        check="claim_citation",
                        severity="fail",
                        detail=str(item.get("detail", "citation lint")),
                    )
                )

    checks: list[dict[str, Any]] = [
        {"check": "claim_bearing_docs_registered", "verdict": "pass" if docs else "fail"},
        {
            "check": "head_binding_or_banner",
            "verdict": "pass"
            if not any(f.check == "head_binding_or_banner" for f in findings)
            else "fail",
        },
        {"check": "phase_reports_exist", "verdict": "pass" if phase_ok else "fail"},
        {"check": "master_timeline_links", "verdict": "pass" if timeline["ok"] else "fail"},
        {
            "check": "unsupported_complete_claim",
            "verdict": "pass"
            if not any(f.check == "unsupported_complete_claim" for f in findings)
            else "fail",
        },
        {
            "check": "sotu_skeleton_exists",
            "verdict": "pass" if skeleton_path.exists() else "fail",
        },
        {
            "check": "claims_cited_and_path_labeled",
            "verdict": "pass" if citation_lint.get("ok", True) else "fail",
        },
    ]

    critical = [f for f in findings if f.severity == "critical"]
    ok = not findings and phase_ok and timeline["ok"] and skeleton_path.exists()

    if not proof_index.topic_proven("dep_soak"):
        deferred.append("dep_soak: no proof bundle — docs must not claim 72h soak passed")
    if not proof_index.topic_proven("live_cognition_live"):
        deferred.append("live_cognition_live: live battery not_proven in latest pack13 bundle")
    if not proof_index.topic_proven("oea_live_actuation"):
        deferred.append("oea_live_actuation: no live actuation proof bundle")

    def _dedupe(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            out.append(item)
        return out

    return ClaimCheckReport(
        ok=ok,
        head=head,
        docs_scanned=len(docs),
        findings=findings,
        todos=_dedupe(todos)[:100],
        deferred=_dedupe(deferred)[:100],
        checks=checks,
        proof_topics=dict(proof_index.topics),
        timeline=timeline,
        phase_reports=phase_status,
        citation_lint=citation_lint,
    )


__all__ = ["run_claim_check"]
