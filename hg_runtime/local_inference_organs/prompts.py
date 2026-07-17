"""Harmless bounded prompts for Phase 33.6 organ tasks."""

from hg_runtime.local_inference_organs.schemas import ADVISORY_LABEL


def organ_prompt(role: str, cycle: int) -> str:
    contracts = {
        "tiny_router": {
            "advisory_marker": ADVISORY_LABEL,
            "role": "tiny_router",
            "task_class": "repair_proposal",
            "severity_hint": "HIGH",
            "affected_component_hint": "Phase 33.6 local_inference_organs",
            "next_route": "small_coder",
            "confidence": "LOW",
        },
        "small_coder": {
            "advisory_marker": ADVISORY_LABEL,
            "role": "small_coder",
            "observed_failure": "LOCAL_TEST failed",
            "likely_root_cause": "UNKNOWN",
            "affected_files": ["UNKNOWN"],
            "affected_tests": ["LOCAL_TEST"],
            "required_tests": ["LOCAL_TEST"],
            "implementation_shape": ["UNKNOWN"],
            "acceptance_criteria": ["LOCAL_TEST passes"],
            "confidence": "LOW",
        },
        "small_code_reviewer": {
            "advisory_marker": ADVISORY_LABEL,
            "role": "small_code_reviewer",
            "specificity_findings": ["UNKNOWN"],
            "missing_evidence": ["UNKNOWN"],
            "authority_risks": ["none"],
            "external_side_effect_risks": ["none"],
            "ready_for_spec_tests_plans_recommendation": False,
            "required_sharpening": ["UNKNOWN"],
            "confidence": "LOW",
        },
        "small_doc_writer": {
            "advisory_marker": ADVISORY_LABEL,
            "role": "small_doc_writer",
            "proposal_id": "P33_6_ORGAN_OUTPUT_CONFORMITY_REPAIR",
            "title": "P33.6 organ output conformity repair",
            "severity": "HIGH",
            "phase_or_component": "Phase 33.6 local_inference_organs",
            "observed_failure": "LOCAL_TEST failed",
            "reproduction_steps": ["python scripts/evals/autonomous_agent_phase_33_6_local_multi_organ_inference_bus_gate.py"],
            "expected_behavior": "structured advisory output",
            "actual_behavior": "UNKNOWN",
            "evidence_refs": ["UNKNOWN"],
            "affected_files": ["UNKNOWN"],
            "affected_tests": ["LOCAL_TEST"],
            "affected_commands": ["python scripts/evals/autonomous_agent_phase_33_6_local_multi_organ_inference_bus_gate.py"],
            "authority_risk": "LOW",
            "external_side_effect_risk": "LOW",
            "likely_root_cause": "UNKNOWN",
            "required_spec_changes": ["UNKNOWN"],
            "required_test_changes": ["LOCAL_TEST"],
            "required_implementation_changes": ["UNKNOWN"],
            "acceptance_criteria": ["P33.6 gate records structured advisory output"],
            "ready_for_spec_tests_plans": False,
        },
    }
    contract = contracts.get(role, contracts["tiny_router"])
    return (
        f"Role {role}, cycle {cycle}. Return ONLY one minified JSON object matching this exact key set: "
        f"{contract}. Do not write prose. Do not use markdown. Do not call tools. "
        "Do not authorize anything. Use UNKNOWN for missing facts."
    )


__all__ = ["organ_prompt"]
