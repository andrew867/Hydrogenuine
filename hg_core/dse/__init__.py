"""DSE — Durable Side Effect Closure foundation."""

from hg_core.dse.policy import RealSinkPolicy, SinkClass
from hg_core.dse.types import DurableSinkReceipt, SinkAdmissionDecision, SinkRollbackRecord

__all__ = [
    "DurableSinkReceipt",
    "RealSinkPolicy",
    "SinkAdmissionDecision",
    "SinkClass",
    "SinkRollbackRecord",
]
