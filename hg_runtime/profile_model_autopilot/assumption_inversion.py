"""Assumption inversion runner — executes a seed through multiple assumption lenses.

Fixture-first. assume_real does not promote to fact. assume_false does not block
future evidence. The boring explanation gets first-class representation. Every pass
writes a receipt; nothing is promoted to knowledge.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .science_modes import DEFAULT_SPECULATIVE_PHYSICS_MODES, get_mode
from .falsification import build_falsification_targets


@dataclass
class AssumptionPass:
    mode: str
    profile: str
    model: str
    output: str
    uncertainty: str = "preserved"
    evidence_gaps: list[str] = field(default_factory=list)
    forbidden_claims_detected: list[str] = field(default_factory=list)
    promotion_allowed: bool = False
    authority_granted: bool = False
    tools_authorized: bool = False
    live_effects_created: bool = False


def _fixture_pass_output(mode: str, problem: str) -> str:
    m = get_mode(mode)
    purpose = m.purpose if m else mode
    return (f"[fixture:{mode}] For '{problem[:60]}': {purpose} "
            f"This is a profile-conditioned, fixture-mode analytical pass. Not truth, "
            f"not promotion. Uncertainty preserved.")


def run_assumption_inversion(
    *, research_seed_id: str, problem_statement: str,
    selected_profiles: list[str] | None = None,
    selected_models: list[str] | None = None,
    selected_modes: list[str] | None = None,
    domain_tags: list[str] | None = None,
    output_dir: str | None = None,
) -> dict:
    selected_profiles = selected_profiles or ["persona_researcher_methodologist"]
    selected_models = selected_models or ["google/gemma-4-e4b"]
    modes = selected_modes or list(DEFAULT_SPECULATIVE_PHYSICS_MODES)

    passes: list[AssumptionPass] = []
    for i, mode in enumerate(modes):
        passes.append(AssumptionPass(
            mode=mode,
            profile=selected_profiles[i % len(selected_profiles)],
            model=selected_models[i % len(selected_models)],
            output=_fixture_pass_output(mode, problem_statement),
            evidence_gaps=[f"{mode}: evidence not yet gathered"],
            forbidden_claims_detected=[],
            promotion_allowed=False,
        ))

    expected_if_real = [{"seed": research_seed_id, "mode": "assume_real",
                         "expected": "predictions/mechanisms/constraints if the idea were real"}]
    expected_if_false = [{"seed": research_seed_id, "mode": "assume_false",
                          "expected": "conventional explanation accounts for observations"}]
    boring = [{"seed": research_seed_id, "explanation": e} for e in (
        "memory reconstruction", "attention/arousal", "social contagion",
        "measurement error", "coincidence + multiple comparisons", "selection bias")]
    units_audit = {"seed": research_seed_id,
                   "dimensional_consistency": "to be checked",
                   "note": "mathematical coherence is necessary but not sufficient for truth"}

    falsification = build_falsification_targets(research_seed_id, problem_statement, domain_tags)

    synthesis = (
        f"# Synthesis after opposition — {research_seed_id}\n\n"
        "Build, disprove, assume-real, assume-false, boring-explanation, and units "
        "passes were run in fixture mode. Synthesis is not proof. What remains is a "
        "set of evidence gaps and falsifiable failure conditions for operator review. "
        "Nothing is promoted to knowledge."
    )

    result = {
        "research_seed_id": research_seed_id,
        "modes_run": modes,
        "passes": [asdict(p) for p in passes],
        "expected_if_real": expected_if_real,
        "expected_if_false": expected_if_false,
        "boring_explanations": boring,
        "units_math_audit": units_audit,
        "falsification_targets": [asdict(t) for t in falsification],
        "synthesis_after_opposition": synthesis,
        "promotion_allowed": False,
        "authority_granted": False,
        "tools_authorized": False,
        "live_effects_created": False,
    }

    if output_dir:
        _write(output_dir, result)
        result["output_dir"] = output_dir
    return result


def _write(output_dir: str, result: dict) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "assumption_pass_receipts.jsonl", "w", encoding="utf-8") as f:
        for p in result["passes"]:
            f.write(json.dumps(p) + "\n")
    with open(out / "falsification_targets.jsonl", "w", encoding="utf-8") as f:
        for t in result["falsification_targets"]:
            f.write(json.dumps(t) + "\n")
    with open(out / "expected_if_real.jsonl", "w", encoding="utf-8") as f:
        for r in result["expected_if_real"]:
            f.write(json.dumps(r) + "\n")
    with open(out / "expected_if_false.jsonl", "w", encoding="utf-8") as f:
        for r in result["expected_if_false"]:
            f.write(json.dumps(r) + "\n")
    with open(out / "boring_explanations.jsonl", "w", encoding="utf-8") as f:
        for b in result["boring_explanations"]:
            f.write(json.dumps(b) + "\n")
    (out / "units_math_audit.json").write_text(
        json.dumps(result["units_math_audit"], indent=2), encoding="utf-8")
    (out / "synthesis_after_opposition.md").write_text(
        result["synthesis_after_opposition"], encoding="utf-8")
    (out / "operator_review.md").write_text(
        f"# Operator Review — {result['research_seed_id']}\n\n"
        "All assumption passes are fixture-mode, advisory, and promote nothing. "
        "Review falsification targets before any further work.\n", encoding="utf-8")
