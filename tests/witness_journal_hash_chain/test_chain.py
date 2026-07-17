"""Witness journal hash chain tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from hg_runtime.external_witness_journal.event_bundle import build_event_bundle
from hg_runtime.external_witness_journal.github_journal_backend import GitHubJournalBackend, write_journal_files
from hg_runtime.external_witness_journal.hash_chain import hash_journal_event, verify_chain
from hg_runtime.external_witness_journal.schema import WitnessEventClass, WitnessImportanceClass, WitnessJournalConfig


@pytest.fixture
def journal_repo(tmp_path: Path):
    repo = tmp_path / "anchor-repo"
    repo.mkdir()
    return repo


def _bundle(seq: int, prev: str | None = None):
    cfg = WitnessJournalConfig()
    bundle, payload = build_event_bundle(
        cfg,
        event_class=WitnessEventClass.BOOT_START if seq == 0 else WitnessEventClass.MISSION_START,
        importance=WitnessImportanceClass.ROUTINE,
        event_sequence=seq,
        summary=f"event {seq}",
        previous_event_sha256=prev,
        created_utc=f"2026-06-15T00:00:{seq:02d}+00:00",
        sign=True,
    )
    return bundle, payload


def test_hash_chain_verifies(journal_repo: Path):
    cfg = WitnessJournalConfig()
    b0, p0 = _bundle(0)
    write_journal_files(journal_repo, cfg, b0, event_payload=p0)
    b1, p1 = _bundle(1, b0.journal_event_sha256)
    write_journal_files(journal_repo, cfg, b1, event_payload=p1)
    v = verify_chain(journal_repo, events_dir=cfg.events_dir, chain_file=cfg.chain_file)
    assert v.ok
    assert v.event_count == 2
    assert v.latest_sequence == 1


def test_chain_break_detected(journal_repo: Path):
    cfg = WitnessJournalConfig()
    b0, p0 = _bundle(0)
    write_journal_files(journal_repo, cfg, b0, event_payload=p0)
    b1, p1 = _bundle(1, "wrong-prev-hash")
    write_journal_files(journal_repo, cfg, b1, event_payload=p1)
    v = verify_chain(journal_repo, events_dir=cfg.events_dir, chain_file=cfg.chain_file)
    assert not v.ok
    assert any("BROKEN" in f for f in v.failures)


def test_history_rewrite_detected(journal_repo: Path):
    cfg = WitnessJournalConfig()
    b0, p0 = _bundle(0)
    write_journal_files(journal_repo, cfg, b0, event_payload=p0)
    chain_path = journal_repo / cfg.chain_file
    chain = json.loads(chain_path.read_text(encoding="utf-8"))
    chain["latest_event_sha256"] = "0" * 64
    chain_path.write_text(json.dumps(chain), encoding="utf-8")
    v = verify_chain(journal_repo, events_dir=cfg.events_dir, chain_file=cfg.chain_file)
    assert not v.ok
    assert any("REWRITE" in f for f in v.failures)


def test_force_push_blocked(tmp_path: Path):
    cfg = WitnessJournalConfig(anchor_repo_path=str(tmp_path / "repo"), allow_push=True)
    backend = GitHubJournalBackend(cfg, workspace=tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    import subprocess

    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    bundle = _bundle(0)
    from hg_runtime.external_start_anchor.github_git_backend import GitHistoryRewriteAttempted, _run_git

    with pytest.raises(GitHistoryRewriteAttempted):
        _run_git(["push", "--force", "origin", "main"], repo, check=False)
