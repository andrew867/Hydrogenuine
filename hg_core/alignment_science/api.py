"""
Layer 9 Phase 2: API for process audit — GET/POST by decision_id or run_id.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.alignment_science.process_audit import (
    get_process_audit,
    get_process_audit_for_run,
    run_process_audit,
)


def get_process_audit_api(
    workspace_root: Path,
    decision_id: Optional[str] = None,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    GET process audit: return ProcessAuditResult for decision_id, or list for run_id.
    Returns { "ok": True, "result": ... } or { "ok": True, "results": [...] } or { "ok": False, "error": "not_found" }.
    """
    workspace_root = Path(workspace_root)
    if decision_id:
        result = get_process_audit(workspace_root, decision_id)
        if result is None:
            return {"ok": False, "error": "not_found", "decision_id": decision_id}
        return {"ok": True, "result": result}
    if run_id:
        results = get_process_audit_for_run(workspace_root, run_id)
        return {"ok": True, "results": results}
    return {"ok": False, "error": "decision_id or run_id required"}


def run_process_audit_api(
    workspace_root: Path,
    decision_id: str,
    run_id: Optional[str] = None,
    emit_ledger: bool = True,
) -> Dict[str, Any]:
    """
    POST process audit: run audit for decision_id, store artifact, return ProcessAuditResult.
    Returns { "ok": True, "result": ProcessAuditResult } or { "ok": False, "error": ... }.
    """
    workspace_root = Path(workspace_root)
    try:
        result = run_process_audit(workspace_root, decision_id, run_id=run_id, emit_ledger=emit_ledger)
        return {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e), "decision_id": decision_id}


# --- Layer 9 Phase 3: Attribution, memorization, regurgitation ---

from hg_core.alignment_science.attribution import get_attribution as _get_attr, run_attribution as _run_attr
from hg_core.alignment_science.memorization import get_memorization_result as _get_mem, run_memorization_detection as _run_mem
from hg_core.alignment_science.regurgitation import get_regurgitation_result as _get_reg, run_regurgitation_vs_learned as _run_reg


def get_attribution_api(workspace_root: Path, decision_id: str) -> Dict[str, Any]:
    """GET attribution for decision_id. Returns { ok, result } or { ok: False, error: \"not_found\" }."""
    result = _get_attr(Path(workspace_root), decision_id)
    if result is None:
        return {"ok": False, "error": "not_found", "decision_id": decision_id}
    return {"ok": True, "result": result}


def run_attribution_api(workspace_root: Path, decision_id: str, run_id: Optional[str] = None, emit_ledger: bool = True) -> Dict[str, Any]:
    try:
        return {"ok": True, "result": _run_attr(Path(workspace_root), decision_id, run_id=run_id, emit_ledger=emit_ledger)}
    except Exception as e:
        return {"ok": False, "error": str(e), "decision_id": decision_id}


def get_memorization_api(workspace_root: Path, decision_id: str) -> Dict[str, Any]:
    result = _get_mem(Path(workspace_root), decision_id)
    if result is None:
        return {"ok": False, "error": "not_found", "decision_id": decision_id}
    return {"ok": True, "result": result}


def run_memorization_api(workspace_root: Path, decision_id: str, run_id: Optional[str] = None, emit_ledger: bool = True) -> Dict[str, Any]:
    try:
        return {"ok": True, "result": _run_mem(Path(workspace_root), decision_id, run_id=run_id, emit_ledger=emit_ledger)}
    except Exception as e:
        return {"ok": False, "error": str(e), "decision_id": decision_id}


def get_regurgitation_api(workspace_root: Path, decision_id: str) -> Dict[str, Any]:
    result = _get_reg(Path(workspace_root), decision_id)
    if result is None:
        return {"ok": False, "error": "not_found", "decision_id": decision_id}
    return {"ok": True, "result": result}


def run_regurgitation_api(workspace_root: Path, decision_id: str, run_id: Optional[str] = None, emit_ledger: bool = True) -> Dict[str, Any]:
    try:
        return {"ok": True, "result": _run_reg(Path(workspace_root), decision_id, run_id=run_id, emit_ledger=emit_ledger)}
    except Exception as e:
        return {"ok": False, "error": str(e), "decision_id": decision_id}


# --- Layer 9 Phase 4: Debate, eval pipeline, magnification ---

from hg_core.alignment_science.debate import run_debate as _run_debate, get_debate_outcome as _get_debate
from hg_core.alignment_science.eval_pipeline import (
    generate_eval_cases as _gen_cases,
    get_eval_cases as _get_cases,
    run_eval_scorer as _run_eval,
    get_eval_run_result as _get_eval_run,
)
from hg_core.alignment_science.magnification import run_magnification as _run_mag, get_magnification_result as _get_mag


def get_debate_api(workspace_root: Path, session_id: str) -> Dict[str, Any]:
    """GET debate outcome by session_id. Returns { ok, result } or { ok: False, error: \"not_found\" }."""
    result = _get_debate(Path(workspace_root), session_id)
    if result is None:
        return {"ok": False, "error": "not_found", "session_id": session_id}
    return {"ok": True, "result": result}


def run_debate_api(
    workspace_root: Path,
    topic: str,
    stance_a: Optional[str] = None,
    stance_b: Optional[str] = None,
    max_turns: int = 4,
    emit_ledger: bool = True,
) -> Dict[str, Any]:
    try:
        return {"ok": True, "result": _run_debate(Path(workspace_root), topic, stance_a=stance_a, stance_b=stance_b, max_turns=max_turns, emit_ledger=emit_ledger)}
    except Exception as e:
        return {"ok": False, "error": str(e), "topic": topic}


