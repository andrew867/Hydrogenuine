"""
Determinism envelope: seed from (task_id, date) when randomness is allowed.

So retries with the same task and date produce the same random choices.
See token_optimization_and_autonomy_plumbing plan a2.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone


def get_date_bucket() -> str:
    """UTC date bucket YYYY-MM-DD."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_run_seed(task_id: str, date_bucket: str) -> int:
    """
    Return a deterministic integer seed from (task_id, date_bucket).
    Use for random.seed(...) at the start of a task run so retries behave.
    """
    raw = f"{task_id}:{date_bucket}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return int(h[:12], 16)  # 48 bits, fits in int


def set_run_seed_if_desired(task_id: str, date_bucket: str | None = None) -> int:
    """
    Call random.seed(get_run_seed(task_id, date_bucket)) and return the seed.
    Use at task entry when randomness is allowed. If date_bucket is None, use today UTC.
    """
    import random
    if date_bucket is None:
        date_bucket = get_date_bucket()
    seed = get_run_seed(task_id, date_bucket)
    random.seed(seed)
    return seed
