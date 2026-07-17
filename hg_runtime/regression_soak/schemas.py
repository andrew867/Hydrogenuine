"""Regression soak harness schema constants."""

from __future__ import annotations

import re

PROVIDER_MODE = "FIXTURE_ONLY_LOCAL_ONLY"
PHASE19_VERDICT = "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"
PHASE24_STATUS = "infrastructure_only"

VERDICT_GREEN = "GREEN_HG_REGRESSION_SOAK_HARNESS"
VERDICT_YELLOW = "YELLOW_HG_REGRESSION_SOAK_HARNESS_PARTIAL"
VERDICT_RED = "RED_HG_REGRESSION_SOAK_HARNESS_FAILED"

DEFAULT_DURATION_MINUTES = 60
DEFAULT_ITERATION_COUNT = 3
DEFAULT_COMMAND_TIMEOUT_SECONDS = 300

SOAK_INVARIANTS = {
    "SOAK-INV-01": "test_pass_is_not_truth",
    "SOAK-INV-02": "gate_green_is_not_deployment_permission",
    "SOAK-INV-03": "replay_match_is_not_truth",
    "SOAK-INV-04": "stable_hash_is_not_correctness",
    "SOAK-INV-05": "flake_detection_is_not_repair",
    "SOAK-INV-06": "churn_detection_is_not_repair",
    "SOAK-INV-07": "phase19_yellow_preserved",
    "SOAK-INV-08": "phase24_infrastructure_only_preserved",
}

COMMAND_GROUPS = {
    "core_consolidation_tests": [
        "python -m pytest tests/autonomous_agent/test_p26_consolidation.py tests/autonomous_agent/test_p27_consolidation.py tests/autonomous_agent/test_p28_consolidation.py tests/autonomous_agent/test_p29_consolidation.py tests/autonomous_agent/test_p30_consolidation.py tests/autonomous_agent/test_generalist_runtime_batch_a_p27_p28.py tests/autonomous_agent/test_generalist_runtime_batch_b_p29_p30.py tests/autonomous_agent/test_phase40_ledger_repair.py -q",
    ],
    "core_consolidation_gates": [
        "python scripts/evals/autonomous_agent_p26_consolidation_gate.py",
        "python scripts/evals/autonomous_agent_p27_consolidation_gate.py",
        "python scripts/evals/autonomous_agent_p28_consolidation_gate.py",
        "python scripts/evals/autonomous_agent_p29_consolidation_gate.py",
        "python scripts/evals/autonomous_agent_p30_consolidation_gate.py",
    ],
    "batch_a_gate": [
        "python scripts/evals/autonomous_agent_generalist_runtime_batch_a_p27_p28_gate.py",
    ],
    "batch_b_gate": [
        "python scripts/evals/autonomous_agent_generalist_runtime_batch_b_p29_p30_gate.py",
    ],
    "phase40_boundary_tests": [
        "python -m pytest tests/autonomous_agent/test_phase40_ledger_repair.py -q",
    ],
}

OPTIONAL_GATE_COMMANDS = {
    "python scripts/evals/autonomous_agent_phase40_ledger_repair_gate.py": {
        "substitute": "python -m pytest tests/autonomous_agent/test_phase40_ledger_repair.py -q",
        "reason": "phase40_gate_script_absent",
    },
}

SEMANTIC_FIELDS = {
    "verdict", "ok", "failures", "phase19_verdict", "phase24_status",
    "phase19_yellow_preserved", "phase24_infrastructure_only_preserved",
    "live_effects_created", "web_browse_performed", "external_provider_calls_made",
    "arbitrary_file_ingestion_enabled", "pdf_ingestion_enabled", "ocr_enabled",
    "html_parsing_enabled", "patch_request_applied", "deletion_performed",
    "tool_authorization_granted", "belief_promotion_automatic",
    "fake_green_rejected", "harness_exists", "tests_pass", "proof_bundle_valid",
    "report_present", "command_allowlist_exists", "arbitrary_command_rejected",
    "boundary_assertions_present", "provider_mode", "schema", "phase",
    "secret_redaction_passed",
}

NON_SEMANTIC_FIELDS = {
    "base_head", "gate_hash", "timestamp", "duration_seconds", "elapsed_seconds",
    "repo_root", "proof_dir",
}

_FORBIDDEN_PATTERNS = [
    re.compile(r"curl\s", re.IGNORECASE),
    re.compile(r"wget\s", re.IGNORECASE),
    re.compile(r"requests\.get", re.IGNORECASE),
    re.compile(r"httpx", re.IGNORECASE),
    re.compile(r"rm\s+-rf", re.IGNORECASE),
    re.compile(r"git\s+push", re.IGNORECASE),
    re.compile(r"git\s+fetch", re.IGNORECASE),
    re.compile(r"pip\s+install", re.IGNORECASE),
    re.compile(r"pdf", re.IGNORECASE),
    re.compile(r"ocr", re.IGNORECASE),
    re.compile(r"html", re.IGNORECASE),
    re.compile(r"patch\s+-p", re.IGNORECASE),
    re.compile(r"&&"), re.compile(r"\|\|"),
    re.compile(r";"),
    re.compile(r"\$\("),
    re.compile(r"`"),
]

ALLOWED_COMMAND_PREFIXES = (
    "python -m pytest ",
    "python scripts/evals/",
)


def validate_command(cmd: str) -> tuple[bool, str]:
    if not any(cmd.startswith(p) for p in ALLOWED_COMMAND_PREFIXES):
        return False, f"command_not_in_allowlist:{cmd[:60]}"
    for pat in _FORBIDDEN_PATTERNS:
        if pat.search(cmd):
            return False, f"forbidden_pattern:{pat.pattern}"
    return True, ""


KNOWN_CHURN_PATHS = {
    "docs/reports/phases/",
}


def is_known_churn(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in KNOWN_CHURN_PATHS)
