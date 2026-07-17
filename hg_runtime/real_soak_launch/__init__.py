"""Real soak launch — Phase 24.5."""

from __future__ import annotations

from hg_runtime.real_soak_launch.launch_preflight import run_launch_preflight
from hg_runtime.real_soak_launch.launch_runner import run_real_soak_start
from hg_runtime.real_soak_launch.moltbook_envelope import (
    MoltbookLiveEnvelope,
    arm_envelope,
    create_template_envelope,
    load_envelope_from_file,
    save_envelope,
)
from hg_runtime.real_soak_launch.envelope_validator import validate_moltbook_envelope

__all__ = [
    "MoltbookLiveEnvelope",
    "run_launch_preflight",
    "run_real_soak_start",
    "create_template_envelope",
    "arm_envelope",
    "load_envelope_from_file",
    "save_envelope",
    "validate_moltbook_envelope",
]
