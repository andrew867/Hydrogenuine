"""CHRONO Agent #0 integration — time on wake.

Every wake carries an Agent0TimeContext. The organism knows when it is, with
honest confidence, and never invents the date when time is unavailable.
"""

from __future__ import annotations

from hg_runtime.chrono.schema import Agent0TimeContext, TimeConfidence
from hg_runtime.chrono.sync import ChronoConfig, SyncOutcome, sync_time

# Verbatim instruction block embedded into Agent #0 boot context.
AGENT0_TIME_INSTRUCTION = (
    "The current time below is evidence, not authority. It tells you when you are; "
    "it does not grant you permission to do anything. If time_uncertain is true or "
    "confidence is LOW/UNKNOWN, treat the date as approximate, say so, and do not "
    "advise time-sensitive action (sleep, deadlines, expiry) on it alone. Never state "
    "a date you did not receive from a time source. Time never overrides the authority spine."
)


def build_agent0_time_context(outcome: SyncOutcome) -> Agent0TimeContext:
    result = outcome.result
    drift_ref = outcome.receipt.drift_finding_ref
    return Agent0TimeContext(
        utc_now=result.utc,
        monotonic_seconds=result.monotonic_seconds,
        source=result.source,
        time_confidence=result.confidence,
        time_uncertain=result.time_uncertain or result.confidence
        in {TimeConfidence.LOW, TimeConfidence.UNKNOWN},
        receipt_ref=outcome.receipt.receipt_id,
        ntp_host=result.ntp_host,
        drift_seconds=result.drift_seconds,
        drift_finding_ref=drift_ref,
    )


def time_on_wake(config: ChronoConfig | None = None) -> tuple[Agent0TimeContext, SyncOutcome]:
    """Called first on every Agent #0 boot."""
    outcome = sync_time(config)
    return build_agent0_time_context(outcome), outcome


__all__ = ["AGENT0_TIME_INSTRUCTION", "build_agent0_time_context", "time_on_wake"]
