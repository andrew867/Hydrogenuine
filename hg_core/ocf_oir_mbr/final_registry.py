"""OCF/OIR/MBR final registry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OcfOirMbrGateEntry:
    feature_id: str
    gate_script: str
    audit_doc: str
    feature_check_fn: str
    test_dir: str


OCF_OIR_MBR_GATES: tuple[OcfOirMbrGateEntry, ...] = (
    OcfOirMbrGateEntry("OCF", "scripts/evals/ocf_organ_control_fields_gate.py", "docs/reports/phases/OCF_FULL_SCOPED_COMPLETION_AUDIT.md", "run_ocf_feature_checks", "tests/ocf"),
    OcfOirMbrGateEntry("OIR", "scripts/evals/oir_organ_interaction_renormalization_gate.py", "docs/reports/phases/OIR_FULL_SCOPED_COMPLETION_AUDIT.md", "run_oir_feature_checks", "tests/oir"),
    OcfOirMbrGateEntry("MBR", "scripts/evals/mbr_many_body_renormalization_gate.py", "docs/reports/phases/MBR_FULL_SCOPED_COMPLETION_AUDIT.md", "run_mbr_feature_checks", "tests/mbr"),
    OcfOirMbrGateEntry("INTEGRATION", "scripts/evals/ocf_oir_mbr_integration_gate.py", "docs/reports/phases/OCF_OIR_MBR_INTEGRATION_AUDIT.md", "run_integration_feature_checks", "tests/ocf_oir_mbr"),
)


def run_ocf_oir_mbr_final_checks() -> dict[str, object]:
    from hg_core.mbr.gate_runner import run_mbr_feature_checks
    from hg_core.ocf.gate_runner import run_ocf_feature_checks
    from hg_core.ocf_oir_mbr.integration_gate import run_integration_feature_checks
    from hg_core.oir.gate_runner import run_oir_feature_checks

    runners = {
        "run_ocf_feature_checks": run_ocf_feature_checks,
        "run_oir_feature_checks": run_oir_feature_checks,
        "run_mbr_feature_checks": run_mbr_feature_checks,
        "run_integration_feature_checks": run_integration_feature_checks,
    }
    checks: list[dict[str, object]] = []
    for entry in OCF_OIR_MBR_GATES:
        result = runners[entry.feature_check_fn]()
        checks.append({"check_id": f"gate_{entry.feature_id}", "ok": result.get("ok"), "detail": entry.feature_id})
    checks.append({"check_id": "all_features_green", "ok": all(c["ok"] for c in checks), "detail": len(OCF_OIR_MBR_GATES)})
    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


__all__ = ["OCF_OIR_MBR_GATES", "OcfOirMbrGateEntry", "run_ocf_oir_mbr_final_checks"]
