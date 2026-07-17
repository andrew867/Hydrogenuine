"""SYN static fixture risk classifier — deterministic, fail-closed."""

from __future__ import annotations

import re
from typing import Mapping

from hg_runtime.synthetic_content_provenance.types import MediaRiskClassification, RiskClass, SyntheticContentArtifact

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"

_IMPERSONATION = re.compile(
    r"\b(official\s+statement|sec\s+filing|white\s+house|federal\s+reserve|"
    r"central\s+bank|government\s+agency|press\s+release\s+from)\b",
    re.IGNORECASE,
)
_DEEPFAKE = re.compile(r"\b(deepfake|face\s+swap|synthetic\s+person\s+media|realistic\s+person)\b", re.IGNORECASE)
_UNDISCLOSED = re.compile(r"\b(passed\s+off\s+as\s+human|not\s+ai|undisclosed\s+generation)\b", re.IGNORECASE)


def classify_fixture(
    artifact: SyntheticContentArtifact,
    *,
    text_hint: str = "",
    observed_at: str | None = None,
) -> MediaRiskClassification:
    """Classify synthetic content risk from static fixture hints only."""
    hint = (text_hint or "").strip()
    risk, rationale, fail_closed = _classify_text(hint, artifact.content_class)
    return MediaRiskClassification(
        artifact_id=artifact.artifact_id,
        risk_class=risk,
        rationale=rationale,
        fail_closed=fail_closed,
        created_at=observed_at or FIXTURE_CLOCK,
    )


def classify_fixture_mapping(fixture: Mapping[str, str], *, observed_at: str | None = None) -> MediaRiskClassification:
    artifact = SyntheticContentArtifact(
        artifact_id=fixture["artifact_id"],
        content_class=fixture.get("content_class", "text"),  # type: ignore[arg-type]
        content_ref=fixture.get("content_ref", f"sha256:{fixture['artifact_id']}"),
        generated=fixture.get("generated", "true").lower() == "true",
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
    )
    return classify_fixture(artifact, text_hint=fixture.get("text_hint", ""), observed_at=observed_at)


def _classify_text(hint: str, content_class: str) -> tuple[RiskClass, str, bool]:
    if not hint.strip():
        return "unknown", "no classification hint", True
    if _IMPERSONATION.search(hint):
        return "public_figure_or_institution_impersonation", "institutional impersonation markers", True
    if _DEEPFAKE.search(hint) or content_class in {"image", "video", "audio", "mixed_media"} and "person" in hint.lower():
        return "deepfake_or_realistic_person_media", "person-media synthetic markers", True
    if _UNDISCLOSED.search(hint):
        return "undisclosed_generation", "undisclosed generation markers", True
    if "misleading" in hint.lower() or "out of context" in hint.lower():
        return "misleading_context", "misleading context markers", False
    if "synthetic voice" in hint.lower():
        return "synthetic_identity_or_voice", "synthetic identity/voice markers", False
    if hint.strip().lower() in {"unknown", "ambiguous", "cannot classify"}:
        return "unknown", "explicit unknown fixture", True
    return "ordinary_generated_content", "ordinary generated content", False


__all__ = ["FIXTURE_CLOCK", "classify_fixture", "classify_fixture_mapping"]
