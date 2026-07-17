"""
Layer 9: Alignment Science & Safety Research.
Process-oriented evaluation, attribution/provenance, debate, scenario tagging, evidence bundles.
"""
from hg_core.alignment_science.schemas import (
    ProcessAuditResult,
    AttributionResult,
    MemorizationResult,
    RegurgitationVsLearnedResult,
    DebateOutcome,
    DebateTurn,
    EvalCase,
    EvalRunResult,
    MagnificationResult,
    ScenarioTag,
    EvidenceBundle,
    PolicyBriefing,
    InfluentialInput,
    process_audit_result,
    attribution_result,
    memorization_result,
    regurgitation_vs_learned_result,
    debate_turn,
    debate_outcome,
    eval_case,
    eval_run_result,
    magnification_result,
    scenario_tag,
    evidence_bundle,
    policy_briefing,
    validate_process_audit_result,
    validate_attribution_result,
    validate_memorization_result,
    validate_regurgitation_vs_learned_result,
    validate_debate_outcome,
    validate_eval_case,
    validate_eval_run_result,
    validate_magnification_result,
    validate_scenario_tag,
    validate_evidence_bundle,
    validate_policy_briefing,
)

__all__ = [
    "ProcessAuditResult",
    "AttributionResult",
    "MemorizationResult",
    "RegurgitationVsLearnedResult",
    "DebateOutcome",
    "DebateTurn",
    "EvalCase",
    "EvalRunResult",
    "MagnificationResult",
    "ScenarioTag",
    "EvidenceBundle",
    "PolicyBriefing",
    "InfluentialInput",
    "process_audit_result",
    "attribution_result",
    "memorization_result",
    "regurgitation_vs_learned_result",
    "debate_turn",
    "debate_outcome",
    "eval_case",
    "eval_run_result",
    "magnification_result",
    "scenario_tag",
    "evidence_bundle",
    "policy_briefing",
    "validate_process_audit_result",
    "validate_attribution_result",
    "validate_memorization_result",
    "validate_regurgitation_vs_learned_result",
    "validate_debate_outcome",
    "validate_eval_case",
    "validate_eval_run_result",
    "validate_magnification_result",
    "validate_scenario_tag",
    "validate_evidence_bundle",
    "validate_policy_briefing",
]

# Phase 2: process audit
from hg_core.alignment_science.process_audit import (
    run_process_audit,
    get_process_audit,
    get_process_audit_for_run,
)
from hg_core.alignment_science.api import (
    get_process_audit_api,
    run_process_audit_api,
)

__all__ += [
    "run_process_audit",
    "get_process_audit",
    "get_process_audit_for_run",
    "get_process_audit_api",
    "run_process_audit_api",
]

# Phase 3: attribution, memorization, regurgitation
from hg_core.alignment_science.attribution import run_attribution, get_attribution
from hg_core.alignment_science.memorization import run_memorization_detection, get_memorization_result
from hg_core.alignment_science.regurgitation import run_regurgitation_vs_learned, get_regurgitation_result
from hg_core.alignment_science.api import (
    get_attribution_api,
    run_attribution_api,
    get_memorization_api,
    run_memorization_api,
    get_regurgitation_api,
    run_regurgitation_api,
)

__all__ += [
    "run_attribution",
    "get_attribution",
    "run_memorization_detection",
    "get_memorization_result",
    "run_regurgitation_vs_learned",
    "get_regurgitation_result",
    "get_attribution_api",
    "run_attribution_api",
    "get_memorization_api",
    "run_memorization_api",
    "get_regurgitation_api",
    "run_regurgitation_api",
]

# Phase 4: debate, eval pipeline, magnification
from hg_core.alignment_science.debate import run_debate, get_debate_outcome
from hg_core.alignment_science.eval_pipeline import (
    generate_eval_cases,
    get_eval_cases,
    run_eval_scorer,
    get_eval_run_result,
)
from hg_core.alignment_science.magnification import run_magnification, get_magnification_result
from hg_core.alignment_science.api import (
    get_debate_api,
    run_debate_api,
    generate_eval_cases_api,
    get_eval_cases_api,
    run_eval_scorer_api,
    get_eval_run_api,
    run_magnification_api,
    get_magnification_api,
)

__all__ += [
    "run_debate",
    "get_debate_outcome",
    "generate_eval_cases",
    "get_eval_cases",
    "run_eval_scorer",
    "get_eval_run_result",
    "run_magnification",
    "get_magnification_result",
    "get_debate_api",
    "run_debate_api",
    "generate_eval_cases_api",
    "get_eval_cases_api",
    "run_eval_scorer_api",
    "get_eval_run_api",
    "run_magnification_api",
    "get_magnification_api",
]

# Phase 5: scenario tagger, evidence bundle, alarm
from hg_core.alignment_science.scenario_tagger import run_scenario_tagger, get_scenario_tag
from hg_core.alignment_science.evidence_bundle import (
    build_evidence_bundle,
    get_evidence_bundle,
    export_evidence_bundle,
)
from hg_core.alignment_science.api import (
    get_scenario_tag_api,
    run_scenario_tagger_api,
    build_evidence_bundle_api,
    get_evidence_bundle_api,
    export_evidence_bundle_api,
)

__all__ += [
    "run_scenario_tagger",
    "get_scenario_tag",
    "build_evidence_bundle",
    "get_evidence_bundle",
    "export_evidence_bundle",
    "get_scenario_tag_api",
    "run_scenario_tagger_api",
    "build_evidence_bundle_api",
    "get_evidence_bundle_api",
    "export_evidence_bundle_api",
]

# Phase 6 (optional): situational-awareness testbed
from hg_core.alignment_science.situational_awareness import (
    run_testbed,
    get_testbed_run_result,
    testbed_config,
    probe_result,
    TestbedConfig,
    ProbeResult,
    TestbedRunResult,
)
from hg_core.alignment_science.api import (
    run_testbed_api,
    get_testbed_run_api,
)

__all__ += [
    "run_testbed",
    "get_testbed_run_result",
    "testbed_config",
    "probe_result",
    "TestbedConfig",
    "ProbeResult",
    "TestbedRunResult",
    "run_testbed_api",
    "get_testbed_run_api",
]
