"""Deterministic Phase 41 review queue fixtures."""

from __future__ import annotations

from hg_runtime.patch_candidate_sandbox.fixtures import all_fixtures


def candidate_fixtures() -> list[dict]:
    by_name = {item["name"]: item for item in all_fixtures()}
    return [
        {"fixture_id": "SAFE_DOC_PATCH_CANDIDATE", **by_name["READY_DOC_ONLY_PATCH"]},
        {"fixture_id": "SAFE_TEST_PATCH_CANDIDATE", **by_name["READY_TEST_ONLY_PATCH"]},
        {"fixture_id": "RUNTIME_PATCH_NEEDS_REVIEW", **by_name["RUNTIME_LOW_PATCH"]},
        {"fixture_id": "UNSAFE_AUTHORITY_PATCH", **by_name["AUTHORITY_BYPASS_PATCH"]},
        {"fixture_id": "LIVE_EFFECT_PATCH", **by_name["LIVE_EFFECT_PATCH"]},
    ]
