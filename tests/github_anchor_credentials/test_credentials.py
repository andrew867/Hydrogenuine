"""GitHub anchor credential tests."""

from __future__ import annotations

import json

from hg_runtime.external_start_anchor.credentials import (
    CredentialMode,
    assert_no_secret_in_payload,
    redact_secrets,
    resolve_credential_status,
)
from hg_runtime.external_start_anchor.agent0_context import build_agent0_anchor_boot_context
import shutil
import pytest

_requires_gh = pytest.mark.skipif(
    shutil.which("gh") is None,
    reason="requires GitHub CLI (gh); absent in hermetic CI (CCS2 env guard)",
)


def test_token_redacted_in_receipts():
    blob = "error: ghp_abcdefghijklmnopqrstuvwxyz1234567890"
    redacted = redact_secrets(blob)
    assert "ghp_" not in redacted
    assert "[REDACTED" in redacted


@_requires_gh
def test_agent_context_never_includes_token():
    handoff = {
        "anchor_enabled": True,
        "verification_status": "verified",
        "anchor_sequence": 0,
        "boot_bundle_sha256": "abc",
        "public_anchor_sha256": "def",
    }
    ctx = build_agent0_anchor_boot_context(handoff)
    payload = ctx.to_payload()
    assert "token" not in json.dumps(payload).lower() or "env_ref" in json.dumps(payload)
    assert payload["credential_visible_to_agent"] is False


@_requires_gh
def test_credential_status_absent_or_deploy_key():
    status = resolve_credential_status()
    assert status.mode in {
        CredentialMode.ABSENT,
        CredentialMode.GITHUB_CLI,
        CredentialMode.GIT_CLI_EXISTING_AUTH,
        CredentialMode.SSH_DEPLOY_KEY_PRESENT,
        CredentialMode.SSH_KEY_PATH_PRESENT,
    }
    assert status.credential_visible_to_agent is False


def test_assert_no_secret_in_payload():
    try:
        assert_no_secret_in_payload({"note": "ghp_abcdefghijklmnopqrstuvwxyz1234567890"})
        raised = False
    except ValueError:
        raised = True
    assert raised
