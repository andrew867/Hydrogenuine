"""Provider comparison records and smoke verdict determination.

A comparison record captures latency and compatibility quirks across providers for
advice, not authority. The verdict is explicit and partial-aware: a missing OpenVINO
configuration is never hidden behind an LM-Studio-only pass.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.local_provider_smoke.schemas import (
    PROVIDER_COMPARISON_RECORD_SCHEMA,
    VERDICT_GREEN_BOTH,
    VERDICT_GREEN_LMSTUDIO_ONLY,
    VERDICT_RED_FAILED,
    VERDICT_YELLOW_PARTIAL,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
)


def compare_providers(entries: list[Mapping[str, Any]], *, control=None) -> dict[str, Any]:
    """Compare per-provider smoke entries by latency and compatibility quirks."""
    preempt_if_needed(control)
    rows = []
    for entry in entries:
        reject_authority_payload(dict(entry))
        rows.append(
            {
                "provider_id": entry.get("provider_id"),
                "status": entry.get("status"),
                "latency_ms": entry.get("latency_ms"),
                "quirks": list(entry.get("quirks", [])),
            }
        )
    record = {
        "schema": PROVIDER_COMPARISON_RECORD_SCHEMA,
        "providers": rows,
        "advisory_only": True,
        **neutral_flags(),
    }
    record["comparison_hash"] = canonical_hash(record)
    return record


def determine_smoke_verdict(lmstudio_status: str, openvino_status: str) -> str:
    """Map per-provider statuses to an explicit, partial-aware verdict."""
    lm = str(lmstudio_status)
    ov = str(openvino_status)
    if lm == "fail":
        return VERDICT_RED_FAILED
    if ov == "fail":
        # A configured OpenVINO that failed is an honest partial, not a clean pass.
        return VERDICT_YELLOW_PARTIAL
    if lm == "pass" and ov == "pass":
        return VERDICT_GREEN_BOTH
    if lm == "pass" and ov == "not_configured":
        return VERDICT_GREEN_LMSTUDIO_ONLY
    # Dry-run / not-contacted / skipped states: contracts verified, no live provider confirmed.
    return VERDICT_YELLOW_PARTIAL


__all__ = ["compare_providers", "determine_smoke_verdict"]
