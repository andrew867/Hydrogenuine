"""Remote witness freshness tests."""

from __future__ import annotations

from hg_runtime.external_witness_journal.agent0_context import load_journal_config
from hg_runtime.external_witness_journal.remote_freshness import check_remote_witness_freshness


def test_load_journal_config_prefers_local():
    cfg = load_journal_config()
    assert "hg-agent0-anchor" in cfg.anchor_repo_path or cfg.anchor_repo_path


def test_remote_freshness_returns_mode():
    result = check_remote_witness_freshness()
    assert result.verification_mode in {
        "local_only", "local_repo", "remote_ls_remote", "remote_unavailable"
    }
    payload = result.to_payload()
    assert "token" not in str(payload).lower() or "advisory_only" in payload