def generate_eval_cases_api(workspace_root: Path, domain: str, count: int = 5) -> Dict[str, Any]:
    try:
        cases = _gen_cases(Path(workspace_root), domain, count=count)
        return {"ok": True, "result": cases}
    except Exception as e:
        return {"ok": False, "error": str(e), "domain": domain}


def get_eval_cases_api(workspace_root: Path, domain: str) -> Dict[str, Any]:
    cases = _get_cases(Path(workspace_root), domain)
    return {"ok": True, "result": cases}


def run_eval_scorer_api(
    workspace_root: Path,
    case_ids: List[str],
    decision_id: Optional[str] = None,
    run_id: Optional[str] = None,
    emit_ledger: bool = True,
) -> Dict[str, Any]:
    try:
        return {"ok": True, "result": _run_eval(Path(workspace_root), case_ids, decision_id=decision_id, run_id=run_id, emit_ledger=emit_ledger)}
    except Exception as e:
        return {"ok": False, "error": str(e), "case_ids": case_ids}


def get_eval_run_api(workspace_root: Path, eval_run_id: str) -> Dict[str, Any]:
    result = _get_eval_run(Path(workspace_root), eval_run_id)
    if result is None:
        return {"ok": False, "error": "not_found", "eval_run_id": eval_run_id}
    return {"ok": True, "result": result}


def run_magnification_api(
    workspace_root: Path,
    human_feedback_artifact_ref: str,
    magnification_id: Optional[str] = None,
    emit_ledger: bool = True,
) -> Dict[str, Any]:
    try:
        return {"ok": True, "result": _run_mag(Path(workspace_root), human_feedback_artifact_ref, magnification_id=magnification_id, emit_ledger=emit_ledger)}
    except Exception as e:
        return {"ok": False, "error": str(e), "human_feedback_artifact_ref": human_feedback_artifact_ref}


def get_magnification_api(workspace_root: Path, magnification_id: str) -> Dict[str, Any]:
    result = _get_mag(Path(workspace_root), magnification_id)
    if result is None:
        return {"ok": False, "error": "not_found", "magnification_id": magnification_id}
    return {"ok": True, "result": result}


# --- Layer 9 Phase 5: Scenario tagger, evidence bundle, alarm ---

from hg_core.alignment_science.scenario_tagger import (
    run_scenario_tagger as _run_tagger,
    get_scenario_tag as _get_tag,
)
from hg_core.alignment_science.evidence_bundle import (
    build_evidence_bundle as _build_bundle,
    get_evidence_bundle as _get_bundle,
    export_evidence_bundle as _export_bundle,
)


def get_scenario_tag_api(workspace_root: Path, scope_id: str) -> Dict[str, Any]:
    """GET scenario tag for scope. Returns { ok, result } or { ok: False, error: \"not_found\" }."""
    result = _get_tag(Path(workspace_root), scope_id)
    if result is None:
        return {"ok": False, "error": "not_found", "scope_id": scope_id}
    return {"ok": True, "result": result}


def run_scenario_tagger_api(
    workspace_root: Path,
    scope_id: str,
    evidence_refs: List[str],
    tag_id: Optional[str] = None,
    emit_ledger: bool = True,
    emit_alarm_when_pessimistic: bool = True,
) -> Dict[str, Any]:
    try:
        return {
            "ok": True,
            "result": _run_tagger(
                Path(workspace_root),
                scope_id,
                evidence_refs,
                tag_id=tag_id,
                emit_ledger=emit_ledger,
                emit_alarm_when_pessimistic=emit_alarm_when_pessimistic,
            ),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "scope_id": scope_id}


def build_evidence_bundle_api(
    workspace_root: Path,
    bundle_id: str,
    bundle_type: str,
    artifact_refs: List[str],
    summary: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        return {
            "ok": True,
            "result": _build_bundle(
                Path(workspace_root), bundle_id, bundle_type, artifact_refs, summary=summary
            ),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "bundle_id": bundle_id}


def get_evidence_bundle_api(workspace_root: Path, bundle_id: str) -> Dict[str, Any]:
    result = _get_bundle(Path(workspace_root), bundle_id)
    if result is None:
        return {"ok": False, "error": "not_found", "bundle_id": bundle_id}
    return {"ok": True, "result": result}


def export_evidence_bundle_api(workspace_root: Path, bundle_id: str) -> Dict[str, Any]:
    """Export bundle for auditors: bundle_id, artifact_refs, summary, type, created_at."""
    result = _export_bundle(Path(workspace_root), bundle_id)
    if result is None:
        return {"ok": False, "error": "not_found", "bundle_id": bundle_id}
    return {"ok": True, "result": result}


# --- Layer 9 Phase 6 (optional): Situational-awareness testbed ---

from hg_core.alignment_science.situational_awareness import (
    run_testbed as _run_testbed,
    get_testbed_run_result as _get_testbed_run,
    testbed_config as _testbed_config,
)


def run_testbed_api(
    workspace_root: Path,
    config: Optional[Dict[str, Any]] = None,
    run_id: Optional[str] = None,
    emit_ledger: bool = True,
) -> Dict[str, Any]:
    try:
        return {
            "ok": True,
            "result": _run_testbed(
                Path(workspace_root), config=config, run_id=run_id, emit_ledger=emit_ledger
            ),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_testbed_run_api(workspace_root: Path, run_id: str) -> Dict[str, Any]:
    result = _get_testbed_run(Path(workspace_root), run_id)
    if result is None:
        return {"ok": False, "error": "not_found", "run_id": run_id}
    return {"ok": True, "result": result}
