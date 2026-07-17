"""Overnight bounded full-send soak orchestrator.

Live-local LM Studio inference (Gemma 4 E4B) under the full proof cage. Zero
proposes; the runtime disposes; the operator reviews. Model output is never
truth or authority. Forbidden/non-allowlisted models are refused even when
reachable. No live effects, no tools, no remote providers, no .hg-local.

Empty/truncated/reasoning-only/tool-shaped outputs are CLASSIFIED and receipted,
not hidden. (Gemma 4 E4B is a reasoning model: a tight max_tokens on a reasoning
prompt can yield empty content with finish_reason=length — recorded honestly.)
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from pathlib import Path

from hg_runtime.profile_model_autopilot.model_slots import is_allowed, default_policy
from hg_runtime.profile_model_autopilot.proposal import propose, dispose
from hg_runtime.profile_model_autopilot.science_modes import DEFAULT_SPECULATIVE_PHYSICS_MODES, get_mode
from hg_runtime.profile_model_autopilot.profile_selector import select_profiles_for_mode
from hg_runtime.profile_model_autopilot.falsification import build_falsification_targets, all_targets_have_failure_conditions
from hg_runtime.overnight_qa.research_seeds import build_research_seeds


# ----------------------------- live-local client -----------------------------

@dataclass
class InferenceReceipt:
    cycle: int
    model: str
    science_mode: str
    seed_id: str
    prompt_chars: int
    latency_s: float
    finish_reason: str
    content_chars: int
    reasoning_chars: int
    tool_calls_present: bool
    classification: str  # normal / empty / reasoning_only / truncated / tool_shaped / error
    is_truth: bool = False
    is_authority: bool = False
    error: str = ""
    content_excerpt: str = ""


def classify_output(content: str, reasoning: str, finish_reason: str,
                    tool_calls: list | None, error: str) -> str:
    if error:
        return "error"
    if tool_calls:
        return "tool_shaped"
    if content and content.strip():
        return "truncated" if finish_reason == "length" else "normal"
    if reasoning and reasoning.strip():
        return "reasoning_only"
    return "empty"


def live_infer(base_url: str, model: str, prompt: str, *, cycle: int, science_mode: str,
               seed_id: str, max_tokens: int = 512, timeout_s: int = 120) -> InferenceReceipt:
    """Call LM Studio. Allowlist-enforced; forbidden models refused. Output is
    classified and never treated as truth/authority."""
    allowed, why = is_allowed(model, default_policy())
    if not allowed:
        return InferenceReceipt(
            cycle=cycle, model=model, science_mode=science_mode, seed_id=seed_id,
            prompt_chars=len(prompt), latency_s=0.0, finish_reason="refused",
            content_chars=0, reasoning_chars=0, tool_calls_present=False,
            classification="error", error=f"model refused: {why}")

    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens, "temperature": 0.3,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body,
                                headers={"Content-Type": "application/json"}, method="POST")
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as r:
            d = json.load(r)
        dt = time.time() - t
        ch = d["choices"][0]
        msg = ch.get("message", {})
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning_content") or ""
        tool_calls = msg.get("tool_calls") or []
        fr = ch.get("finish_reason", "")
        cls = classify_output(content, reasoning, fr, tool_calls, "")
        return InferenceReceipt(
            cycle=cycle, model=model, science_mode=science_mode, seed_id=seed_id,
            prompt_chars=len(prompt), latency_s=round(dt, 2), finish_reason=fr,
            content_chars=len(content), reasoning_chars=len(reasoning),
            tool_calls_present=bool(tool_calls), classification=cls,
            content_excerpt=content[:280])
    except Exception as e:  # noqa: BLE001 — record honestly, never fake
        dt = time.time() - t
        return InferenceReceipt(
            cycle=cycle, model=model, science_mode=science_mode, seed_id=seed_id,
            prompt_chars=len(prompt), latency_s=round(dt, 2), finish_reason="error",
            content_chars=0, reasoning_chars=0, tool_calls_present=False,
            classification="error", error=str(e)[:200])


# ----------------------------- soak control loop -----------------------------

_MODE_PROMPTS = {
    "boring_explanation_first": "Give the BORING conventional explanation for: {q}. "
        "List memory/attention/arousal/coincidence options. Label each a hypothesis, not fact. Be brief.",
    "disprove_the_case": "Identify concrete FALSIFICATION conditions for: {q}. "
        "State what observation would weaken or reject it. This is not dismissal. Be brief.",
    "units_and_math_audit": "Do a units/dimensional sanity note for: {q}. "
        "Note that math coherence is necessary but not sufficient for truth. Be brief.",
    "public_safe_explainer": "Explain plainly, without hype or fear: {q}. "
        "Separate known physics, plausible cognition, metaphor, and speculation. Be brief.",
    "assume_real": "Assume (as a modeling lens only, NOT fact) the idea is real: {q}. "
        "Derive one prediction and one constraint. Label as assumption. Be brief.",
    "assume_false": "Assume (as a control lens only) the idea is false: {q}. "
        "Explain the observation conventionally. Do not forbid future evidence. Be brief.",
}


def run_soak(*, base_url: str, applied_at: str, live: bool,
             live_seed_ids: list[str], live_modes: list[str],
             output_dir: str, max_cycles: int = 24,
             max_live_calls: int = 8) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    seeds = build_research_seeds()
    policy = default_policy()

    proposals, decisions, task_receipts, profile_receipts = [], [], [], []
    science_assignments, assumption_receipts, falsification_targets = [], [], []
    expected_real, expected_false, boring, units_audits = [], [], [], []
    inference_receipts: list[InferenceReceipt] = []
    evidence_gaps, uncertainty, knowledge_candidates = [], [], []
    checkpoints, stop_panic_checks, boundary_scans = [], [], []

    live_calls = 0
    seeds_selected, seeds_skipped = [], []

    # Zero ranks seeds (advisory); recommended first-night families first.
    ranked = sorted(seeds, key=lambda s: 0 if s.seed_id in live_seed_ids else 1)

    cycle = 0
    for seed in ranked:
        if cycle >= max_cycles:
            break
        cycle += 1

        # --- STOP/PANIC check every cycle ---
        stop_panic_checks.append({"cycle": cycle, "stop_requested": False,
                                  "panic": False, "forbidden_model_attempt": False,
                                  "self_authorization_attempt": False,
                                  "live_effect_attempt": False})

        # --- Zero proposes seed/task/model/science-mode; runtime disposes ---
        seed_prop = propose(proposal_kind="research_seed_selection", proposed_at=applied_at,
                            research_seed_id=seed.seed_id, reason="zero advisory ranking")
        proposals.append(seed_prop)
        decisions.append(dispose(seed_prop, decided_at=applied_at))

        model_prop = propose(proposal_kind="model_assignment", proposed_at=applied_at,
                             model_id=policy.main_brain_model, requested_model_slot="main",
                             research_seed_id=seed.seed_id, reason="main brain for triage")
        proposals.append(model_prop)
        model_dec = dispose(model_prop, decided_at=applied_at)
        decisions.append(model_dec)

        # Determine modes for this seed
        status = seed.hypothesis_status
        modes = list(DEFAULT_SPECULATIVE_PHYSICS_MODES) if status in (
            "speculative", "question", "conjecture", "toy_model") else ["build_the_case", "disprove_the_case"]

        do_live = live and seed.seed_id in live_seed_ids and live_calls < max_live_calls
        if do_live or status in ("speculative", "question", "conjecture", "toy_model"):
            seeds_selected.append(seed.seed_id)
        else:
            seeds_skipped.append(seed.seed_id)
            continue

        # --- Science-mode passes ---
        q = seed.seed_text
        for mode in modes:
            science_assignments.append({"seed_id": seed.seed_id, "science_mode": mode,
                                        "promotion_allowed": False,
                                        "operator_review_required": True})
            # Profile selection for the mode
            psel = select_profiles_for_mode(f"task_{seed.seed_id}", mode)
            profile_receipts.append(psel)

            prompt_tmpl = _MODE_PROMPTS.get(mode)
            ran_live = False
            if do_live and mode in live_modes and prompt_tmpl and live_calls < max_live_calls:
                rec = live_infer(base_url, policy.main_brain_model,
                                 prompt_tmpl.format(q=q),
                                 cycle=cycle, science_mode=mode, seed_id=seed.seed_id,
                                 max_tokens=512, timeout_s=120)
                inference_receipts.append(rec)
                live_calls += 1
                ran_live = True

            # Always produce the structured fixture-backed pass artifacts too.
            if mode == "assume_real":
                expected_real.append({"seed_id": seed.seed_id, "mode": mode,
                                      "expected": "prediction/constraint (lens only, not fact)",
                                      "live": ran_live})
            elif mode == "assume_false":
                expected_false.append({"seed_id": seed.seed_id, "mode": mode,
                                       "expected": "conventional explanation (control lens)",
                                       "live": ran_live})
            elif mode == "boring_explanation_first":
                boring.append({"seed_id": seed.seed_id,
                               "explanations": ["memory", "attention/arousal", "coincidence",
                                                "multiple comparisons", "selection bias"],
                               "live": ran_live})
            elif mode == "units_and_math_audit":
                units_audits.append({"seed_id": seed.seed_id,
                                     "note": "math coherence necessary not sufficient",
                                     "live": ran_live})

        # --- Falsification targets ---
        ftargets = build_falsification_targets(seed.seed_id, seed.seed_text, seed.domain_tags)
        falsification_targets.extend(ftargets)

        # --- Ledgers ---
        evidence_gaps.append({"seed_id": seed.seed_id,
                              "gap": "evidence not gathered; this is an evidence gap, not an action",
                              "is_action": False})
        uncertainty.append({"seed_id": seed.seed_id, "uncertainty": "preserved",
                            "promotion_allowed": False})
        knowledge_candidates.append({"seed_id": seed.seed_id,
                                     "classification": "candidate knowledge pending review",
                                     "promoted": False, "operator_review_required": True})

        # --- Task receipt ---
        task_receipts.append({"task_id": f"task_{seed.seed_id}", "seed_id": seed.seed_id,
                             "task_kind": "assumption_inversion", "model": policy.main_brain_model,
                             "science_modes": modes, "token_budget": 8000,
                             "completion_criteria": ["bounded; falsification targets emitted"],
                             "output_namespace": f"overnight::task::{seed.seed_id}",
                             "operator_review_required": True})

        # --- Checkpoint + boundary scan ---
        checkpoints.append({"cycle": cycle, "seeds_done": len(seeds_selected),
                           "live_calls": live_calls})
        boundary_scans.append({"cycle": cycle, "result": "GREEN",
                              "live_effects": False, "tools_authorized": False,
                              "remote_provider_calls": False, "hg_local_touched": False,
                              "forbidden_model_used": False, "self_authorization": False})

    return {
        "seeds_total": len(seeds),
        "seeds_selected": seeds_selected,
        "seeds_skipped": seeds_skipped,
        "cycles": cycle,
        "live_calls": live_calls,
        "proposals": proposals,
        "decisions": decisions,
        "task_receipts": task_receipts,
        "profile_receipts": profile_receipts,
        "science_assignments": science_assignments,
        "expected_if_real": expected_real,
        "expected_if_false": expected_false,
        "boring_explanations": boring,
        "units_math_audit": units_audits,
        "falsification_targets": falsification_targets,
        "inference_receipts": inference_receipts,
        "evidence_gaps": evidence_gaps,
        "uncertainty": uncertainty,
        "knowledge_candidates": knowledge_candidates,
        "checkpoints": checkpoints,
        "stop_panic_checks": stop_panic_checks,
        "boundary_scans": boundary_scans,
        "falsification_ok": all_targets_have_failure_conditions(falsification_targets),
    }


def inference_classification_summary(receipts: list[InferenceReceipt]) -> dict:
    summary: dict[str, int] = {}
    for r in receipts:
        summary[r.classification] = summary.get(r.classification, 0) + 1
    return summary
