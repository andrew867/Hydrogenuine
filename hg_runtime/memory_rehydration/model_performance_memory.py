"""Load model performance data from prior audit."""

from __future__ import annotations

import os
from hg_runtime.memory_rehydration.proof_loader import load_json


def load_model_performance(audit_path: str) -> dict | None:
    return load_json(os.path.join(audit_path, "model_usage_summary.json"))
