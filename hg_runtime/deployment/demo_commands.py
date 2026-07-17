"""Safe demo commands for Docker deployment.

All commands write receipts, redact secrets, and do not create live effects.
"""

from __future__ import annotations

import json
import sys

from .runtime_config import load_runtime_config, redacted_config
from .health import run_health_check
from .lmstudio_networking import check_lmstudio_endpoint, probe_lmstudio_health
from .database import init_database, list_tables


def cmd_fixture_health() -> dict:
    return run_health_check()


def cmd_print_config_redacted() -> dict:
    cfg = load_runtime_config()
    return redacted_config(cfg)


def cmd_check_lmstudio() -> dict:
    cfg = load_runtime_config()
    endpoint_check = check_lmstudio_endpoint(cfg)
    reachable, models = probe_lmstudio_health(cfg.lmstudio_base_url)
    return {
        "base_url": endpoint_check.base_url,
        "is_container_localhost": endpoint_check.is_container_localhost,
        "is_host_docker_internal": endpoint_check.is_host_docker_internal,
        "is_tailscale_ip": endpoint_check.is_tailscale_ip,
        "is_lan_ip": endpoint_check.is_lan_ip,
        "selected_model": endpoint_check.selected_model,
        "model_allowlisted": endpoint_check.model_allowlisted,
        "model_forbidden": endpoint_check.model_forbidden,
        "endpoint_reachable": reachable,
        "models_available": models[:10],
        "warning": endpoint_check.warning,
    }


def cmd_check_openvino() -> dict:
    from .openvino_models import list_model_dir, is_download_allowed
    cfg = load_runtime_config()
    return {
        "model_dir": cfg.openvino_model_dir,
        "downloads_allowed": is_download_allowed(cfg),
        "models_found": list_model_dir(cfg),
    }


def cmd_init_db() -> dict:
    cfg = load_runtime_config()
    db_path = init_database(cfg)
    tables = list_tables(cfg)
    return {"db_path": db_path, "tables": tables}


def cmd_moral_capsule_fixture_demo() -> dict:
    from hg_runtime.moral_research_capsule.scenario_suite import build_scenario_suite
    from hg_runtime.moral_research_capsule.cohort_registry import build_cohort_registry
    from hg_runtime.moral_research_capsule.fixture_responses import build_fixture_responses
    from hg_runtime.moral_research_capsule.response_loader import build_all_receipts
    from hg_runtime.moral_research_capsule.perspective_matrix import build_perspective_matrix
    from hg_runtime.moral_research_capsule.conflict_map import build_conflict_map
    from hg_runtime.moral_research_capsule.gate import run_gate
    from hg_runtime.moral_research_capsule.evidence_gap_ledger import build_evidence_gap_ledger
    from hg_runtime.moral_research_capsule.uncertainty_ledger import build_uncertainty_ledger
    from hg_runtime.moral_research_capsule.source_ledger import build_source_ledger_placeholders
    from hg_runtime.moral_research_capsule.research_document import build_research_document

    scenarios = build_scenario_suite()
    cohort = build_cohort_registry()
    responses = build_fixture_responses()
    receipts = build_all_receipts(responses)
    cells = build_perspective_matrix(responses, receipts)
    conflicts = build_conflict_map(cells)
    evidence_gaps = build_evidence_gap_ledger(responses)
    uncertainty = build_uncertainty_ledger([s.scenario_id for s in scenarios])
    sources = build_source_ledger_placeholders()
    doc = build_research_document(
        question="How do models frame hard moral dilemmas?",
        scenario_count=len(scenarios), model_count=len(cohort),
        fixture_response_count=len(responses), matrix_cells=cells,
        conflicts=conflicts, evidence_gaps=evidence_gaps,
        uncertainty_records=uncertainty, source_records=sources,
    )
    gate = run_gate(
        scenarios=scenarios, cohort=cohort, receipts=receipts,
        matrix_cells=cells, conflicts=conflicts, evidence_gaps=evidence_gaps,
        uncertainty_records=uncertainty, source_records=sources,
        research_doc=doc, proof_bundle_exists=False,
    )
    return {
        "demo": "moral_capsule_fixture",
        "scenarios": len(scenarios),
        "models": len(cohort),
        "responses": len(responses),
        "matrix_cells": len(cells),
        "conflicts": len(conflicts),
        "evidence_gaps": len(evidence_gaps),
        "gate_verdict": gate["verdict"],
        "gate_checks_passed": gate["checks_passed"],
        "gate_checks_total": gate["checks_total"],
    }


def cmd_write_proof_smoke() -> dict:
    cfg = load_runtime_config()
    from pathlib import Path
    proof_dir = Path(cfg.proof_dir) / "smoke"
    proof_dir.mkdir(parents=True, exist_ok=True)
    smoke = {"smoke": True, "mode": cfg.mode, "live_effects": False}
    (proof_dir / "smoke_proof.json").write_text(json.dumps(smoke, indent=2), encoding="utf-8")
    return {"proof_path": str(proof_dir / "smoke_proof.json"), "written": True}


COMMANDS = {
    "fixture-health": cmd_fixture_health,
    "print-config-redacted": cmd_print_config_redacted,
    "check-lmstudio": cmd_check_lmstudio,
    "check-openvino": cmd_check_openvino,
    "init-db": cmd_init_db,
    "moral-capsule-fixture-demo": cmd_moral_capsule_fixture_demo,
    "write-proof-smoke": cmd_write_proof_smoke,
}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(json.dumps({"error": f"Usage: {sys.argv[0]} <command>", "available": list(COMMANDS.keys())}))
        sys.exit(1)
    result = COMMANDS[sys.argv[1]]()
    print(json.dumps(result, indent=2, default=str))
