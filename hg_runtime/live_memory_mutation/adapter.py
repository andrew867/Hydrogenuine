"""MEM-LIVE runtime adapter — fake sink only; no durable writes."""

from __future__ import annotations

from typing import Any

from hg_core.mem_live.config import mem_fake_sink_only, mem_refuse_durable_writes
from hg_core.mem_live.errors import MEM_COMMIT_FAKE_SINK, REFUSED_DURABLE_WRITE
from hg_core.mem_live.no_authority import advisory_only_marker
from hg_runtime.live_memory_mutation.types import FIXTURE_CLOCK, MemoryMutationReceipt, MemoryWriteCandidate


def request_to_fake_sink(
    candidate: MemoryWriteCandidate,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Stage memory write candidate in fake sink; never performs durable write."""
    if not mem_fake_sink_only():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "mem.refused.fake_sink_disabled",
            "durable_write_performed": False,
        }

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "mem.advisory.request_staged",
        "sink_type": "fake",
        "candidate_ref": candidate.candidate_id,
        "mutation_kind": candidate.mutation_kind,
        "durable_write_performed": False,
        "live_action_performed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


def commit_to_fake_sink(
    receipt: MemoryMutationReceipt,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, Any]:
    """Commit memory mutation receipt to fake sink; never performs durable write."""
    if not mem_refuse_durable_writes():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_DURABLE_WRITE,
            "durable_write_performed": False,
        }

    if not mem_fake_sink_only():
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "mem.refused.fake_sink_disabled",
            "durable_write_performed": False,
        }

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": MEM_COMMIT_FAKE_SINK,
        "sink_type": "fake",
        "receipt_ref": receipt.receipt_id,
        "mutation_kind": receipt.mutation_kind,
        "durable_write_performed": False,
        "live_action_performed": False,
        "permission_granted": False,
        "observed_at": observed_at,
    }


__all__ = ["commit_to_fake_sink", "request_to_fake_sink"]
