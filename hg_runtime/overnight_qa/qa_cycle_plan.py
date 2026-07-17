"""Plan for the future 12-hour overnight QA / knowledge-acquisition run."""

from __future__ import annotations

from dataclasses import asdict

from .schemas import QACyclePlan


def build_default_plan(browsing_enabled: bool = False) -> QACyclePlan:
    return QACyclePlan(
        duration_target_hours=12,
        mode="qa_knowledge_acquisition_curiosity",
        local_inference_optional=True,
        browsing_enabled=browsing_enabled,
        checkpoint_cadence_minutes=30,
        proof_bundle_cadence_minutes=60,
        stop_panic_checks_enabled=True,
        operator_morning_review_required=True,
    )


def plan_snapshot(plan: QACyclePlan) -> dict:
    return asdict(plan)
