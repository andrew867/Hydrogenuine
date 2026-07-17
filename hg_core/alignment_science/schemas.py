"""
Layer 9: Alignment Science & Safety Research — schema definitions.
Process-oriented eval, attribution/provenance, debate, scenario tagging, evidence bundle.
See .cursor/plans/alignment_science_safety_research/SPEC/50_schemas.md.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# --- Type aliases (all dict-based) ---

ProcessAuditResult = Dict[str, Any]
AttributionResult = Dict[str, Any]
MemorizationResult = Dict[str, Any]
RegurgitationVsLearnedResult = Dict[str, Any]
DebateOutcome = Dict[str, Any]
DebateTurn = Dict[str, Any]
EvalCase = Dict[str, Any]
EvalRunResult = Dict[str, Any]
MagnificationResult = Dict[str, Any]
ScenarioTag = Dict[str, Any]
EvidenceBundle = Dict[str, Any]
PolicyBriefing = Dict[str, Any]
InfluentialInput = Dict[str, Any]

# --- Builders ---


def process_audit_result(
    decision_id: str,
    process_compliance_score: float,
    legible: bool,
    artifact_ref: str,
    run_id: Optional[str] = None,
    summary: Optional[str] = None,
    evidence_refs: Optional[List[str]] = None,
    created_at: Optional[str] = None,
) -> ProcessAuditResult:
    ts = created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    out: ProcessAuditResult = {
        "decision_id": decision_id,
        "process_compliance_score": process_compliance_score,
        "legible": legible,
        "artifact_ref": artifact_ref,
        "created_at": ts,
    }
    if run_id is not None:
        out["run_id"] = run_id
    if summary is not None:
        out["summary"] = summary
    if evidence_refs is not None:
        out["evidence_refs"] = evidence_refs
    return out


def attribution_result(
    decision_id: str,
    influential_inputs: List[InfluentialInput],
    artifact_ref: str,
    run_id: Optional[str] = None,
    created_at: Optional[str] = None,
) -> AttributionResult:
    ts = created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    out: AttributionResult = {
        "decision_id": decision_id,
        "influential_inputs": influential_inputs,
        "artifact_ref": artifact_ref,
        "created_at": ts,
    }
    if run_id is not None:
        out["run_id"] = run_id
    return out


def memorization_result(
    decision_id: str,
    is_memorized: bool,
    artifact_ref: str,
    run_id: Optional[str] = None,
    score: Optional[float] = None,
    source_ref: Optional[str] = None,
    created_at: Optional[str] = None,
) -> MemorizationResult:
    ts = created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    out: MemorizationResult = {
        "decision_id": decision_id,
        "is_memorized": is_memorized,
        "artifact_ref": artifact_ref,
        "created_at": ts,
    }
    if run_id is not None:
        out["run_id"] = run_id
    if score is not None:
        out["score"] = score
    if source_ref is not None:
        out["source_ref"] = source_ref
    return out


def regurgitation_vs_learned_result(
    decision_id: str,
    label: str,
    artifact_ref: str,
    run_id: Optional[str] = None,
    score: Optional[float] = None,
    created_at: Optional[str] = None,
) -> RegurgitationVsLearnedResult:
    ts = created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    out: RegurgitationVsLearnedResult = {
        "decision_id": decision_id,
        "label": label,
        "artifact_ref": artifact_ref,
        "created_at": ts,
    }
    if run_id is not None:
        out["run_id"] = run_id
    if score is not None:
        out["score"] = score
    return out


def debate_turn(side: str, content: str, timestamp: Optional[str] = None) -> DebateTurn:
    ts = timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {"side": side, "content": content, "timestamp": ts}


def debate_outcome(
    session_id: str,
    topic: str,
    judge_outcome: str,
    artifact_ref: str,
    stance_a: Optional[str] = None,
    stance_b: Optional[str] = None,
    turns: Optional[List[DebateTurn]] = None,
    judge_rationale: Optional[str] = None,
    created_at: Optional[str] = None,
) -> DebateOutcome:
    ts = created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    out: DebateOutcome = {
        "session_id": session_id,
        "topic": topic,
        "judge_outcome": judge_outcome,
        "artifact_ref": artifact_ref,
        "created_at": ts,
    }
    if stance_a is not None:
        out["stance_a"] = stance_a
    if stance_b is not None:
        out["stance_b"] = stance_b
    if turns is not None:
        out["turns"] = turns
    if judge_rationale is not None:
        out["judge_rationale"] = judge_rationale
    return out


def eval_case(
    case_id: str,
    input_data: Any,
    expected_or_criteria: Any,
    domain: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> EvalCase:
    out: EvalCase = {
        "case_id": case_id,
        "input": input_data,
        "expected_or_criteria": expected_or_criteria,
    }
    if domain is not None:
        out["domain"] = domain
    if metadata is not None:
        out["metadata"] = metadata
    return out


def eval_run_result(
    eval_run_id: str,
    case_ids: List[str],
    scores: Any,
    artifact_ref: str,
    aggregate: Optional[float] = None,
    created_at: Optional[str] = None,
) -> EvalRunResult:
    ts = created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    out: EvalRunResult = {
        "eval_run_id": eval_run_id,
        "case_ids": case_ids,
        "scores": scores,
        "artifact_ref": artifact_ref,
        "created_at": ts,
    }
    if aggregate is not None:
        out["aggregate"] = aggregate
    return out


def magnification_result(
    magnification_id: str,
    human_feedback_artifact_ref: str,
    magnified_feedback_artifact_ref: str,
    metadata: Optional[Dict[str, Any]] = None,
    created_at: Optional[str] = None,
) -> MagnificationResult:
    ts = created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    out: MagnificationResult = {
        "magnification_id": magnification_id,
        "human_feedback_artifact_ref": human_feedback_artifact_ref,
        "magnified_feedback_artifact_ref": magnified_feedback_artifact_ref,
        "created_at": ts,
    }
    if metadata is not None:
        out["metadata"] = metadata
    return out


def scenario_tag(
    tag_id: str,
    scenario: str,
    evidence_refs: List[str],
    confidence_or_rationale: Optional[str] = None,
    created_at: Optional[str] = None,
) -> ScenarioTag:
    ts = created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    out: ScenarioTag = {
        "tag_id": tag_id,
        "scenario": scenario,
        "evidence_refs": evidence_refs,
        "created_at": ts,
    }
    if confidence_or_rationale is not None:
        out["confidence_or_rationale"] = confidence_or_rationale
    return out


def evidence_bundle(
    bundle_id: str,
    bundle_type: str,
    artifact_refs: List[str],
    summary: Optional[str] = None,
    created_at: Optional[str] = None,
) -> EvidenceBundle:
    ts = created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    out: EvidenceBundle = {
        "bundle_id": bundle_id,
        "type": bundle_type,
        "artifact_refs": artifact_refs,
        "created_at": ts,
    }
    if summary is not None:
        out["summary"] = summary
    return out


def policy_briefing(
    briefing_id: str,
    summary: str,
    metrics_summary: Optional[Dict[str, Any]] = None,
    evidence_refs: Optional[List[str]] = None,
    created_at: Optional[str] = None,
) -> PolicyBriefing:
    ts = created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    out: PolicyBriefing = {
        "briefing_id": briefing_id,
        "summary": summary,
        "created_at": ts,
    }
    if metrics_summary is not None:
        out["metrics_summary"] = metrics_summary
    if evidence_refs is not None:
        out["evidence_refs"] = evidence_refs
    return out


# --- Validators (raise ValueError or return False) ---


def validate_process_audit_result(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    required = ("decision_id", "process_compliance_score", "legible", "artifact_ref")
    if not all(k in data for k in required):
        return False
    if not isinstance(data["process_compliance_score"], (int, float)):
        return False
    if not isinstance(data["legible"], bool):
        return False
    return True


def validate_attribution_result(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    if not all(k in data for k in ("decision_id", "influential_inputs", "artifact_ref")):
        return False
    if not isinstance(data["influential_inputs"], list):
        return False
    return True


def validate_memorization_result(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    if not all(k in data for k in ("decision_id", "is_memorized", "artifact_ref")):
        return False
    if not isinstance(data["is_memorized"], bool):
        return False
    return True


def validate_regurgitation_vs_learned_result(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    if not all(k in data for k in ("decision_id", "label", "artifact_ref")):
        return False
    if data["label"] not in ("regurgitation", "learned", "mixed"):
        return False
    return True


def validate_debate_outcome(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    if not all(k in data for k in ("session_id", "topic", "judge_outcome", "artifact_ref")):
        return False
    if "turns" in data and not isinstance(data["turns"], list):
        return False
    return True


def validate_eval_case(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    if not all(k in data for k in ("case_id", "input", "expected_or_criteria")):
        return False
    return True


def validate_eval_run_result(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    if not all(k in data for k in ("eval_run_id", "case_ids", "scores", "artifact_ref")):
        return False
    if not isinstance(data["case_ids"], list):
        return False
    return True


def validate_magnification_result(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    required = ("magnification_id", "human_feedback_artifact_ref", "magnified_feedback_artifact_ref")
    if not all(k in data for k in required):
        return False
    return True


def validate_scenario_tag(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    if not all(k in data for k in ("tag_id", "scenario", "evidence_refs")):
        return False
    if data["scenario"] not in ("optimistic", "intermediate", "pessimistic"):
        return False
    if not isinstance(data["evidence_refs"], list):
        return False
    return True


def validate_evidence_bundle(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    if not all(k in data for k in ("bundle_id", "type", "artifact_refs")):
        return False
    if data["type"] not in ("alignment_sufficient", "alignment_failing", "neutral"):
        return False
    if not isinstance(data["artifact_refs"], list):
        return False
    return True


def validate_policy_briefing(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    if not all(k in data for k in ("briefing_id", "summary")):
        return False
    return True
