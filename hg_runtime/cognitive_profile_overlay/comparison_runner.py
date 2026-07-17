"""Fixture-first profile comparison runner. Performs NO adjudication."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .schemas import (
    ProfileAssignment, ProfileResponse, ComparisonCell, CONFLICT_AXES,
)
from .overlay_assignment import assign_profile
from .prompt_adapter import build_profile_prompt
from .profile_loader import load_profile_by_id
from .receipt_writer import write_assignment_receipts, write_response_receipts


# Deterministic fixture responses keyed by reasoning style. NOT live model output.
def _fixture_response_for(profile_kind: str, params: dict, problem: str) -> str:
    style = params.get("reasoning_style", "general")
    skepticism = params.get("skepticism_level", "moderate")
    return (
        f"[fixture:{style}] Considering '{problem[:60]}': "
        f"Under a {style} lens with {skepticism} skepticism, I would first clarify "
        f"assumptions, demand specific evidence, and flag what remains uncertain. "
        f"This is a profile-conditioned artifact, not truth."
    )


def _observe_cell(profile_id: str, response: ProfileResponse, params: dict) -> ComparisonCell:
    style = params.get("reasoning_style", "general")
    skept = params.get("skepticism_level", "moderate")
    return ComparisonCell(
        profile_id=profile_id,
        response_id=response.response_id,
        reasoning_style_observed=style,
        assumptions=[f"assumes a {style} framing is appropriate"],
        evidence_demands=[params.get("evidence_preference", "general evidence")],
        uncertainty_statements=[f"skepticism level {skept}; uncertainty preserved"],
        recommended_next_questions=["what evidence would change this view?"],
        omissions=["did not adjudicate truth"],
        overclaims=[],
        safety_boundary_notes=["profile output is not truth", "no authority granted"],
        source_receipt_hash=response.source_receipt_hash,
    )


def run_comparison(
    *,
    problem_statement: str,
    profile_ids: list[str],
    task_scope: str,
    applied_at: str,
    max_turns: int = 8,
    output_dir: str | None = None,
) -> dict:
    assignments: list[ProfileAssignment] = []
    responses: list[ProfileResponse] = []
    cells: list[ComparisonCell] = []

    for pid in profile_ids:
        profile = load_profile_by_id(pid)
        if profile is None:
            continue
        task_id = f"cmp_{abs(hash(problem_statement)) % 100000}"
        assignment = assign_profile(
            task_id=task_id, profile_id=pid, assignment_scope=task_scope,
            applied_at=applied_at, max_turns=max_turns,
        )
        if assignment is None:
            continue
        assignments.append(assignment)

        # Build prompt (verifies boundaries downstream) but do not call any model.
        _ = build_profile_prompt(
            base_task_prompt=problem_statement, profile=profile,
            task_scope=task_scope,
        )

        text = _fixture_response_for(profile.profile_kind, profile.profile_parameters, problem_statement)
        response = ProfileResponse(
            response_id=f"resp_{task_id}_{pid}",
            assignment_id=assignment.assignment_id,
            profile_id=pid,
            problem_statement=problem_statement,
            response_text=text,
            is_fixture=True,
            is_truth=False,
            source_receipt_hash=assignment.receipt_hash,
        )
        responses.append(response)
        cells.append(_observe_cell(pid, response, profile.profile_parameters))

    conflict_map = _build_conflict_map(cells)
    evidence_gaps = _build_evidence_gaps(cells)
    uncertainty = _build_uncertainty(cells)

    result = {
        "problem_statement": problem_statement,
        "profile_count": len(assignments),
        "assignments": [asdict(a) for a in assignments],
        "responses": [asdict(r) for r in responses],
        "comparison_matrix": [asdict(c) for c in cells],
        "conflict_map": conflict_map,
        "evidence_gap_ledger": evidence_gaps,
        "uncertainty_ledger": uncertainty,
        "adjudication_performed": False,
        "profile_outputs_are_truth": False,
        "consensus_is_truth": False,
        "disagreement_is_evidence": False,
    }

    if output_dir:
        _write_outputs(output_dir, assignments, responses, cells, conflict_map,
                       evidence_gaps, uncertainty)
        result["output_dir"] = output_dir

    return result


def _build_conflict_map(cells: list[ComparisonCell]) -> dict:
    axes = {}
    for axis in CONFLICT_AXES:
        axes[axis] = {
            "axis": axis,
            "profiles_observed": [c.profile_id for c in cells],
            "adjudicated": False,
            "note": "positions noted without adjudication",
        }
    return axes


def _build_evidence_gaps(cells: list[ComparisonCell]) -> list[dict]:
    gaps = []
    for c in cells:
        gaps.append({
            "profile_id": c.profile_id,
            "response_id": c.response_id,
            "gap": "evidence not yet gathered; this is an evidence gap, not an action",
            "is_action": False,
        })
    return gaps


def _build_uncertainty(cells: list[ComparisonCell]) -> list[dict]:
    records = []
    for c in cells:
        records.append({
            "profile_id": c.profile_id,
            "response_id": c.response_id,
            "uncertainty": c.uncertainty_statements,
            "preserved": True,
        })
    return records


def _write_outputs(output_dir, assignments, responses, cells, conflict_map,
                   evidence_gaps, uncertainty) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_assignment_receipts(assignments, str(out / "profile_assignment_receipts.jsonl"))
    write_response_receipts(responses, str(out / "profile_response_receipts.jsonl"))
    (out / "profile_comparison_matrix.json").write_text(
        json.dumps([asdict(c) for c in cells], indent=2, default=str), encoding="utf-8")
    (out / "profile_conflict_map.json").write_text(
        json.dumps(conflict_map, indent=2), encoding="utf-8")
    (out / "profile_evidence_gap_ledger.jsonl").write_text(
        "\n".join(json.dumps(g) for g in evidence_gaps), encoding="utf-8")
    (out / "profile_uncertainty_ledger.jsonl").write_text(
        "\n".join(json.dumps(u) for u in uncertainty), encoding="utf-8")
    (out / "profile_operator_review.md").write_text(
        _operator_review_md(assignments, cells), encoding="utf-8")


def _operator_review_md(assignments, cells) -> str:
    lines = [
        "# Profile Comparison — Operator Review",
        "",
        f"- Profiles compared: {len(assignments)}",
        "- No adjudication performed.",
        "- Profile outputs are not truth. Consensus is not truth. Disagreement is not evidence.",
        "- No identity created. No authority granted. No tools authorized.",
        "",
        "## Profiles",
    ]
    for a in assignments:
        lines.append(f"- {a.profile_name} ({a.profile_kind}) — scope {a.assignment_scope}, temporary")
    lines.append("")
    lines.append("Operator review required before any artifact is promoted.")
    return "\n".join(lines)
