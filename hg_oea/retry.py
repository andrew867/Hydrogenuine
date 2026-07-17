"""OEA conservative retry policy."""

from __future__ import annotations

from hg_oea.types import CapabilityDefinition


def may_retry(
    capability: CapabilityDefinition,
    *,
    retry_count: int,
    result_status: str,
) -> bool:
    if result_status == "executed":
        return False
    if capability.retry_policy == "none":
        return False
    if not capability.idempotent:
        return False
    if retry_count >= capability.max_retries:
        return False
    return result_status in {"failed", "timed_out"}


__all__ = ["may_retry"]
