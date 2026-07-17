"""DSE-FINAL registry and integration checks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DseGateEntry:
    tranche_id: str
    gate_script: str
    audit_doc: str
    feature_check_fn: str
    test_dir: str


DSE_GATES: tuple[DseGateEntry, ...] = (
    DseGateEntry("DSE-FOUNDATION", "scripts/evals/dse_foundation_gate.py", "docs/reports/phases/DSE_FOUNDATION_AUDIT.md", "run_dse_foundation_checks", "tests/dse_foundation"),
    DseGateEntry("INFER-DSE", "scripts/evals/infer_durable_sink_gate.py", "docs/reports/phases/INFER_DSE_AUDIT.md", "run_infer_dse_checks", "tests/infer_dse"),
    DseGateEntry("MEM-DSE", "scripts/evals/mem_durable_sink_gate.py", "docs/reports/phases/MEM_DSE_AUDIT.md", "run_mem_dse_checks", "tests/mem_dse"),
    DseGateEntry("GMG-DSE", "scripts/evals/gmg_durable_sink_gate.py", "docs/reports/phases/GMG_DSE_AUDIT.md", "run_gmg_dse_checks", "tests/gmg_dse"),
    DseGateEntry("OEA-TER-DSE", "scripts/evals/oea_ter_durable_sink_gate.py", "docs/reports/phases/OEA_TER_DSE_AUDIT.md", "run_oea_ter_dse_checks", "tests/oea_ter_dse"),
    DseGateEntry("SRP-DSE", "scripts/evals/srp_durable_sink_gate.py", "docs/reports/phases/SRP_DSE_AUDIT.md", "run_srp_dse_checks", "tests/srp_dse"),
    DseGateEntry("SEN-DSE", "scripts/evals/sen_durable_sink_gate.py", "docs/reports/phases/SEN_DSE_AUDIT.md", "run_sen_dse_checks", "tests/sen_dse"),
    DseGateEntry("PUB-EXT-DSE", "scripts/evals/pub_ext_durable_sink_gate.py", "docs/reports/phases/PUB_EXT_DSE_AUDIT.md", "run_pub_ext_dse_checks", "tests/pub_ext_dse"),
    DseGateEntry("REB-DSE", "scripts/evals/reb_durable_sink_gate.py", "docs/reports/phases/REB_DSE_AUDIT.md", "run_reb_dse_checks", "tests/reb_dse"),
    DseGateEntry("RIB-DSE", "scripts/evals/rib_durable_sink_gate.py", "docs/reports/phases/RIB_DSE_AUDIT.md", "run_rib_dse_checks", "tests/rib_dse"),
    DseGateEntry("ALOOP-DSE", "scripts/evals/aloop_durable_sink_gate.py", "docs/reports/phases/ALOOP_DSE_AUDIT.md", "run_aloop_dse_checks", "tests/aloop_dse"),
)


def run_dse_final_checks() -> dict[str, object]:
    from hg_core.dse.gate_runner import run_dse_foundation_checks
    from hg_core.dse.tranche_gates import (
        run_aloop_dse_checks,
        run_gmg_dse_checks,
        run_infer_dse_checks,
        run_mem_dse_checks,
        run_oea_ter_dse_checks,
        run_pub_ext_dse_checks,
        run_reb_dse_checks,
        run_rib_dse_checks,
        run_sen_dse_checks,
        run_srp_dse_checks,
    )

    runners = {
        "run_dse_foundation_checks": run_dse_foundation_checks,
        "run_infer_dse_checks": run_infer_dse_checks,
        "run_mem_dse_checks": run_mem_dse_checks,
        "run_gmg_dse_checks": run_gmg_dse_checks,
        "run_oea_ter_dse_checks": run_oea_ter_dse_checks,
        "run_srp_dse_checks": run_srp_dse_checks,
        "run_sen_dse_checks": run_sen_dse_checks,
        "run_pub_ext_dse_checks": run_pub_ext_dse_checks,
        "run_reb_dse_checks": run_reb_dse_checks,
        "run_rib_dse_checks": run_rib_dse_checks,
        "run_aloop_dse_checks": run_aloop_dse_checks,
    }

    checks: list[dict[str, object]] = []
    for entry in DSE_GATES:
        fn = runners[entry.feature_check_fn]
        result = fn()
        checks.append(
            {
                "check_id": f"dse_gate_{entry.tranche_id}",
                "ok": result.get("ok"),
                "detail": entry.tranche_id,
            }
        )

    checks.append(
        {
            "check_id": "all_tranches_have_real_sink",
            "ok": all(c["ok"] for c in checks),
            "detail": len(DSE_GATES),
        }
    )

    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


__all__ = ["DSE_GATES", "DseGateEntry", "run_dse_final_checks"]
