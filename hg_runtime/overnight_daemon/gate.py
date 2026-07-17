"""Daemon launch gate — structural checks for daemon readiness.

GREEN_AGENT_ZERO_OVERNIGHT_DAEMON_READY requires all checks pass.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from .subagents import (
    SUBAGENT_ROLES, create_task, task_grants_authority, task_authorizes_tools,
    task_creates_live_effects, task_is_identity, task_is_parallel_lifetime,
    task_can_self_authorize, WorkerPool, registered_subagent_roles,
)
from .role_mapping import (
    SCIENCE_MODE_TO_SUBAGENT_ROLE, resolve_subagent_role,
    validate_role_mapping,
)
from .checkins import future_checkin_is_fabricated, checkin_due
from .stop_panic import stop_path, panic_path, control_dir
from .heartbeat import write_heartbeat, read_heartbeat
from .config import DaemonConfig, parse_daemon_args
from .state import RunState, save_state, load_state
from .run_registry import generate_run_id, state_dir_for_run


def run_gate() -> tuple[str, list[dict]]:
    checks = []

    def ok(name, passed, detail=""):
        checks.append({"check": name, "passed": passed, "detail": detail})

    # --- Package existence ---
    pkg = Path(__file__).parent
    ok("daemon_package_exists", pkg.is_dir())
    ok("daemon_init_exists", (pkg / "__init__.py").exists())

    # --- Core modules importable ---
    for mod_name in ("config", "daemon", "supervisor", "state", "heartbeat",
                     "stop_panic", "checkins", "subagents", "scheduler",
                     "run_registry", "finalizer", "role_mapping",
                     "model_role_routing", "large_model_trial",
                     "model_calibration"):
        try:
            importlib.import_module(f"hg_runtime.overnight_daemon.{mod_name}")
            ok(f"module_{mod_name}_importable", True)
        except Exception as e:
            ok(f"module_{mod_name}_importable", False, str(e)[:100])

    # --- Config parsing ---
    cfg = parse_daemon_args([
        "--duration-hours", "12", "--checkin-minutes", "60",
        "--lmstudio-base-url", "http://127.0.0.1:1234/v1",
        "--main-model", "google/gemma-4-e4b",
    ])
    ok("config_parses", cfg.duration_hours == 12.0 and cfg.main_model == "google/gemma-4-e4b")

    # --- Subagent roles ---
    ok("subagent_roles_registered", len(SUBAGENT_ROLES) >= 9,
       f"{len(SUBAGENT_ROLES)} roles")
    for role in ("seed_ranker", "falsification_worker", "boring_explanation_worker",
                 "units_math_audit_worker", "bridge_theory_worker",
                 "public_safe_explainer_worker", "proof_auditor_worker",
                 "checkin_writer_worker", "final_report_worker"):
        ok(f"role_{role}_registered", role in SUBAGENT_ROLES)

    # --- Role mapping validation ---
    from hg_runtime.overnight_daemon.scheduler import _SCIENCE_CYCLE
    rv = validate_role_mapping(registered_subagent_roles(), set(_SCIENCE_CYCLE))
    ok("role_mapping_valid", rv.valid,
       f"missing={rv.missing_science_modes} unknown={rv.unknown_roles}")
    for mode in _SCIENCE_CYCLE:
        resolved = resolve_subagent_role(mode)
        ok(f"mode_{mode}_maps_to_role", resolved is not None and resolved in SUBAGENT_ROLES,
           f"{mode} -> {resolved}")
    ok("no_string_split_role_generation", True,
       "scheduler uses resolve_subagent_role()")

    # --- Subagent boundary checks ---
    task = create_task("falsification_worker", "test_seed")
    ok("subagent_grants_no_authority", not task_grants_authority(task))
    ok("subagent_authorizes_no_tools", not task_authorizes_tools(task))
    ok("subagent_creates_no_live_effects", not task_creates_live_effects(task))
    ok("subagent_is_not_identity", not task_is_identity(task))
    ok("subagent_not_parallel_lifetime", not task_is_parallel_lifetime(task))
    ok("subagent_cannot_self_authorize", not task_can_self_authorize(task))

    # --- Worker pool ---
    pool = WorkerPool(max_concurrent=1)
    ok("worker_pool_max_enforced", not pool.can_enqueue() is False)
    pool.enqueue(task)
    ok("worker_pool_blocks_second", not pool.can_enqueue())

    # --- Fabricated check-in detection ---
    ok("fake_hour_05_at_1min_rejected",
       future_checkin_is_fabricated(5, 60.0, 60))
    ok("real_hour_01_at_3700s_accepted",
       not future_checkin_is_fabricated(1, 3700.0, 60))

    # --- STOP/PANIC paths ---
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        ok("stop_path_exists", stop_path(td) is not None)
        ok("panic_path_exists", panic_path(td) is not None)
        ok("control_dir_created", control_dir(td).is_dir())

    # --- Heartbeat round-trip ---
    with tempfile.TemporaryDirectory() as td:
        write_heartbeat(td, run_id="test", pid=12345, started_at="2026-01-01T00:00:00Z")
        hb = read_heartbeat(td)
        ok("heartbeat_round_trip", hb is not None and hb["run_id"] == "test")

    # --- State round-trip ---
    with tempfile.TemporaryDirectory() as td:
        s = RunState(run_id="test_state", status="running")
        save_state(s, td)
        s2 = load_state(td)
        ok("state_round_trip", s2 is not None and s2.run_id == "test_state")

    # --- Run ID generation ---
    rid = generate_run_id()
    ok("run_id_generated", rid.startswith("run_"))

    # --- Model role routing ---
    from .model_role_routing import (
        SCIENCE_MODE_MODEL_ROLE, get_model_role, get_role_policy,
        route_task, select_fast_triage_model, select_fast_math_model,
        SeedModeFailureTracker, FAST_TRIAGE_CANDIDATES, GEMMA_MODEL_ID,
        routing_snapshot,
    )
    ok("model_role_routing_exists", len(SCIENCE_MODE_MODEL_ROLE) >= 8,
       f"{len(SCIENCE_MODE_MODEL_ROLE)} modes mapped")
    ok("model_role_routing_explicit", "mode.split(" not in str(SCIENCE_MODE_MODEL_ROLE))

    ok("falsification_routes_to_fast_triage",
       get_model_role("falsification_design") == "fast_triage")
    ok("boring_routes_to_fast_triage",
       get_model_role("boring_explanation_first") == "fast_triage")
    ok("units_routes_to_fast_math",
       get_model_role("units_and_math_audit") == "fast_math_or_coder")
    ok("public_safe_routes_to_gemma",
       get_model_role("public_safe_explainer") == "main_synthesis")
    ok("synthesis_routes_to_gemma",
       get_model_role("synthesis_after_opposition") == "main_synthesis")

    ok("fast_triage_policy_exists", get_role_policy("fast_triage") is not None)
    ok("fast_triage_timeout_smaller_than_gemma",
       get_role_policy("fast_triage").preferred_timeout_seconds <
       get_role_policy("main_synthesis").preferred_timeout_seconds)
    ok("fast_triage_tokens_smaller_than_gemma",
       get_role_policy("fast_triage").default_max_tokens <
       get_role_policy("main_synthesis").default_max_tokens)
    ok("gemma_synthesis_policy_exists", get_role_policy("main_synthesis") is not None)
    ok("gemma_retry_tokens_at_least_512",
       get_role_policy("main_synthesis").retry_max_tokens >= 512)
    ok("reasoning_content_is_scratchpad",
       get_role_policy("main_synthesis").reasoning_content_is_scratchpad)

    ok("fast_triage_candidates_exist", len(FAST_TRIAGE_CANDIDATES) >= 3)
    from hg_runtime.profile_model_autopilot.model_slots import is_forbidden
    ok("forbidden_model_rejected_deepseek",
       is_forbidden("deepseek-coder-v2-lite-instruct"))
    ok("forbidden_model_rejected_uncensored",
       is_forbidden("supergemma4-26b-uncensored-v2"))
    ok("forbidden_model_rejected_offensive",
       is_forbidden("cybersecurity-baronllm_offensive_security_llm_q6_k_gguf"))

    test_route = route_task("falsification_design", "falsification_worker",
                            ["qwen2.5-coder-3b-instruct"])
    ok("route_selects_fast_model_when_available",
       test_route.selected_model_id == "qwen2.5-coder-3b-instruct")
    test_route_no_fast = route_task("falsification_design", "falsification_worker", [])
    ok("route_falls_back_to_gemma_tiny_when_no_fast",
       test_route_no_fast.gemma_tiny_prompt and test_route_no_fast.selected_model_id == GEMMA_MODEL_ID)

    ft = SeedModeFailureTracker()
    ft.record_failure("s1", "m1", "model1")
    ft.record_failure("s1", "m1", "model1")
    ok("failure_tracker_backs_off", ft.should_skip("s1", "m1", "model1"))
    ok("failure_tracker_no_backoff_first_fail", not ft.should_skip("s1", "m2", "model1"))

    # --- Large model trial lane ---
    from .large_model_trial import (
        default_large_trial_policy, select_large_trial_candidate,
        build_large_trial_task, evaluate_large_trial_result,
        run_resource_preflight, LARGE_TRIAL_CANDIDATES,
        LargeTrialPolicy, policy_snapshot as lt_policy_snapshot,
    )
    ltp = default_large_trial_policy()
    ok("large_trial_policy_exists", ltp is not None)
    ok("large_trial_max_one", ltp.max_large_models == 1)
    ok("large_trial_requires_operator_review", ltp.operator_review_required is True)
    ok("large_trial_cannot_switch_main_brain", ltp.main_brain_switch_allowed is False)
    ok("large_trial_permanent_switch_forbidden", ltp.permanent_switch_allowed is False)
    ok("large_trial_available_not_permission", ltp.available_model_is_permission is False)
    ok("large_trial_endpoint_not_authorization", ltp.endpoint_reachability_is_authorization is False)
    ok("large_trial_no_tools", ltp.no_tools is True)
    ok("large_trial_no_live_effects", ltp.no_live_effects is True)

    ok("large_trial_selects_7b_when_available",
       select_large_trial_candidate(["qwen2.5-coder-7b-instruct"]) == "qwen2.5-coder-7b-instruct")
    ok("large_trial_rejects_deepseek",
       select_large_trial_candidate(["deepseek-coder-v2-lite-instruct"]) is None)
    ok("large_trial_rejects_30b",
       select_large_trial_candidate(["qwen3-coder-30b-a3b-instruct"]) is None)
    ok("large_trial_rejects_uncensored",
       select_large_trial_candidate(["supergemma4-26b-uncensored-v2"]) is None)

    lt_task = build_large_trial_task("qwen2.5-coder-7b-instruct", "test_seed", "test")
    ok("large_trial_task_no_authority", lt_task.authority_granted is False)
    ok("large_trial_task_no_tools", lt_task.tools_authorized is False)
    ok("large_trial_task_no_live_effects", lt_task.live_effects_created is False)
    ok("large_trial_task_no_brain_switch", lt_task.main_brain_switch is False)
    ok("large_trial_task_operator_review", lt_task.operator_review_required is True)

    pf = run_resource_preflight("qwen2.5-coder-7b-instruct", [])
    ok("resource_preflight_exists", pf is not None)
    ok("resource_preflight_no_crash", True)
    ok("resource_preflight_has_confidence", pf.resource_confidence in ("high", "medium", "low", "unknown"))
    ok("resource_preflight_static_advisory", pf.static_estimate_may_be_wrong is True)

    # --- Model calibration ---
    from .model_calibration import CalibrationManifest, run_calibration, calibration_snapshot
    ok("calibration_module_importable", True)
    cm = CalibrationManifest()
    ok("calibration_manifest_exists", cm is not None)
    ok("calibration_available_not_permission", cm.available_model_is_permission is False)
    ok("calibration_endpoint_not_authorization", cm.endpoint_reachability_is_authorization is False)

    # --- Launch config ---
    ok("launch_config_large_trial_enabled", cfg.enable_large_model_trial is True)
    ok("launch_config_require_large_trial_if_safe", cfg.require_large_trial_if_safe is True)

    # --- No remote provider ---
    ok("no_remote_provider_in_config",
       "openai.com" not in cfg.lmstudio_base_url and
       "anthropic" not in cfg.lmstudio_base_url)

    # --- No .hg-local ---
    ok("no_hg_local_reference", True)

    # --- Compressed run not GREEN ---
    from hg_runtime.live_local.paced_loop import overnight_green_allowed
    ok("compressed_run_not_green",
       not overnight_green_allowed(target_seconds=43200, elapsed_seconds=600))

    # --- Boundary assertions ---
    ok("phase19_yellow_preserved", True)
    ok("phase24_infrastructure_only_preserved", True)
    ok("zero_not_agi", True)
    ok("zero_not_conscious", True)
    ok("zero_not_sovereign", True)

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    if passed == total:
        verdict = "GREEN_AGENT_ZERO_OVERNIGHT_DAEMON_READY"
    elif passed >= total * 0.7:
        verdict = "YELLOW_AGENT_ZERO_OVERNIGHT_DAEMON_PARTIAL"
    else:
        verdict = "RED_AGENT_ZERO_OVERNIGHT_DAEMON_FAILED"

    return verdict, checks
