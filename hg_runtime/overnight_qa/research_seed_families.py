"""Research seed families for the overnight QA queue expansion.

Every seed is a bounded QUESTION, not a conclusion. Speculation is allowed;
promotion requires evidence. Numerology is not proof. CERN/LHC/collider claims
require extraordinary evidence and falsifiable predictions. No seed promotes to
knowledge by default. Operator review and runtime approval remain mandatory.

Source documents (ingested as short summaries / inspiration only):
- hg-resonance-ideas-frequency-mixing.md
- observer_state_frequency_hypothesis_research_pack.md
- speculative_time_perception_collider_research_note.md
"""

from __future__ import annotations

from .research_seeds import ResearchSeed


_NO_NEW_PHYSICS = "do not claim new physics"
_NO_CERN_MANDELA = "do not claim CERN causes Mandela effects"
_NO_CONSCIOUSNESS_TIME = "do not claim consciousness causes time dilation"
_NO_MANIFEST_PHYSICS = "do not claim manifestation is established physics"
_NO_ATTENTION_COLLAPSE = "do not claim human attention collapses external reality"
_NO_SCHUMANN_CONSCIOUSNESS = "do not claim Schumann resonance proves consciousness coupling"
_NO_FREQ_COINCIDENCE = "do not claim frequency coincidences are evidence"
_NO_HAWKINS_PHYSICAL = "do not claim Hawkins-scale values are physical frequencies"

_COMMON_FORBIDDEN = [_NO_NEW_PHYSICS]


def _seed(**kw) -> ResearchSeed:
    kw.setdefault("operator_review_required", True)
    kw.setdefault("can_promote_to_knowledge", False)
    kw.setdefault("source_policy_required", True)
    kw.setdefault("knowledge_policy_required", True)
    kw.setdefault("receipts_required", True)
    if not kw.get("forbidden_promotions"):
        kw["forbidden_promotions"] = list(_COMMON_FORBIDDEN)
    return ResearchSeed(**kw)


