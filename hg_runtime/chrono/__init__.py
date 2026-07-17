"""CHRONO — trustworthy-enough time for Agent #0.

Time receipts are evidence, not authority. The clock never grants permission,
and the organism never invents the date.
"""

from hg_runtime.chrono.epoch import BootEpoch, EpochConfidence, compute_epoch_lock_id
from hg_runtime.chrono.lock import ChronoLock, create_chrono_lock
from hg_runtime.chrono.schema import (
    CHRONO_SCHEMA_VERSION,
    Agent0TimeContext,
    ClockDriftFinding,
    DriftKind,
    TimeConfidence,
    TimeSource,
    TimeSyncResult,
)

__all__ = [
    "CHRONO_SCHEMA_VERSION",
    "Agent0TimeContext",
    "BootEpoch",
    "ChronoLock",
    "ClockDriftFinding",
    "DriftKind",
    "EpochConfidence",
    "TimeConfidence",
    "TimeSource",
    "TimeSyncResult",
    "compute_epoch_lock_id",
    "create_chrono_lock",
]
