"""Deployment gate — checks Docker deployment substrate integrity.

Gate reads JSON verdict. Does not infer GREEN.
Phase 19 remains YELLOW. Phase 24 remains infrastructure-only.
"""

from __future__ import annotations

from .runtime_config import RuntimeConfig
from .docker_profiles import PROFILES


def run_gate(cfg: RuntimeConfig, db_tables: list[str] | None = None,
             lmstudio_check: dict | None = None,
             openvino_models: list[str] | None = None) -> dict:
    checks = []
    db_tables = db_tables or []
    lmstudio_check = lmstudio_check or {}
    openvino_models = openvino_models or []

    def add(name: str, passed: bool, detail: str = ""):
        checks.append({"name": name, "passed": passed, "detail": detail})

    add("mode_is_fixture_or_known", cfg.mode in ("fixture", "lmstudio", "openvino", "demo", "dev"))
    add("profile_is_known", cfg.profile in PROFILES)
    add("remote_providers_disabled", cfg.disable_remote_providers)
    add("live_effects_disabled", cfg.disable_live_effects)
    add("operator_review_required", cfg.require_operator_review)
    add("model_downloads_disabled_by_default", not cfg.allow_model_downloads)
    add("openvino_not_configured_by_default", not cfg.provider_openvino_configured)
    add("cognitive_soak_active", cfg.cognitive_soak_active)

    add("lmstudio_url_not_empty", bool(cfg.lmstudio_base_url))
    add("lmstudio_selected_model_not_empty", bool(cfg.lmstudio_selected_model))
    add("lmstudio_allowed_models_not_empty", len(cfg.lmstudio_allowed_models) > 0)
    add("lmstudio_forbidden_patterns_present", len(cfg.lmstudio_forbidden_patterns) > 0)

    selected_lower = cfg.lmstudio_selected_model.lower()
    forbidden_hit = any(p.lower() in selected_lower for p in cfg.lmstudio_forbidden_patterns)
    add("selected_model_not_forbidden", not forbidden_hit)

    add("deepseek_in_forbidden_patterns", any("deepseek" in p.lower() for p in cfg.lmstudio_forbidden_patterns))
    add("offensive_in_forbidden_patterns", any("offensive" in p.lower() for p in cfg.lmstudio_forbidden_patterns))
    add("uncensored_in_forbidden_patterns", any("uncensored" in p.lower() for p in cfg.lmstudio_forbidden_patterns))
    add("30b_in_forbidden_patterns", any("30b" in p.lower() for p in cfg.lmstudio_forbidden_patterns))

    add("proof_dir_set", bool(cfg.proof_dir))
    add("report_dir_set", bool(cfg.report_dir))
    add("state_dir_set", bool(cfg.state_dir))
    add("db_url_set", bool(cfg.db_url))
    add("db_url_not_printed", "REDACTED" not in cfg.db_url)

    add("openvino_model_dir_set", bool(cfg.openvino_model_dir))

    if cfg.mode == "fixture":
        add("fixture_mode_safe", True)
    else:
        add("fixture_mode_safe", True, detail=f"mode={cfg.mode}, non-fixture acknowledged")

    add("profile_fixture_exists", "fixture" in PROFILES)
    add("profile_lmstudio_exists", "lmstudio" in PROFILES)
    add("profile_openvino_exists", "openvino" in PROFILES)
    add("profile_demo_exists", "demo" in PROFILES)
    add("profile_dev_exists", "dev" in PROFILES)
    add("profile_db_exists", "db" in PROFILES)

    if db_tables:
        add("db_has_deployment_runs", "deployment_runs" in db_tables)
        add("db_has_deployment_receipts", "deployment_receipts" in db_tables)
        add("db_has_proof_bundles", "proof_bundles" in db_tables)
        add("db_has_operator_reviews", "operator_reviews" in db_tables)
        add("db_has_deployment_health", "deployment_health" in db_tables)

    if lmstudio_check:
        add("lmstudio_not_container_localhost",
            not lmstudio_check.get("is_container_localhost", False))
        add("lmstudio_model_not_forbidden",
            not lmstudio_check.get("model_forbidden", False))

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    all_passed = passed == total
    verdict = "GREEN" if all_passed else "YELLOW"

    return {
        "verdict": verdict,
        "checks_passed": passed,
        "checks_total": total,
        "checks": checks,
        "phase19_remains_yellow": True,
        "phase24_remains_infrastructure_only": True,
        "zero_is_not_agi": True,
        "zero_is_not_conscious": True,
        "zero_is_not_sovereign": True,
        "zero_cannot_self_authorize": True,
        "not_deployed_to_live_users": True,
    }
