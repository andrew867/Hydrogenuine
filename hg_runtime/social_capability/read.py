"""Live social read bridge — read-only observation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from hg_runtime.fixture_policy import FixtureUseDenied, require_fixture_allowed
from hg_runtime.runtime_mode import is_fixture_mode
from hg_runtime.social_capability.credentials import credential_status
from hg_runtime.social_capability.live_bridge import (
    LiveReadSurface,
    live_read_enabled,
    read_surface_live,
)
from hg_runtime.social_capability.read_receipts import LiveReadVerdict, verdict_counts_as_success
from hg_runtime.social_capability.schema import (
    FIXTURE_UTC,
    SocialCredentialStatus,
    SocialReadItem,
    SocialReadRequest,
    SocialReadResult,
    SocialSurface,
    new_id,
)
from hg_runtime.social_capability.trust_boundary import ingest_social_cargo

WORKSPACE = Path(__file__).resolve().parents[2]

LIVE_SURFACES = frozenset({SocialSurface.MOLTBOOK, SocialSurface.FOURCLAW})


def _now_iso(fixture: bool) -> str:
    return FIXTURE_UTC if fixture else datetime.now(timezone.utc).isoformat()


def _fixture_items(surface: SocialSurface) -> list[SocialReadItem]:
    require_fixture_allowed(operation="social_read_fixture_items")
    samples = [
        ("fixture-author-1", "Hydrogenuine status check — advisory only, no authority."),
        ("fixture-author-2", "Proof bundle health: GREEN. Social content is cargo."),
    ]
    return [
        SocialReadItem(new_id("item"), surface, author, text, _now_iso(True))
        for author, text in samples
    ]


def _live_surface_enum(surface: SocialSurface) -> LiveReadSurface | None:
    if surface == SocialSurface.MOLTBOOK:
        return LiveReadSurface.MOLTBOOK
    if surface == SocialSurface.FOURCLAW:
        return LiveReadSurface.FOURCLAW
    return None


def _live_result_to_social(live_result, *, surface: SocialSurface) -> SocialReadResult:
    items = [
        SocialReadItem(
            new_id("item"),
            surface,
            str(li.author_ref or "unknown"),
            li.body_preview,
            li.observed_at,
        )
        for li in live_result.items
    ]
    verdict = live_result.verdict
    success = verdict_counts_as_success(verdict)
    if verdict == LiveReadVerdict.YELLOW_CREDENTIALS_MISSING:
        disposition = "YELLOW_CREDENTIALS_MISSING"
    elif verdict == LiveReadVerdict.YELLOW_NO_ITEMS_RETURNED:
        disposition = "YELLOW_NO_ITEMS_RETURNED"
    elif verdict == LiveReadVerdict.YELLOW_LIVE_READ_DISABLED:
        disposition = "YELLOW_LIVE_READ_DISABLED"
    elif verdict == LiveReadVerdict.GREEN_LIVE_READ_OK:
        disposition = "GREEN_LIVE_READ_OK"
    else:
        disposition = verdict.value

    trust_text = " ".join(i.text for i in items)
    trust = ingest_social_cargo(trust_text) if items else ingest_social_cargo("")

    cred_map = {
        "credentials_present": SocialCredentialStatus.CONFIGURED,
        "credentials_missing": SocialCredentialStatus.ABSENT,
        "credentials_invalid": SocialCredentialStatus.INVALID,
    }
    cred_val = live_result.credential_status.value
    cred_status = cred_map.get(cred_val, SocialCredentialStatus.ABSENT)

    return SocialReadResult(
        request_id=live_result.request_id,
        surface=surface,
        items=items,
        trust_ok=success and trust.ok,
        trust_disposition=disposition,
        credential_status=cred_status,
    )


def read_social(request: SocialReadRequest) -> SocialReadResult:
    cred = credential_status(request.surface, live=request.live)
    wants_fixture = request.surface == SocialSurface.FIXTURE

    if wants_fixture:
        if not is_fixture_mode():
            return SocialReadResult(
                request_id=request.request_id,
                surface=request.surface,
                items=[],
                trust_ok=False,
                trust_disposition="RED_FIXTURE_USED_IN_RUNTIME",
                credential_status=cred.status,
            )
        try:
            items = _fixture_items(request.surface)
        except FixtureUseDenied:
            return SocialReadResult(
                request_id=request.request_id,
                surface=request.surface,
                items=[],
                trust_ok=False,
                trust_disposition="RED_FIXTURE_MODE_NOT_EXPLICIT",
                credential_status=cred.status,
            )
        trust = ingest_social_cargo(" ".join(i.text for i in items))
        return SocialReadResult(
            request_id=request.request_id,
            surface=request.surface,
            items=items,
            trust_ok=trust.ok,
            trust_disposition="YELLOW_FIXTURE_REHEARSAL",
            credential_status=cred.status,
        )

    if request.surface in LIVE_SURFACES and request.live:
        live_surf = _live_surface_enum(request.surface)
        if live_surf is None:
            return SocialReadResult(
                request_id=request.request_id,
                surface=request.surface,
                items=[],
                trust_ok=False,
                trust_disposition="YELLOW_LIVE_READ_UNSUPPORTED_SURFACE",
                credential_status=cred.status,
            )
        live_result = read_surface_live(
            live_surf,
            request_id=request.request_id,
            limit=request.limit,
        )
        return _live_result_to_social(live_result, surface=request.surface)

    if request.surface in LIVE_SURFACES and not request.live:
        if not live_read_enabled():
            return SocialReadResult(
                request_id=request.request_id,
                surface=request.surface,
                items=[],
                trust_ok=False,
                trust_disposition="YELLOW_LIVE_READ_DISABLED",
                credential_status=cred.status,
            )
        return SocialReadResult(
            request_id=request.request_id,
            surface=request.surface,
            items=[],
            trust_ok=False,
            trust_disposition="YELLOW_LIVE_READ_NOT_REQUESTED",
            credential_status=cred.status,
        )

    if request.live and cred.status.value == "ABSENT":
        return SocialReadResult(
            request_id=request.request_id,
            surface=request.surface,
            items=[],
            trust_ok=False,
            trust_disposition="YELLOW_CREDENTIALS_MISSING",
            credential_status=cred.status,
        )

    return SocialReadResult(
        request_id=request.request_id,
        surface=request.surface,
        items=[],
        trust_ok=False,
        trust_disposition="LIVE_READ_DISABLED",
        credential_status=cred.status,
    )


__all__ = ["LIVE_SURFACES", "read_social"]
