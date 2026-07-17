"""ORI deterministic fixture deduplicator — duplicates are not consent."""

from __future__ import annotations

from hg_core.ori_cluster.errors import ORI_DEDUPLICATION_APPLIED
from hg_core.ori_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.operator_review_intake.request_types import (
    OperatorReviewRequest,
    ReviewDeduplicationRecord,
)


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def deduplicate_review_requests(
    requests: tuple[OperatorReviewRequest, ...],
) -> dict[str, object]:
    groups: dict[str, list[OperatorReviewRequest]] = {}
    for request in requests:
        groups.setdefault(request.dedupe_key(), []).append(request)

    records: list[ReviewDeduplicationRecord] = []
    canonical_ids: list[str] = []
    suppressed_total = 0

    for dedupe_key, group in sorted(groups.items()):
        sorted_group = sorted(group, key=lambda r: r.review_request_id)
        critical = [r for r in sorted_group if r.is_critical()]
        non_critical = [r for r in sorted_group if not r.is_critical()]

        if len(sorted_group) == 1:
            canonical_ids.append(sorted_group[0].review_request_id)
            continue

        if critical:
            for req in critical:
                canonical_ids.append(req.review_request_id)
            if non_critical:
                canonical = non_critical[0]
                suppressed = tuple(r.review_request_id for r in non_critical[1:])
                if suppressed:
                    records.append(
                        ReviewDeduplicationRecord(
                            dedupe_record_id=_deterministic_id("ori-dedupe", dedupe_key, "nc"),
                            request_refs=tuple(r.review_request_id for r in non_critical),
                            dedupe_key=dedupe_key,
                            dedupe_reason="duplicate_non_critical_within_critical_group",
                            canonical_request_ref=canonical.review_request_id,
                            suppressed_request_refs=suppressed,
                            suppression_visible=True,
                        )
                    )
                    canonical_ids.append(canonical.review_request_id)
                    suppressed_total += len(suppressed)
            continue

        canonical = sorted_group[0]
        suppressed = tuple(r.review_request_id for r in sorted_group[1:])
        records.append(
            ReviewDeduplicationRecord(
                dedupe_record_id=_deterministic_id("ori-dedupe", dedupe_key),
                request_refs=tuple(r.review_request_id for r in sorted_group),
                dedupe_key=dedupe_key,
                dedupe_reason="duplicate_review_request",
                canonical_request_ref=canonical.review_request_id,
                suppressed_request_refs=suppressed,
                suppression_visible=True,
            )
        )
        canonical_ids.append(canonical.review_request_id)
        suppressed_total += len(suppressed)

    canonical_unique = list(dict.fromkeys(canonical_ids))
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": ORI_DEDUPLICATION_APPLIED,
        "canonical_request_refs": canonical_unique,
        "dedupe_records": [r.to_payload() for r in records],
        "suppressed_count": suppressed_total,
        "critical_never_suppressed": all(
            not any(r.is_critical() for r in group if r.review_request_id in rec.suppressed_request_refs)
            for rec in records
            for group in [groups.get(rec.dedupe_key, [])]
        ),
        "review_is_advisory_only": True,
    }


__all__ = ["deduplicate_review_requests"]
