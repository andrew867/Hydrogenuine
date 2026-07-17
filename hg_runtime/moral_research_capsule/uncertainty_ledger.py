"""Uncertainty ledger for moral research capsule."""

from __future__ import annotations

from .schemas import UncertaintyRecord


def build_uncertainty_ledger(scenario_ids: list[str]) -> list[UncertaintyRecord]:
    records: list[UncertaintyRecord] = []
    counter = 0

    structural = [
        ("fixture_only_limitation", "All responses are fixture data, not live model output", "high"),
        ("model_cohort_limitation", "Only a subset of available models is represented", "high"),
        ("overtraining_benchmark_risk", "Trolley-variant scenarios are heavily overtrained in most model families", "medium"),
    ]
    for kind, desc, severity in structural:
        counter += 1
        records.append(UncertaintyRecord(
            record_id=f"unc-{counter:04d}",
            scenario_id="*",
            kind=kind,
            description=desc,
            severity=severity,
        ))

    per_scenario = {
        "classic_trolley": [
            ("scenario_ambiguity", "Classic formulation abstracts away real-world context"),
            ("overtraining_benchmark_risk", "Most models have seen this scenario thousands of times in training"),
        ],
        "doctor_transplant": [
            ("missing_empirical_data", "No real medical prognosis data for the five patients"),
            ("scenario_ambiguity", "Scenario assumes no other medical options exist"),
        ],
        "self_driving_car_allocation": [
            ("missing_legal_context", "Liability framework depends on jurisdiction"),
            ("missing_empirical_data", "Crash scenario probabilities are unspecified"),
        ],
        "pandemic_ventilator_allocation": [
            ("missing_medical_prognosis", "Individual patient prognoses not specified"),
            ("missing_empirical_data", "Survival statistics for each patient group unknown"),
        ],
        "whistleblower_vs_social_stability": [
            ("missing_legal_context", "Whistleblower protection laws vary by jurisdiction"),
            ("missing_empirical_data", "Actual corruption scope and unrest probability unknown"),
        ],
        "family_loyalty_vs_public_law": [
            ("missing_legal_context", "Family exemption laws vary by jurisdiction"),
            ("missing_cultural_evidence", "Family loyalty norms claimed without survey data"),
        ],
        "poverty_bribery_dilemma": [
            ("missing_empirical_data", "Healthcare access data for the specific context missing"),
            ("missing_affected_party_preferences", "Parent and community preferences not surveyed"),
        ],
        "censorship_vs_social_harmony": [
            ("missing_legal_context", "Free speech jurisprudence varies by jurisdiction"),
            ("missing_empirical_data", "Hate speech impact data not specified"),
        ],
        "factory_vs_small_shops_economic_triage": [
            ("missing_economic_data", "Actual economic impact figures not provided"),
            ("missing_affected_party_preferences", "Worker and shop owner preferences not surveyed"),
        ],
        "ai_harm_ranking_across_cultures": [
            ("missing_cultural_evidence", "No cross-cultural survey data provided"),
            ("missing_affected_party_preferences", "Affected populations not consulted"),
        ],
    }

    for sid in scenario_ids:
        for kind, desc in per_scenario.get(sid, []):
            counter += 1
            records.append(UncertaintyRecord(
                record_id=f"unc-{counter:04d}",
                scenario_id=sid,
                kind=kind,
                description=desc,
            ))

    return records
