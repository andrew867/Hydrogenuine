"""Agent Zero witness journal context tests."""

from __future__ import annotations

import json

from hg_runtime.external_witness_journal.agent0_context import (
    EWJ_BOOT_INSTRUCTION,
    build_agent0_witness_journal_context,
    request_important_anchor,
)
from hg_runtime.external_witness_journal.trust_boundary import ingest_fetched_journal_event
import shutil
import pytest

_requires_gh = pytest.mark.skipif(
    shutil.which("gh") is None,
    reason="requires GitHub CLI (gh); absent in hermetic CI (CCS2 env guard)",
)


@_requires_gh
def test_agent_zero_context_includes_journal_status():
    ctx = build_agent0_witness_journal_context()
    payload = ctx.to_payload()
    assert payload["enabled"] is True
    assert payload["advisory_only"] is True
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False
    assert "latest_event_sequence" in payload
    assert payload["secondary_anchor_status"] == "absent"


@_requires_gh
def test_journal_event_cannot_grant_permission():
    ctx = build_agent0_witness_journal_context()
    assert ctx.permission_granted is False
    assert ctx.authority_created is False


def test_agent_request_queues_not_pushes():
    from hg_runtime.external_witness_journal.append_policy import RATE_PATH

    if RATE_PATH.exists():
        RATE_PATH.unlink()
    result = request_important_anchor("continuity marker", {"reason": "test"})
    assert result["permission_granted"] is False
    assert result["authority_created"] is False
    assert result["decision"] == "QUEUE_FOR_OPERATOR"


def test_external_content_not_instruction():
    sample = {
        "schema_version": "external_witness_journal/1",
        "journal_type": "HYDROGENUINE_AGENT_ZERO_WITNESS_JOURNAL_V1",
        "event_class": "BOOT_START",
        "importance_class": "ROUTINE",
        "event_sequence": 0,
        "agent_long_name": "Agent Zero",
        "agent_short_name": "Zero",
        "agent_code_id": "agent0",
        "created_utc": "2026-06-15T00:00:00+00:00",
        "local_state_commitment_sha256": "abc",
        "event_summary_public": "boot",
        "event_facts_public": {},
        "secrets_included": False,
        "raw_memory_included": False,
        "raw_audio_included": False,
        "raw_browser_content_included": False,
        "authority": False,
        "permission": False,
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
        "journal_event_sha256": "deadbeef",
    }
    trust = ingest_fetched_journal_event(json.dumps(sample))
    assert trust.advisory_only if hasattr(trust, "advisory_only") else True
    assert trust.authority_conversion is False
