"""
Sticky Reality Ch3: Metacognition — self-assessment, tool outcomes, calibration, proof-path.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .self_assess import record_self_assessment
from .tool_outcomes import record_tool_outcome
from .capability_profile import publish_capability_profile
from .postmortem import record_postmortem
from .artifacts import write_reflection_artifact
from .proof_path import get_proof_path, export_proof_path
from .api import list_self_assessments, get_calibration_metrics, get_tool_reliability, check_has_self_assessment

__all__ = [
    "record_self_assessment",
    "record_tool_outcome",
    "publish_capability_profile",
    "record_postmortem",
    "write_reflection_artifact",
    "get_proof_path",
    "export_proof_path",
    "list_self_assessments",
    "get_calibration_metrics",
    "get_tool_reliability",
    "check_has_self_assessment",
]
