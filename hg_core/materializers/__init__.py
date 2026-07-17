"""
Sticky Reality materializers: deterministic derived views from the canonical ledger.
"""

from pathlib import Path

from .molecules_materializer import run as run_molecules
from .decision_materializer import run as run_decision
from .reputation_materializer import run as run_reputation
from .observations_indexer import run as run_observations_indexer
from .metacognition_metrics import run as run_metacognition_metrics
from .temporal_indexer import run as run_temporal_indexer
from .social_indexer import run as run_social_indexer
from .affective_indexer import run as run_affective_indexer
from .extras_indexer import run as run_extras_indexer
from .work_items_indexer import run as run_work_items_indexer
from .drift_indexer import run as run_drift_indexer
from .steering_state_indexer import run as run_steering_state_indexer
from .goal_integrity_indexer import run as run_goal_integrity_indexer
from .group_drift_indexer import run as run_group_drift_indexer
from .operator_guardrails_indexer import run as run_operator_guardrails_indexer


def run_all(workspace_root: Path, rebuild: bool = False) -> None:
    """Run all materializers (including drift and Pack 7 steering/guardrails)."""
    run_molecules(workspace_root, rebuild=rebuild)
    run_decision(workspace_root, rebuild=rebuild)
    run_reputation(workspace_root, rebuild=rebuild)
    run_observations_indexer(workspace_root, rebuild=rebuild)
    run_metacognition_metrics(workspace_root, rebuild=rebuild)
    run_temporal_indexer(workspace_root, rebuild=rebuild)
    run_social_indexer(workspace_root, rebuild=rebuild)
    run_affective_indexer(workspace_root, rebuild=rebuild)
    run_extras_indexer(workspace_root, rebuild=rebuild)
    run_work_items_indexer(workspace_root, rebuild=rebuild)
    run_drift_indexer(workspace_root, rebuild=rebuild)
    run_steering_state_indexer(workspace_root, rebuild=rebuild)
    run_goal_integrity_indexer(workspace_root, rebuild=rebuild)
    run_group_drift_indexer(workspace_root, rebuild=rebuild)
    run_operator_guardrails_indexer(workspace_root, rebuild=rebuild)
