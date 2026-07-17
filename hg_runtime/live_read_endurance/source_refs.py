"""Endurance-layer source refs from live read items."""

from __future__ import annotations

from typing import Any

from hg_runtime.live_read_endurance.schema import LiveReadFreshnessStatus, LiveReadSourceRef, new_id, now_iso
from hg_runtime.social_capability.live_bridge import LiveReadItem, LiveReadResult


def build_source_refs_from_result(
    result: LiveReadResult,
    *,
    freshness_status: LiveReadFreshnessStatus,
) -> list[LiveReadSourceRef]:
    refs: list[LiveReadSourceRef] = []
    observed = now_iso()
    for item in result.items:
        refs.append(
            LiveReadSourceRef(
                source_ref_id=new_id("src-ref"),
                source_kind=result.surface,
                source_name=result.surface,
                source_item_id=getattr(item, "item_id", None) or getattr(item, "post_id", None),
                source_url=getattr(item, "url", None),
                observed_at=observed,
                freshness_status=freshness_status,
                data_tier=result.data_tier,
            ).with_hash()
        )
    if not refs and result.receipt.source_refs:
        for legacy in result.receipt.source_refs[:20]:
            if isinstance(legacy, dict):
                refs.append(
                    LiveReadSourceRef(
                        source_ref_id=legacy.get("source_ref_id") or new_id("src-ref"),
                        source_kind=legacy.get("source_kind") or result.surface,
                        source_name=legacy.get("source_name") or result.surface,
                        source_item_id=legacy.get("source_item_id"),
                        source_url=legacy.get("source_url"),
                        observed_at=legacy.get("observed_at") or observed,
                        freshness_status=freshness_status,
                        data_tier=result.data_tier,
                    ).with_hash()
                )
            elif isinstance(legacy, str):
                refs.append(
                    LiveReadSourceRef(
                        source_ref_id=legacy,
                        source_kind=result.surface,
                        source_name=result.surface,
                        observed_at=observed,
                        freshness_status=freshness_status,
                        data_tier=result.data_tier,
                    ).with_hash()
                )
    if not refs:
        refs.append(
            LiveReadSourceRef(
                source_ref_id=new_id("src-ref"),
                source_kind=result.surface,
                source_name=result.surface,
                observed_at=observed,
                freshness_status=freshness_status,
                data_tier=result.data_tier,
            ).with_hash()
        )
    return refs


def source_ref_payloads(refs: list[LiveReadSourceRef]) -> list[dict[str, Any]]:
    return [r.to_payload() for r in refs]
