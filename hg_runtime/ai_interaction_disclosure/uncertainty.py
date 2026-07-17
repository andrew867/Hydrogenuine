"""AID uncertainty disclosure — consumes TRL/SAB feeds or discloses absence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from hg_core.policy_safety.errors import REFUSED_HIDE_UNCERTAINTY, PolicyValidationError
from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.policy_safety.no_authority import advisory_only_marker
from hg_runtime.ai_interaction_disclosure.types import AID_SCHEMA_VERSION

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"


@dataclass(frozen=True)
class UncertaintyDisclosure:
    uncertainty_id: str
    interaction_id: str
    uncertainty_summary: str
    known_limitations: tuple[str, ...]
    trl_feed_status: str
    sab_feed_status: str
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "aid-uncertainty-disclosure",
            "schema_version": AID_SCHEMA_VERSION,
            "uncertainty_id": self.uncertainty_id,
            "interaction_id": self.interaction_id,
            "uncertainty_summary": self.uncertainty_summary,
            "known_limitations": list(self.known_limitations),
            "trl_feed_status": self.trl_feed_status,
            "sab_feed_status": self.sab_feed_status,
            "created_at": self.created_at,
            "disclosure_is_not_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class GeneratedContentDisclosure:
    content_disclosure_id: str
    interaction_id: str
    content_generated_status: str
    syn_feed_status: str
    syn_artifact_id: Optional[str]
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "aid-generated-content-disclosure",
            "schema_version": AID_SCHEMA_VERSION,
            "content_disclosure_id": self.content_disclosure_id,
            "interaction_id": self.interaction_id,
            "content_generated_status": self.content_generated_status,
            "syn_feed_status": self.syn_feed_status,
            "syn_artifact_id": self.syn_artifact_id,
            "created_at": self.created_at,
            "disclosure_is_not_permission": True,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def assemble_uncertainty(
    interaction_id: str,
    *,
    trl_feed: Mapping[str, str] | None = None,
    sab_feed: Mapping[str, str] | None = None,
    fixture: Mapping[str, str] | None = None,
    observed_at: str | None = None,
) -> UncertaintyDisclosure:
    if fixture and fixture.get("hide_uncertainty", "").lower() == "true":
        raise PolicyValidationError(REFUSED_HIDE_UNCERTAINTY, "cannot hide uncertainty disclosure")

    trl_status = "present" if trl_feed else "absent"
    sab_status = "present" if sab_feed else "absent"
    summary_parts: list[str] = []
    limitations: list[str] = []

    if trl_feed:
        summary_parts.append(trl_feed.get("uncertainty_summary", "trl_unknowns_present"))
        if trl_feed.get("known_limitations"):
            limitations.extend(trl_feed["known_limitations"].split("|"))
    else:
        summary_parts.append("trl_feed_absent")

    if sab_feed:
        summary_parts.append(sab_feed.get("uncertainty_summary", "sab_unknowns_present"))
        if sab_feed.get("known_limitations"):
            limitations.extend(sab_feed["known_limitations"].split("|"))
    else:
        summary_parts.append("sab_feed_absent")

    if fixture:
        if fixture.get("uncertainty_summary"):
            summary_parts.insert(0, fixture["uncertainty_summary"])
        if fixture.get("known_limitations"):
            limitations.extend(fixture["known_limitations"].split("|"))

    return UncertaintyDisclosure(
        uncertainty_id=f"unc-{interaction_id}",
        interaction_id=interaction_id,
        uncertainty_summary="; ".join(summary_parts),
        known_limitations=tuple(limitations) if limitations else ("feed_absent_or_empty",),
        trl_feed_status=trl_status,
        sab_feed_status=sab_status,
        created_at=observed_at or FIXTURE_CLOCK,
    )


def assemble_generated_content(
    interaction_id: str,
    *,
    syn_feed: Mapping[str, str] | None = None,
    fixture: Mapping[str, str] | None = None,
    observed_at: str | None = None,
) -> GeneratedContentDisclosure:
    syn_status = "present" if syn_feed else "absent"
    if syn_feed:
        content_status = syn_feed.get("content_generated_status", "present")
        artifact_id = syn_feed.get("artifact_id")
    elif fixture:
        content_status = fixture.get("content_generated_status", "none")
        artifact_id = None
    else:
        content_status = "unknown"
        artifact_id = None

    return GeneratedContentDisclosure(
        content_disclosure_id=f"gcd-{interaction_id}",
        interaction_id=interaction_id,
        content_generated_status=content_status,
        syn_feed_status=syn_status,
        syn_artifact_id=artifact_id,
        created_at=observed_at or FIXTURE_CLOCK,
    )


def feed_absence_marker(feed_name: str) -> dict[str, object]:
    return {**advisory_only_marker(), "feed": feed_name, "status": "absent"}


__all__ = [
    "FIXTURE_CLOCK",
    "GeneratedContentDisclosure",
    "UncertaintyDisclosure",
    "assemble_generated_content",
    "assemble_uncertainty",
    "feed_absence_marker",
]
