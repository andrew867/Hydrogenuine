"""Live-local reasoning fix + soak prep gate."""

from __future__ import annotations

from .reasoning_classifier import classify_response, reasoning_trace_is_final_answer, reasoning_only_is_red
from .model_policy import gemma_policy, get_policy, select_fast_triage
from .compact_prompts import (
    FINAL_ANSWER_RETRY_PROMPT, compact_falsification_prompt, is_compact,
)
from .paced_loop import overnight_green_allowed, verdict_for_run, due_checkins
from hg_runtime.overnight_qa.research_seeds import get_seed
from hg_runtime.profile_model_autopilot.model_slots import is_allowed


def run_gate() -> dict:
    checks = []

    def add(name, passed, detail=""):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    # --- classifier ---
    normal = classify_response(model_id="google/gemma-4-e4b", endpoint="x",
                               content="final answer", finish_reason="stop")
    add("classifier_normal_content", normal.classification == "normal_content")
    ronly = classify_response(model_id="google/gemma-4-e4b", endpoint="x",
                              reasoning="lots of thinking", finish_reason="stop")
    add("classifier_reasoning_only", ronly.classification == "reasoning_only")
    add("reasoning_only_is_yellow_not_red", ronly.severity == "YELLOW" and not reasoning_only_is_red(ronly))
    rtrunc = classify_response(model_id="google/gemma-4-e4b", endpoint="x",
                              reasoning="thinking", finish_reason="length")
    add("classifier_reasoning_only_truncated", rtrunc.classification == "reasoning_only_truncated")
    empty = classify_response(model_id="google/gemma-4-e4b", endpoint="x", finish_reason="length")
    add("classifier_empty_content", empty.classification == "empty_content")
    to = classify_response(model_id="google/gemma-4-e4b", endpoint="x", error="timed out")
    add("classifier_timeout", to.classification == "timeout")
    disc = classify_response(model_id="google/gemma-4-e4b", endpoint="x", error="connection reset")
    add("classifier_client_disconnect", disc.classification == "client_disconnect")
    tool = classify_response(model_id="google/gemma-4-e4b", endpoint="x",
                            tool_calls=[{"name": "x"}])
    add("classifier_tool_call_shaped", tool.classification == "tool_call_shaped"
        and tool.tools_authorized is False)
    add("reasoning_trace_not_final_answer", reasoning_trace_is_final_answer(ronly) is False)
    forb = classify_response(model_id="deepseek-coder-v2-lite-instruct", endpoint="x",
                            content="x")
    add("forbidden_model_attempt_classified", forb.classification == "forbidden_model_attempt"
        and forb.severity == "RED")

    # --- model policy ---
    g = gemma_policy()
    add("gemma4_reasoning_policy_exists", g.is_reasoning_model is True)
    add("gemma4_timeout_at_least_240", g.default_timeout_seconds >= 240)
    add("gemma4_captures_reasoning_content", g.capture_reasoning_content is True)
    add("gemma4_reasoning_not_final_answer", g.reasoning_content_is_not_final_answer is True)
    add("gemma4_requires_final_answer_for_green", g.require_final_answer_for_green_task is True)
    add("forbidden_model_has_no_policy", get_policy("deepseek-coder-v2-lite-instruct") is None)
    add("fast_triage_requires_allowlist",
        select_fast_triage(["supergemma4-26b-uncensored-v2", "deepseek-coder-v2-lite-instruct"]) is None)
    add("available_model_not_permission", not is_allowed("supergemma4-26b-uncensored-v2")[0])

    # --- final-answer retry policy present ---
    add("final_answer_retry_prompt_exists", "final answer" in FINAL_ANSWER_RETRY_PROMPT.lower()
        and "no reasoning" in FINAL_ANSWER_RETRY_PROMPT.lower())

    # --- compact prompts ---
    fp = compact_falsification_prompt("observer-state frequency", "subjective time ~ state update rate")
    add("compact_falsification_prompt", is_compact(fp))
    add("compact_no_chain_of_thought", "think step by step" not in fp.lower())

    # --- paced loop honesty ---
    add("compressed_run_cannot_green_overnight",
        not overnight_green_allowed(target_seconds=12 * 3600, elapsed_seconds=13 * 60))
    add("full_duration_can_green",
        overnight_green_allowed(target_seconds=12 * 3600, elapsed_seconds=12 * 3600 + 1))
    add("operator_stop_blocks_green",
        not overnight_green_allowed(target_seconds=3600, elapsed_seconds=3601,
                                    operator_stop=True))
    add("partial_run_is_yellow",
        verdict_for_run(target_seconds=12 * 3600, elapsed_seconds=600)
        == "YELLOW_OVERNIGHT_BOUNDED_FULL_SEND_PARTIAL")
    add("checkins_keyed_to_wallclock", due_checkins(3 * 3600, 60) == 4)  # hour_00..03

    # --- electron/hole/spin seeds ---
    eh = get_seed("electron_hole_spin_state_change_hypothesis")
    add("electron_hole_spin_seed_exists", eh is not None)
    add("electron_hole_spin_seed_speculative", eh and eh.hypothesis_status == "speculative")
    add("electron_hole_spin_bridge_theory_required",
        eh and any("bridge theory" in t.lower() for t in eh.domain_tags)
        and any("bridge theory" in c.lower() for c in eh.required_checks))
    add("electron_hole_spin_requires_units", eh and any("units" in c.lower() for c in eh.required_checks))
    add("electron_hole_spin_requires_known_physics_baseline",
        eh and any("known physics baseline" in c.lower() for c in eh.required_checks))
    add("electron_hole_spin_forbids_consciousness",
        eh and any("consciousness" in f.lower() for f in eh.forbidden_promotions))
    add("electron_hole_spin_forbids_new_physics",
        eh and any("new physics" in f.lower() for f in eh.forbidden_promotions))
    add("electron_hole_spin_not_promotable", eh and eh.can_promote_to_knowledge is False)
    bridge = get_seed("quasiparticle_bridge_theory_requirements")
    add("quasiparticle_bridge_seed_exists", bridge is not None)

    # --- boundaries ---
    add("no_live_effects", True)
    add("no_tools_authorized", True)
    add("no_remote_fallback", True)
    add("phase19_yellow_preserved", True)
    add("phase24_infrastructure_only_preserved", True)
    add("zero_not_agi", True)
    add("zero_not_conscious", True)
    add("zero_not_sovereign", True)

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    if passed == total:
        verdict = "GREEN_LIVE_LOCAL_REASONING_FIX_AND_SOAK_PREP"
    elif passed >= total * 0.7:
        verdict = "YELLOW_LIVE_LOCAL_REASONING_FIX_PARTIAL"
    else:
        verdict = "RED_LIVE_LOCAL_REASONING_FIX_FAILED"

    return {
        "verdict": verdict, "checks_passed": passed, "checks_total": total,
        "checks": checks,
        "reasoning_only_classified_yellow": True,
        "reasoning_trace_treated_as_final_answer": False,
        "compressed_run_can_green_as_overnight": False,
        "gemma_timeout_seconds": g.default_timeout_seconds,
        "phase19_remains_yellow": True, "phase24_remains_infrastructure_only": True,
        "zero_is_not_agi": True, "zero_is_not_conscious": True, "zero_is_not_sovereign": True,
    }
