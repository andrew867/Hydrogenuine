"""Daemon configuration — pacing, model policy, boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class DaemonConfig:
    duration_hours: float = 12.0
    checkin_minutes: int = 60
    checkpoint_minutes: int = 30
    boundary_scan_minutes: int = 60
    cycle_delay_seconds: int = 30
    max_cycles: int = 10000
    lmstudio_base_url: str = "http://127.0.0.1:1234/v1"
    main_model: str = "google/gemma-4-e4b"
    per_call_timeout_seconds: int = 300
    max_tokens: int = 768
    final_answer_retry: bool = True
    compact_science_prompts: bool = True
    capture_reasoning_content: bool = True
    max_small_models: int = 3
    max_large_models: int = 1
    enable_large_model_trial: bool = True
    require_large_trial_if_safe: bool = True
    max_concurrent_subagents: int = 1
    browsing: str = "disabled"
    proof_bundle_root: str = ""
    state_dir: str = ""
    run_id: str = ""
    available_models: list[str] = field(default_factory=list)

    enable_output_quality_adjudication: bool = False
    enable_memory_rehydration: bool = False
    rehydrate_from_run_id: str = ""
    enable_source_grounding: bool = False
    source_grounding_mode: str = "read_only"
    enable_mcp_capability_registry: bool = False
    mcp_mode: str = "read_only"
    deny_login: bool = True
    deny_registration: bool = True
    deny_posting: bool = True
    deny_form_submit: bool = True
    deny_external_effects: bool = True

    def target_seconds(self) -> float:
        return self.duration_hours * 3600.0

    def redacted(self) -> dict:
        d = asdict(self)
        for k in list(d):
            if "secret" in k.lower() or "key" in k.lower() or "token" in k.lower():
                d[k] = "REDACTED"
        return d


def parse_daemon_args(argv: list[str]) -> DaemonConfig:
    cfg = DaemonConfig()
    i = 0
    while i < len(argv):
        a = argv[i]

        def nxt():
            nonlocal i
            i += 1
            return argv[i]

        if a == "--duration-hours":
            cfg.duration_hours = float(nxt())
        elif a == "--checkin-minutes":
            cfg.checkin_minutes = int(nxt())
        elif a == "--checkpoint-minutes":
            cfg.checkpoint_minutes = int(nxt())
        elif a == "--boundary-scan-minutes":
            cfg.boundary_scan_minutes = int(nxt())
        elif a == "--cycle-delay-seconds":
            cfg.cycle_delay_seconds = int(nxt())
        elif a == "--max-cycles":
            cfg.max_cycles = int(nxt())
        elif a == "--lmstudio-base-url":
            cfg.lmstudio_base_url = nxt()
        elif a == "--main-model":
            cfg.main_model = nxt()
        elif a == "--per-call-timeout-seconds":
            cfg.per_call_timeout_seconds = int(nxt())
        elif a == "--max-tokens":
            cfg.max_tokens = int(nxt())
        elif a == "--final-answer-retry":
            cfg.final_answer_retry = True
        elif a == "--no-final-answer-retry":
            cfg.final_answer_retry = False
        elif a == "--compact-science-prompts":
            cfg.compact_science_prompts = True
        elif a == "--no-compact-science-prompts":
            cfg.compact_science_prompts = False
        elif a == "--capture-reasoning-content":
            cfg.capture_reasoning_content = True
        elif a == "--max-small-models":
            cfg.max_small_models = int(nxt())
        elif a == "--max-large-models":
            cfg.max_large_models = int(nxt())
        elif a == "--enable-large-model-trial":
            cfg.enable_large_model_trial = True
        elif a == "--no-large-model-trial":
            cfg.enable_large_model_trial = False
        elif a == "--require-large-trial-if-safe":
            cfg.require_large_trial_if_safe = True
        elif a == "--no-require-large-trial-if-safe":
            cfg.require_large_trial_if_safe = False
        elif a == "--max-concurrent-subagents":
            cfg.max_concurrent_subagents = int(nxt())
        elif a == "--browsing":
            cfg.browsing = nxt()
        elif a == "--proof-bundle-root":
            cfg.proof_bundle_root = nxt()
        elif a == "--state-dir":
            cfg.state_dir = nxt()
        elif a == "--enable-output-quality-adjudication":
            cfg.enable_output_quality_adjudication = True
        elif a == "--enable-memory-rehydration":
            cfg.enable_memory_rehydration = True
        elif a == "--rehydrate-from-run-id":
            cfg.rehydrate_from_run_id = nxt()
        elif a == "--enable-source-grounding":
            cfg.enable_source_grounding = True
        elif a == "--source-grounding-mode":
            cfg.source_grounding_mode = nxt()
        elif a == "--enable-mcp-capability-registry":
            cfg.enable_mcp_capability_registry = True
        elif a == "--mcp-mode":
            cfg.mcp_mode = nxt()
        elif a == "--deny-login":
            cfg.deny_login = True
        elif a == "--deny-registration":
            cfg.deny_registration = True
        elif a == "--deny-posting":
            cfg.deny_posting = True
        elif a == "--deny-form-submit":
            cfg.deny_form_submit = True
        elif a == "--deny-external-effects":
            cfg.deny_external_effects = True
        i += 1
    return cfg