def build_family_seeds() -> list[ResearchSeed]:
    seeds: list[ResearchSeed] = []

    # ---- Family 1: Observer-State / Subjective Time ----
    fam1 = "observer_state_subjective_time"
    seeds.append(_seed(
        seed_id="internal_state_update_rate_model", family=fam1,
        title="Internal state update-rate model of perceived duration",
        short_name="internal_state_update_rate",
        source_kind="mathematical_toy_model", hypothesis_status="toy_model",
        confidence_status="plausible_cognitive",
        seed_text="Perceived duration may scale with the density or salience of internal state transitions.",
        domain_tags=["subjective time", "psychophysics", "information theory", "neuroscience"],
        required_checks=[
            "compare clock time, memory density, attention, arousal, prediction error",
            "derive units", "identify behavioral tests",
            "search interval timing literature later",
        ],
        forbidden_promotions=[_NO_NEW_PHYSICS, "do not claim a proven law of perceived time"],
        falsification_or_constraint_path=["fit fails to beat clock-time baseline under controls"],
        suggested_profile_lenses=["psychophysics researcher", "signal-processing engineer"],
        completion_criteria=["toy model with explicit units and one behavioral test sketched"],
    ))
    seeds.append(_seed(
        seed_id="subjective_time_memory_density", family=fam1,
        title="Subjective time vs novelty / memory density",
        short_name="subjective_time_memory_density",
        source_kind="generated_hypothesis", hypothesis_status="question",
        confidence_status="plausible_cognitive",
        seed_text="Time may feel slow during high novelty or dense memory formation and fast during routine intervals.",
        domain_tags=["subjective time", "memory", "attention", "arousal"],
        required_checks=["compare memory density literature", "compare arousal and attention models",
                         "identify experiments"],
        suggested_profile_lenses=["psychophysics researcher"],
        completion_criteria=["one experiment design referencing existing literature categories"],
    ))

    # ---- Family 2: Collider / High-Energy Coupling Triage ----
    fam2 = "collider_high_energy_triage"
    seeds.append(_seed(
        seed_id="collider_observer_state_coupling", family=fam2,
        title="Collider/observer-state coupling triage",
        short_name="collider_observer_coupling",
        source_kind="operator_note", hypothesis_status="speculative",
        confidence_status="physically_unproven",
        source_documents=["speculative_time_perception_collider_research_note.md"],
        seed_text="Could collider-state variables correlate with human observer-state update dynamics?",
        domain_tags=["collider", "high energy", "observer state", "correlation"],
        required_checks=["define coupling term", "identify collider variables",
                         "require blinded correlation", "check distance/scaling",
                         "reject if no scaling above controls"],
        forbidden_promotions=[_NO_NEW_PHYSICS, _NO_CERN_MANDELA, _NO_CONSCIOUSNESS_TIME],
        falsification_or_constraint_path=["no scaling with luminosity/energy/distance => weaken"],
        suggested_profile_lenses=["skeptical physicist", "proof auditor"],
        completion_criteria=["coupling term defined with units and a null hypothesis g=0"],
    ))
    seeds.append(_seed(
        seed_id="collider_time_dilation_sanity_check", family=fam2,
        title="GR sanity check on collider time dilation",
        short_name="collider_time_dilation_sanity",
        source_kind="literature_gap", hypothesis_status="established",
        confidence_status="known_physics_baseline",
        source_documents=["speculative_time_perception_collider_research_note.md"],
        seed_text="Ordinary gravitational time dilation from collider energy is far too small for human-scale time perception effects.",
        domain_tags=["general relativity", "time dilation", "sanity check"],
        required_checks=["preserve GR sanity calculation",
                         "distinguish particle lifetime dilation from human subjective time",
                         "ensure future research does not confuse collision energy with macroscopic time warp"],
        forbidden_promotions=["do not overstate the baseline as disproving all hypotheses"],
        suggested_profile_lenses=["skeptical physicist"],
        completion_criteria=["GR estimate (~1e-50 scale at 1 m) preserved as baseline"],
        # established baseline is the only status allowed a relaxed promotion stance,
        # but we still keep promotion gated to operator review.
    ))
    seeds.append(_seed(
        seed_id="lhc_frequency_concept_disambiguation", family=fam2,
        title="LHC frequency concept disambiguation",
        short_name="lhc_frequency_disambiguation",
        source_kind="literature_gap", hypothesis_status="established",
        confidence_status="known_physics_baseline",
        source_documents=["speculative_time_perception_collider_research_note.md"],
        seed_text="Collision energy photon-equivalent frequency, bunch-crossing frequency, event rate, and subjective rhythm are different physical concepts.",
        domain_tags=["collider", "frequency", "units", "disambiguation"],
        required_checks=["separate energy-frequency conversion from pulse/event rates",
                         "preserve units", "identify correct CERN/CMS/ATLAS source categories"],
        forbidden_promotions=[_NO_FREQ_COINCIDENCE],
        source_policy_required=True,
        suggested_profile_lenses=["signal-processing engineer", "skeptical physicist"],
        completion_criteria=["table separating 40 MHz bunch crossing from ~1e27 Hz photon-equivalent"],
    ))

    # ---- Family 3: Resonance / Frequency Mixing / Log-Scale Bridges ----
    fam3 = "resonance_frequency_mixing"
    seeds.append(_seed(
        seed_id="schumann_thz_mantissa_bridge", family=fam3,
        title="Schumann/THz mantissa bridge audit",
        short_name="schumann_thz_bridge",
        source_kind="operator_note", hypothesis_status="speculative",
        confidence_status="unsupported_claim_filter",
        source_documents=["hg-resonance-ideas-frequency-mixing.md"],
        seed_text="7.83 Hz and 7.83 THz share a mantissa across 10^12 scale separation; this may be a log-scale pattern worth auditing, not proof.",
        domain_tags=["schumann", "THz", "log-scale", "numerology audit", "frequency"],
        required_checks=["distinguish 7.83 Hz from 7.83 THz", "compute ratio",
                         "identify physical bands", "penalize degrees of freedom",
                         "avoid treating coincidence as evidence"],
        forbidden_promotions=[_NO_FREQ_COINCIDENCE, _NO_SCHUMANN_CONSCIOUSNESS],
        falsification_or_constraint_path=["pattern score below DOF-penalized threshold => discard"],
        suggested_profile_lenses=["signal-processing engineer", "skeptical physicist"],
        completion_criteria=["ratio computed; coincidence scored with degrees-of-freedom penalty"],
    ))
    seeds.append(_seed(
        seed_id="superheterodyne_cognition_metaphor", family=fam3,
        title="Superheterodyne cognition metaphor",
        short_name="superheterodyne_cognition",
        source_kind="operator_note", hypothesis_status="conjecture",
        confidence_status="plausible_cognitive",
        source_documents=["hg-resonance-ideas-frequency-mixing.md"],
        seed_text="Mind/attention/body may be modeled metaphorically as a mixer that converts high-frequency reality into an intermediate experience band.",
        domain_tags=["signal processing", "metaphor", "cognition", "superheterodyne"],
        required_checks=["define carrier, local oscillator, IF, demodulated meaning correspondences",
                         "separate metaphor from physical mechanism",
                         "explore whether signal-processing math suggests useful cognitive models"],
        forbidden_promotions=["do not claim literal RF tuning of reality", _NO_ATTENTION_COLLAPSE],
        suggested_profile_lenses=["signal-processing engineer", "public explainer"],
        completion_criteria=["metaphor mapping table with explicit metaphor-vs-mechanism labels"],
    ))
    seeds.append(_seed(
        seed_id="hawkins_log_frequency_mapping_audit", family=fam3,
        title="Hawkins log-frequency mapping numerology audit",
        short_name="hawkins_log_mapping_audit",
        source_kind="operator_note", hypothesis_status="speculative",
        confidence_status="unsupported_claim_filter",
        source_documents=["hg-resonance-ideas-frequency-mixing.md"],
        seed_text="If Hawkins-style levels are treated as exponential claims, test log-frequency mappings rather than linear Hz, while treating the whole exercise as numerology audit.",
        domain_tags=["hawkins scale", "log mapping", "numerology audit", "frequency"],
        required_checks=["do not assert Hawkins scale is physics", "test log10/log2 mappings",
                         "score coincidences with degree-of-freedom penalty",
                         "require source provenance for Hawkins values",
                         "output 'pattern score', not truth"],
        forbidden_promotions=[_NO_HAWKINS_PHYSICAL, _NO_FREQ_COINCIDENCE],
        source_policy_required=True,
        suggested_profile_lenses=["skeptical physicist", "proof auditor"],
        completion_criteria=["log-fit pattern score with DOF penalty; explicitly labeled not-truth"],
    ))
    seeds.append(_seed(
        seed_id="resonance_pattern_scoring_tool", family=fam3,
        title="Honest frequency-pattern audit tool design",
        short_name="resonance_pattern_scoring_tool",
        source_kind="mathematical_toy_model", hypothesis_status="experiment_design",
        confidence_status="source_required",
        source_documents=["hg-resonance-ideas-frequency-mixing.md"],
        seed_text="Build an honest frequency-pattern audit tool computing ratios, octaves, log distances, constants, wavelength, photon energy, and residual penalties.",
        domain_tags=["tool design", "frequency", "scoring", "multiple comparisons"],
        required_checks=["define input schema", "include constants and references",
                         "include multiple-comparison penalty", "avoid worshipping pretty numbers",
                         "produce ranked hypotheses only"],
        forbidden_promotions=[_NO_FREQ_COINCIDENCE],
        suggested_profile_lenses=["signal-processing engineer"],
        allowed_task_kinds=["tool_design"],
        completion_criteria=["input/output schema with DOF penalty defined"],
    ))

    # ---- Family 4: Consciousness / Attention / Will as Cognitive Variables ----
    fam4 = "attention_will_cognitive_variables"
    seeds.append(_seed(
        seed_id="attention_as_band_selection", family=fam4,
        title="Attention as perceptual band selection (metaphor)",
        short_name="attention_band_selection",
        source_kind="operator_note", hypothesis_status="conjecture",
        confidence_status="plausible_cognitive",
        source_documents=["hg-resonance-ideas-frequency-mixing.md"],
        seed_text="Attention may select the perceptual band; will may sustain lock; emotion may modulate amplitude; memory may provide phase reference.",
        domain_tags=["attention", "will", "salience", "metaphor"],
        required_checks=["translate into cognitive variables",
                         "avoid claiming literal RF tuning of reality",
                         "compare attention/salience/control literature later",
                         "preserve 'authority decides whether action occurs' Hydrogenuine analogy"],
        forbidden_promotions=[_NO_ATTENTION_COLLAPSE],
        suggested_profile_lenses=["psychophysics researcher", "public explainer"],
        completion_criteria=["cognitive-variable translation table"],
    ))
    seeds.append(_seed(
        seed_id="manifestation_as_attention_action_bias", family=fam4,
        title="Manifestation as attention/action-selection bias",
        short_name="manifestation_attention_bias",
        source_kind="operator_note", hypothesis_status="experiment_design",
        confidence_status="plausible_cognitive",
        source_documents=["speculative_time_perception_collider_research_note.md"],
        seed_text="Manifestation may be reframed as attention, salience, action selection, memory retrieval, and opportunity detection rather than external quantum control.",
        domain_tags=["manifestation", "attention", "action selection", "cognition"],
        required_checks=["define attention/action model", "design blinded/control tests",
                         "separate outcome noticing from outcome causation",
                         "forbid paranormal promotion without evidence"],
        forbidden_promotions=[_NO_MANIFEST_PHYSICS, _NO_ATTENTION_COLLAPSE],
        falsification_or_constraint_path=["no outcome change beyond attention/action under blinding => conventional"],
        suggested_profile_lenses=["psychophysics researcher", "proof auditor"],
        completion_criteria=["blinded experiment design separating noticing from causation"],
    ))
    seeds.append(_seed(
        seed_id="observer_attention_internal_state_distribution", family=fam4,
        title="Attention changes internal state distribution (safe quantum-adjacent framing)",
        short_name="attention_internal_state",
        source_kind="operator_note", hypothesis_status="conjecture",
        confidence_status="plausible_cognitive",
        source_documents=["speculative_time_perception_collider_research_note.md"],
        seed_text="A safe quantum-adjacent framing: attention changes the observer's internal state distribution, not external quantum reality.",
        domain_tags=["attention", "quantum measurement", "boundary filter"],
        required_checks=["distinguish quantum measurement from human attention",
                         "avoid consciousness-collapse claims", "compare neuroscience/psychology first"],
        forbidden_promotions=[_NO_ATTENTION_COLLAPSE],
        suggested_profile_lenses=["skeptical physicist", "psychophysics researcher"],
        completion_criteria=["explicit separation of measurement-decoherence from attention"],
    ))

    # ---- Family 5: Memory Anomalies / Mandela / Social Propagation ----
    fam5 = "memory_anomalies_mandela"
    seeds.append(_seed(
        seed_id="mandela_effect_memory_model", family=fam5,
        title="Mandela effects as reconstructive memory + social propagation",
        short_name="mandela_memory_model",
        source_kind="literature_gap", hypothesis_status="literature_review",
        confidence_status="unsupported_claim_filter",
        source_documents=["observer_state_frequency_hypothesis_research_pack.md"],
        seed_text="Memory anomalies may be better modeled through reconstructive memory, familiarity, source confusion, and social propagation than timeline shifts.",
        domain_tags=["mandela effect", "false memory", "social contagion", "memory"],
        required_checks=["find false-memory literature later",
                         "classify video transcript claims as inspiration only",
                         "design memory-confidence experiment", "no timeline-shift promotion"],
        forbidden_promotions=[_NO_CERN_MANDELA, "do not claim timeline shifts"],
        suggested_profile_lenses=["psychophysics researcher", "proof auditor"],
        completion_criteria=["memory-confidence experiment design referencing false-memory literature"],
    ))
    seeds.append(_seed(
        seed_id="media_exposure_memory_confidence", family=fam5,
        title="Media exposure vs memory confidence study",
        short_name="media_exposure_memory",
        source_kind="experiment_design", hypothesis_status="experiment_design",
        confidence_status="plausible_cognitive",
        seed_text="Public reports of 'timeline' effects may correlate with media exposure, stress, suggestion, familiarity, and source-memory errors.",
        domain_tags=["memory", "media exposure", "survey", "social contagion"],
        required_checks=["identify variables", "design survey/task",
                         "require preregistration", "account for social contagion"],
        forbidden_promotions=[_NO_CERN_MANDELA],
        suggested_profile_lenses=["psychophysics researcher"],
        completion_criteria=["preregistered survey design with social-contagion controls"],
    ))

    # ---- Family 6: Field / Aura / Local Coupling ----
    fam6 = "field_aura_local_coupling"
    seeds.append(_seed(
        seed_id="aura_as_measurable_field_envelope", family=fam6,
        title="Aura as a measurable field envelope (if physical)",
        short_name="aura_field_envelope",
        source_kind="operator_note", hypothesis_status="experiment_design",
        confidence_status="physically_unproven",
        source_documents=["speculative_time_perception_collider_research_note.md"],
        seed_text="If 'aura' is treated physically, define field type, falloff, radius, instrumentation, shielding, and measured coupling target.",
        domain_tags=["aura", "field", "instrumentation", "experiment design"],
        required_checks=["define field units", "define detector", "distance falloff",
                         "shielding tests", "reject experiential-only claims as physical evidence"],
        forbidden_promotions=["do not claim a measured aura without instrumentation"],
        falsification_or_constraint_path=["no distance/shielding relationship => reject as physical"],
        suggested_profile_lenses=["skeptical physicist", "signal-processing engineer"],
        completion_criteria=["field type, units, detector, falloff law specified"],
    ))
    seeds.append(_seed(
        seed_id="local_biofield_measurement_plan", family=fam6,
        title="Local biofield measurement plan",
        short_name="local_biofield_plan",
        source_kind="experiment_design", hypothesis_status="experiment_design",
        confidence_status="physically_unproven",
        source_documents=["observer_state_frequency_hypothesis_research_pack.md"],
        seed_text="Measure local EM/thermal/acoustic/physiological envelopes around humans under controlled attention/arousal states.",
        domain_tags=["biofield", "EM", "thermal", "measurement"],
        required_checks=["magnetometer/RF/electric/thermal instruments",
                         "0.25m/0.5m/1m/2m/4m distances",
                         "controls for movement, temperature, electronics", "no mystical promotion"],
        forbidden_promotions=["do not claim a mystical field"],
        suggested_profile_lenses=["signal-processing engineer"],
        completion_criteria=["instrument list + distance protocol + controls"],
    ))

    # ---- Family 7: Quasiparticles / Bridge Theory Triage ----
    fam7 = "quasiparticle_bridge_triage"
    seeds.append(_seed(
        seed_id="exciton_spin_phonon_observer_bridge", family=fam7,
        title="Exciton/spin/phonon -> observer-state bridge triage",
        short_name="exciton_spin_phonon_bridge",
        source_kind="literature_gap", hypothesis_status="speculative",
        confidence_status="physically_unproven",
        source_documents=["observer_state_frequency_hypothesis_research_pack.md"],
        seed_text="Photons, phonons, spin, electron-hole pairs, and excitons are real physical concepts; connecting them to observer state requires a bridge theory.",
        domain_tags=["excitons", "phonons", "spin", "condensed matter", "bridge theory"],
        required_checks=["define known physics baseline", "define state variables",
                         "define coupling field", "avoid 'particle-hole = timeline switch'",
                         "require equations and measurable outputs"],
        forbidden_promotions=[_NO_NEW_PHYSICS, "do not claim particle-hole timeline switching"],
        source_policy_required=True,
        suggested_profile_lenses=["skeptical physicist", "proof auditor"],
        completion_criteria=["baseline + required coupling equations enumerated"],
    ))
    seeds.append(_seed(
        seed_id="electron_hole_spin_state_change_hypothesis", family=fam7,
        title="Electron/hole/spin/exciton/phonon state-change bridge hypothesis",
        short_name="electron_hole_spin_state_change",
        source_kind="operator_note", hypothesis_status="speculative",
        confidence_status="physically_unproven",
        source_documents=["observer_state_frequency_hypothesis_research_pack.md",
                          "speculative_time_perception_collider_research_note.md"],
        seed_text=(
            "Speculative operator hypothesis: subjective time / observer-state dynamics "
            "may be explored as acceleration of state change in electron-hole pairings, "
            "exciton-like transitions, spin-state changes, phonon coupling, or other "
            "quasiparticle/state-transition processes. This is a hypothesis-generation "
            "frame, not established physics."
        ),
        domain_tags=[
            "electron-hole pairs", "excitons", "spin states", "phonons", "quasiparticles",
            "condensed matter", "quantum state transitions", "observer-state dynamics",
            "subjective time", "state-transition rate", "bridge theory",
        ],
        required_checks=[
            "define 'state'", "define 'state-change rate'",
            "define 'acceleration of state change'",
            "distinguish electron/hole quasiparticle dynamics from neural/cognitive state dynamics",
            "distinguish spin-state transition from conscious observation",
            "distinguish exciton/phonon dynamics from subjective time perception",
            "identify known physics baseline", "identify missing bridge theory",
            "identify units", "identify measurable variables",
            "identify plausible biological substrate, if any",
            "identify failure conditions",
            "compare against conventional cognitive explanations",
            "forbid promotion without evidence",
        ],
        forbidden_promotions=[
            "do not claim electron-hole pairings cause consciousness",
            "do not claim spin states prove consciousness",
            "do not claim excitons cause subjective time",
            "do not claim phonons create timeline shifts",
            "do not claim quasiparticles are observer channels",
            "do not claim new physics", "do not claim CERN/Mandela coupling",
            "do not claim manifestation", "do not claim proof",
        ],
        evidence_requirements=[
            "condensed-matter references for any quasiparticle claim",
            "explicit units and a bridge equation before any quantitative claim",
            "blinded measurable variable separating physics from cognition",
        ],
        falsification_or_constraint_path=[
            "no bridge equation with units => remains metaphor",
            "no measurable variable separating quasiparticle dynamics from cognition => weaken",
        ],
        suggested_profile_lenses=["skeptical physicist", "condensed matter physicist",
                                 "signal-processing engineer", "psychophysics researcher",
                                 "proof auditor", "public-safe explainer"],
        model_lens_suggestions=["units_and_math_audit", "mechanism_builder",
                               "disprove_the_case", "assume_real", "assume_false",
                               "boring_explanation_first", "falsification_design",
                               "synthesis_after_opposition"],
        completion_criteria=["bridge-theory requirements enumerated with units; "
                            "metaphor-vs-mechanism explicitly separated"],
    ))
    seeds.append(_seed(
        seed_id="quasiparticle_bridge_theory_requirements", family=fam7,
        title="Quasiparticle bridge-theory requirements",
        short_name="quasiparticle_bridge_requirements",
        source_kind="literature_gap", hypothesis_status="experiment_design",
        confidence_status="source_required",
        seed_text=(
            "Define what equations, coupling terms, biological substrate, and measurements "
            "would be required before electron/hole, exciton, phonon, or spin language can "
            "meaningfully connect to observer-state or subjective-time claims."
        ),
        domain_tags=["bridge theory", "condensed matter", "coupling terms", "requirements",
                     "quasiparticles", "observer-state dynamics"],
        required_checks=[
            "enumerate required equations and coupling terms",
            "specify units for each term", "specify a candidate biological substrate",
            "specify measurable variables and instruments",
            "specify failure conditions", "require condensed-matter baseline citations later",
        ],
        forbidden_promotions=[
            "do not claim a bridge theory exists", "do not claim new physics",
            "do not claim quasiparticles are observer channels",
        ],
        evidence_requirements=["a written requirements list is a plan, not evidence"],
        suggested_profile_lenses=["condensed matter physicist", "proof auditor",
                                 "skeptical physicist"],
        completion_criteria=["explicit requirements list: equations, units, substrate, "
                            "measurements, failure conditions"],
    ))
    seeds.append(_seed(
        seed_id="electron_hole_switching_metaphor_audit", family=fam7,
        title="Electron-hole switching metaphor audit",
        short_name="electron_hole_metaphor_audit",
        source_kind="literature_gap", hypothesis_status="conjecture",
        confidence_status="unsupported_claim_filter",
        source_documents=["speculative_time_perception_collider_research_note.md"],
        seed_text="Electron-hole pair language may be a useful metaphor for switching/state transitions, but not evidence of 4D channel switching.",
        domain_tags=["electron-hole", "condensed matter", "metaphor", "boundary filter"],
        required_checks=["preserve condensed-matter meaning", "reject unsupported 4D switch claim",
                         "ask what Hamiltonian/field equation would be needed"],
        forbidden_promotions=["do not claim 4D channel switching"],
        suggested_profile_lenses=["skeptical physicist"],
        completion_criteria=["metaphor labeled; required Hamiltonian/field equation named"],
    ))

    # ---- Family 8: Experiment Design / Source Discovery ----
    fam8 = "experiment_design_source_discovery"
    seeds.append(_seed(
        seed_id="subjective_time_experiment_design", family=fam8,
        title="Subjective-time pilot experiment design",
        short_name="subjective_time_experiment",
        source_kind="experiment_design", hypothesis_status="experiment_design",
        confidence_status="plausible_cognitive",
        source_documents=["observer_state_frequency_hypothesis_research_pack.md"],
        seed_text="Design a low-cost pilot experiment testing subjective timing, novelty, attention, arousal, memory density, reaction time, and HRV/EEG if available.",
        domain_tags=["experiment design", "subjective time", "preregistration"],
        required_checks=["preregistration template", "variables", "controls",
                         "failure condition", "no new physics required"],
        forbidden_promotions=[_NO_NEW_PHYSICS],
        suggested_profile_lenses=["psychophysics researcher"],
        completion_criteria=["preregistered pilot with failure condition"],
    ))
    seeds.append(_seed(
        seed_id="geomagnetic_em_correlation_study_design", family=fam8,
        title="Geomagnetic/EM correlation study design",
        short_name="geomagnetic_em_correlation",
        source_kind="experiment_design", hypothesis_status="experiment_design",
        confidence_status="source_required",
        seed_text="Design a blinded long-run correlation between subjective time metrics and geomagnetic/EM/Schumann proxies.",
        domain_tags=["geomagnetic", "EM", "schumann", "correlation", "source discovery"],
        required_checks=["identify datasets later", "correction for multiple comparisons",
                         "sleep/stress/time-of-day controls", "no causal claim from correlation alone"],
        forbidden_promotions=[_NO_SCHUMANN_CONSCIOUSNESS, "do not claim causation from correlation"],
        can_browse_later=True, source_policy_required=True,
        suggested_profile_lenses=["proof auditor", "signal-processing engineer"],
        completion_criteria=["blinded design + multiple-comparison correction plan"],
    ))
    seeds.append(_seed(
        seed_id="collider_status_blind_correlation_design", family=fam8,
        title="Collider-status blinded correlation design",
        short_name="collider_blind_correlation",
        source_kind="experiment_design", hypothesis_status="experiment_design",
        confidence_status="source_required",
        source_documents=["speculative_time_perception_collider_research_note.md"],
        seed_text="If public collider state data is available, design a blinded correlation study with pre-registered lag windows and failure conditions.",
        domain_tags=["collider", "blinded", "correlation", "preregistration"],
        required_checks=["beam off/on/stable beams/ramp/dump/luminosity",
                         "participant timing residuals", "blinding",
                         "controls for media/news timing", "no effect implies weakened hypothesis"],
        forbidden_promotions=[_NO_CERN_MANDELA, "do not claim collider effect without blinded scaling"],
        can_browse_later=True, source_policy_required=True,
        suggested_profile_lenses=["skeptical physicist", "proof auditor"],
        completion_criteria=["preregistered lag windows + failure condition"],
    ))
    seeds.append(_seed(
        seed_id="source_dataset_discovery_queue", family=fam8,
        title="Source dataset discovery queue",
        short_name="source_dataset_discovery",
        source_kind="source_discovery_task", hypothesis_status="source_discovery",
        confidence_status="source_required",
        source_documents=["observer_state_frequency_hypothesis_research_pack.md"],
        seed_text="Find reliable data sources for LHC beam status, Schumann resonance, geomagnetic indices, space weather, timing-task protocols, and false-memory literature.",
        domain_tags=["source discovery", "datasets", "provenance"],
        required_checks=["browsing requires source policy", "source ledger required",
                         "no paywall bypass", "no credentialed access", "no source treated as truth"],
        forbidden_promotions=["do not treat any source as truth"],
        can_browse_later=True, source_policy_required=True,
        suggested_profile_lenses=["proof auditor"],
        allowed_task_kinds=["source_discovery"],
        completion_criteria=["candidate source list with provenance, none promoted"],
    ))
    seeds.append(_seed(
        seed_id="preregistration_template_for_speculative_claims", family=fam8,
        title="Preregistration template for speculative claims",
        short_name="preregistration_template",
        source_kind="experiment_design", hypothesis_status="experiment_design",
        confidence_status="plausible_cognitive",
        seed_text="Create a preregistration template for any observer-state/time-perception experiment.",
        domain_tags=["preregistration", "methodology", "experiment design"],
        required_checks=["hypothesis", "primary/secondary variables", "sample size",
                         "exclusion criteria", "blinding", "statistical test",
                         "multiple-comparison correction", "failure condition"],
        forbidden_promotions=["do not skip failure conditions"],
        suggested_profile_lenses=["proof auditor", "psychophysics researcher"],
        completion_criteria=["reusable preregistration template"],
    ))

    # ---- Family 9: Public Explainers / Boundary Documents ----
    fam9 = "public_explainers_boundary"
    seeds.append(_seed(
        seed_id="public_explainer_new_physics_without_woo", family=fam9,
        title="Public explainer: wonder without woo",
        short_name="public_explainer_no_woo",
        source_kind="public_explainer_task", hypothesis_status="public_explainer",
        confidence_status="plausible_cognitive",
        seed_text="Write a public-safe explainer that preserves wonder while separating known physics, speculative models, unsupported claims, and testable paths.",
        domain_tags=["public explainer", "boundary", "science communication"],
        required_checks=["no CERN fear", "no Mandela proof", "no consciousness-collapse claim",
                         "no manifestation-as-physics claim",
                         "'interesting intuition; define variables; measure first'"],
        forbidden_promotions=[_NO_CERN_MANDELA, _NO_MANIFEST_PHYSICS, _NO_ATTENTION_COLLAPSE],
        suggested_profile_lenses=["public explainer"],
        allowed_task_kinds=["public_explainer"],
        completion_criteria=["explainer with four labeled tiers (known/speculative/unsupported/testable)"],
    ))
    seeds.append(_seed(
        seed_id="hydrogenuine_signal_processing_metaphor", family=fam9,
        title="Hydrogenuine signal-processing metaphor explainer",
        short_name="hg_signal_metaphor",
        source_kind="public_explainer_task", hypothesis_status="public_explainer",
        confidence_status="inspiration_only",
        source_documents=["hg-resonance-ideas-frequency-mixing.md"],
        seed_text="Use receiver/superheterodyne metaphors to explain Hydrogenuine: model as signal processor, memory as phase history, governance as transmitter key, operator intent as will.",
        domain_tags=["public explainer", "metaphor", "hydrogenuine"],
        required_checks=["metaphor labeled", "no physical overclaim",
                         "connect to receipts/proofs/authority boundaries"],
        forbidden_promotions=["do not present metaphor as mechanism"],
        suggested_profile_lenses=["public explainer", "signal-processing engineer"],
        completion_criteria=["labeled-metaphor explainer tied to receipts/authority"],
    ))
    seeds.append(_seed(
        seed_id="speculative_claim_boundary_taxonomy", family=fam9,
        title="Speculative claim boundary taxonomy",
        short_name="claim_boundary_taxonomy",
        source_kind="public_explainer_task", hypothesis_status="public_explainer",
        confidence_status="plausible_cognitive",
        seed_text="Build a taxonomy classifying ideas as known physics, plausible cognitive science, metaphor, speculative bridge, unsupported leap, or unsafe overclaim.",
        domain_tags=["taxonomy", "boundary filter", "public explainer"],
        required_checks=["each claim gets category", "evidence requirement",
                         "promotion status", "forbidden claim list"],
        forbidden_promotions=["do not leave any claim uncategorized"],
        suggested_profile_lenses=["proof auditor", "public explainer"],
        completion_criteria=["taxonomy with category + evidence requirement per claim"],
    ))

    # ---- Family 10: Hydrogenuine / Agent Zero Research Process ----
    fam10 = "agent_zero_research_process"
    seeds.append(_seed(
        seed_id="zero_curiosity_queue_policy", family=fam10,
        title="Zero curiosity queue policy",
        short_name="zero_curiosity_policy",
        source_kind="operator_note", hypothesis_status="question",
        confidence_status="plausible_cognitive",
        seed_text="Let Zero propose which research seed to work on based on profile/model autopilot, but require runtime approval, budget, source policy, and operator review.",
        domain_tags=["policy", "agent zero", "queue", "governance"],
        required_checks=["Zero proposes only", "runtime disposes", "no unbounded tasks",
                         "no promotion without evidence", "morning operator review"],
        forbidden_promotions=["do not let Zero self-authorize a task"],
        suggested_profile_lenses=["proof auditor"],
        completion_criteria=["policy stating propose-only + runtime approval + operator review"],
    ))
    seeds.append(_seed(
        seed_id="profile_lens_selection_for_speculative_research", family=fam10,
        title="Profile lens selection for speculative research",
        short_name="profile_lens_selection",
        source_kind="operator_note", hypothesis_status="question",
        confidence_status="plausible_cognitive",
        seed_text="Select cognitive profiles for speculative research tasks: skeptical physicist, signal-processing engineer, psychophysics researcher, public explainer, proof auditor.",
        domain_tags=["profile overlay", "lens selection", "agent zero"],
        required_checks=["temporary overlays only", "no identity claims", "no consciousness claims",
                         "profile outputs not truth", "comparison without adjudication"],
        forbidden_promotions=["do not treat a profile as identity or authority"],
        suggested_profile_lenses=["skeptical physicist", "signal-processing engineer",
                                  "psychophysics researcher", "public explainer", "proof auditor"],
        completion_criteria=["lens selection map for speculative research scopes"],
    ))
    seeds.append(_seed(
        seed_id="overnight_research_soak_seed_sampler", family=fam10,
        title="Overnight research soak seed sampler",
        short_name="seed_sampler",
        source_kind="operator_note", hypothesis_status="experiment_design",
        confidence_status="plausible_cognitive",
        seed_text="Implement a sampler that picks a bounded subset of seeds for a run and records skipped seeds honestly.",
        domain_tags=["scheduler", "sampler", "agent zero"],
        required_checks=["no pressure to complete all seeds", "bounded task count",
                         "budget by token/time/profile/model", "skipped != failed",
                         "chosen_by_zero != approved_by_runtime"],
        forbidden_promotions=["do not treat chosen_by_zero as approved"],
        suggested_profile_lenses=["proof auditor"],
        completion_criteria=["sampler that records skipped seeds honestly"],
    ))

    # ---- Family 11: CTMU / Self-Reference / Cognition-Reality Boundary ----
    fam11 = "ctmu_self_reference_cognition_reality"
    _NO_CTMU_PHYSICS = "do not claim CTMU is established physics"
    _NO_CTMU_CONSCIOUSNESS = "do not claim CTMU proves consciousness"
    _NO_CTMU_TELEOLOGY = "do not claim teleology is physics unless operationalized"
    _NO_CTMU_TRUTH = "do not treat CTMU source text as truth"
    _NO_CTMU_SOVEREIGNTY = "do not claim CTMU proves sovereign AI or sovereign cognition"

    seeds.append(_seed(
        seed_id="ctmu_self_reference_cognition_reality_boundary",
        family=fam11,
        title="CTMU / Cognitive-Theoretic Model of the Universe — Self-Reference, Cognition, and Reality Boundary Audit",
        short_name="ctmu_boundary_audit",
        source_kind="operator_note",
        hypothesis_status="speculative",
        confidence_status="physically_unproven",
        seed_text=(
            "Can CTMU's claims about cognition, self-reference, reality-as-language, and "
            "self-processing information be translated into bounded mathematical/philosophical "
            "subclaims without treating them as established physics or empirical truth? "
            "CTMU uses formal language about self-reference, telesis, conspansion, and "
            "self-configuring self-processing language (SCSPL). These must be audited for "
            "mathematical rigor, empirical falsifiability, terminology inflation, and "
            "unsupported leaps before any use."
        ),
        domain_tags=[
            "CTMU", "self-reference", "formal language", "cognition",
            "reality boundary", "teleology", "metaphysics",
            "information theory", "philosophy of mind", "process philosophy",
            "speculative_bridge", "metaphysical_claim", "formal_language_claim",
            "self_reference_claim", "cognition_reality_boundary",
            "teleology_claim", "high_overclaim_risk", "empirical_gap",
            "public_claim_risk",
        ],
        required_checks=[
            "build claim stack from source text",
            "define term glossary (telesis, conspansion, SCSPL, syndiffeonesis, etc.)",
            "separate formal claims from metaphorical claims",
            "inventory all empirical claims",
            "inventory all non-empirical metaphysical claims",
            "compare to mainstream adjacent fields: fixed-point logic, formal language theory, "
            "information theory, cybernetics, dynamical systems, active inference, "
            "quantum-like cognition, philosophy of mind, process philosophy",
            "list unsupported leaps",
            "list what would be needed for scientific support",
            "mathematical rigor audit",
            "empirical falsifiability audit",
            "physics compatibility audit",
            "terminology inflation audit",
            "unsupported inference audit",
            "public claim safety audit",
            "write public-safe summary",
            "write rejection list: what cannot be concluded",
        ],
        forbidden_promotions=[
            _NO_CTMU_PHYSICS,
            _NO_CTMU_CONSCIOUSNESS,
            _NO_CTMU_TELEOLOGY,
            _NO_CTMU_TRUTH,
            _NO_CTMU_SOVEREIGNTY,
            "do not claim CTMU is proven mathematics",
            "do not claim self-reference is evidence of consciousness",
            "do not claim mathematical language is proof of empirical physics",
            "do not claim metaphor is mechanism",
            "do not use CTMU in investor or public product claims",
            "do not promote CTMU output to memory or knowledge",
            _NO_NEW_PHYSICS,
        ],
        evidence_requirements=[
            "source-grounded review of CTMU primary texts required",
            "comparison to mainstream adjacent fields required before any assessment",
            "mathematical rigor audit required before treating formalism as valid",
            "empirical falsifiability audit required before treating as physics",
            "operator review required before any output use",
        ],
        falsification_or_constraint_path=[
            "no operationalizable prediction => remains metaphysics",
            "no mathematical rigor beyond natural language => remains philosophy",
            "no empirical test design => remains unfalsifiable",
            "terminology inflation without formal definitions => reject as vague",
        ],
        source_documents=[
            "https://www.learnctmu.com/",
            "https://ctmucommunity.org/wiki/Cognitive-Theoretic_Model_of_the_Universe",
        ],
        suggested_profile_lenses=[
            "skeptical physicist", "formal logician", "philosophy of mind researcher",
            "proof auditor", "public-safe explainer",
        ],
        model_lens_suggestions=[
            "boring_explanation_first", "disprove_the_case",
            "units_and_math_audit", "assume_false",
            "falsification_design", "synthesis_after_opposition",
        ],
        can_browse_later=True,
        can_promote_to_knowledge=False,
        source_policy_required=True,
        priority_hint="low",
        budget_hint="medium",
        completion_criteria=[
            "claim stack built",
            "term glossary complete",
            "metaphor/mechanism split explicit",
            "formalism inventory with rigor assessment",
            "empirical-claim inventory with falsifiability assessment",
            "comparison to mainstream adjacent fields complete",
            "unsupported-leap audit complete",
            "public-safe summary written",
            "rejection list written",
        ],
    ))
    seeds.append(_seed(
        seed_id="ctmu_source_candidate_learnctmu",
        family=fam11,
        title="CTMU source candidate: learnctmu.com",
        short_name="ctmu_source_learnctmu",
        source_kind="source_discovery_task",
        hypothesis_status="source_discovery",
        confidence_status="source_required",
        seed_text=(
            "Source candidate: https://www.learnctmu.com/ — "
            "Community educational site for CTMU. Retrieval mode: read-only GET. "
            "Source type: speculative_theory_site. Trust score: unscored until reviewed. "
            "Risk score: high. Source is not truth."
        ),
        domain_tags=[
            "CTMU", "source candidate", "speculative_theory_site",
            "high_overclaim_risk", "public_claim_risk",
        ],
        required_checks=[
            "read-only retrieval only",
            "source is not truth",
            "extract claims for boundary audit",
            "do not treat as established science",
        ],
        forbidden_promotions=[
            _NO_CTMU_PHYSICS, _NO_CTMU_TRUTH,
            "do not treat source text as knowledge",
        ],
        source_documents=["https://www.learnctmu.com/"],
        can_browse_later=True,
        source_policy_required=True,
        allowed_task_kinds=["source_discovery"],
        completion_criteria=["source fetched, claims extracted, boundary audit initiated"],
    ))
    seeds.append(_seed(
        seed_id="ctmu_source_candidate_wiki",
        family=fam11,
        title="CTMU source candidate: ctmucommunity.org wiki",
        short_name="ctmu_source_wiki",
        source_kind="source_discovery_task",
        hypothesis_status="source_discovery",
        confidence_status="source_required",
        seed_text=(
            "Source candidate: https://ctmucommunity.org/wiki/Cognitive-Theoretic_Model_of_the_Universe — "
            "Community wiki for CTMU. Retrieval mode: read-only GET. "
            "Source type: wiki. Trust score: unscored until reviewed. "
            "Risk score: high. Source is not truth."
        ),
        domain_tags=[
            "CTMU", "source candidate", "wiki",
            "high_overclaim_risk", "public_claim_risk",
        ],
        required_checks=[
            "read-only retrieval only",
            "source is not truth",
            "extract claims for boundary audit",
            "do not treat as established science",
            "wiki content may be community-edited, not peer-reviewed",
        ],
        forbidden_promotions=[
            _NO_CTMU_PHYSICS, _NO_CTMU_TRUTH,
            "do not treat wiki content as authoritative",
        ],
        source_documents=["https://ctmucommunity.org/wiki/Cognitive-Theoretic_Model_of_the_Universe"],
        can_browse_later=True,
        source_policy_required=True,
        allowed_task_kinds=["source_discovery"],
        completion_criteria=["source fetched, claims extracted, boundary audit initiated"],
    ))

    return seeds
