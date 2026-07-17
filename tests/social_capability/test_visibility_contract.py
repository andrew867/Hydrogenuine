"""Publish receipt URL contract tests."""

from __future__ import annotations

from hg_runtime.social_capability.schema import SocialSurface
from hg_runtime.social_capability.visibility_contract import (
    build_visibility_contract,
    visibility_verdict,
)


def test_manual_surface_yellow():
    c = build_visibility_contract(
        surface=SocialSurface.CUSTOM_MANUAL_POST,
        published=True,
        fixture_mode=False,
    )
    assert c["external_visibility_status"] == "manual_surface_no_url"
    assert visibility_verdict(c) == "YELLOW_PLATFORM_URL_UNAVAILABLE"


def test_governance_only_yellow():
    c = build_visibility_contract(
        surface=SocialSurface.MASTODON_LIKE,
        published=True,
        fixture_mode=False,
    )
    assert visibility_verdict(c) == "YELLOW_PLATFORM_URL_UNAVAILABLE"
