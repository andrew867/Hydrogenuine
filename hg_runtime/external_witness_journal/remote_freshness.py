"""Remote witness freshness — compare local journal state to git remote."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.external_witness_journal.agent0_context import load_journal_config
from hg_runtime.external_witness_journal.hash_chain import read_chain

WORKSPACE = Path(__file__).resolve().parents[2]
LOCAL_CHAIN = WORKSPACE / ".hg-local" / "external_witness_journal" / "chain_local.json"


@dataclass
class RemoteWitnessFreshness:
    verification_mode: str  # local_only | local_repo | remote_ls_remote | remote_unavailable
    local_chain_sequence: int | None
    local_repo_sequence: int | None
    local_repo_head: str | None
    remote_head: str | None
    remote_available: bool
    remote_contains_local_head: bool | None
    sequence_gap: int | None
    stale: bool
    verdict: str
    detail: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "verification_mode": self.verification_mode,
            "local_chain_sequence": self.local_chain_sequence,
            "local_repo_sequence": self.local_repo_sequence,
            "local_repo_head": self.local_repo_head,
            "remote_head": self.remote_head,
            "remote_available": self.remote_available,
            "remote_contains_local_head": self.remote_contains_local_head,
            "sequence_gap": self.sequence_gap,
            "stale": self.stale,
            "verdict": self.verdict,
            "detail": self.detail,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


def _read_local_chain_sequence() -> int | None:
    if not LOCAL_CHAIN.is_file():
        return None
    import json

    data = json.loads(LOCAL_CHAIN.read_text(encoding="utf-8"))
    seq = data.get("latest_event_sequence")
    return int(seq) if seq is not None else None


def check_remote_witness_freshness(
    *,
    workspace: Path | None = None,
    config_path: str | Path | None = None,
) -> RemoteWitnessFreshness:
    ws = workspace or WORKSPACE
    cfg = load_journal_config(config_path)
    repo = cfg.resolved_repo_path(ws)
    local_seq = _read_local_chain_sequence()
    repo_seq: int | None = None
    repo_head: str | None = None
    if repo.is_dir() and (repo / cfg.chain_file).is_file():
        chain = read_chain(repo, cfg.chain_file)
        repo_seq = chain.latest_event_sequence
        head = _git(repo, "rev-parse", "HEAD")
        if head.returncode == 0:
            repo_head = head.stdout.strip()

    gap = None
    if local_seq is not None and repo_seq is not None:
        gap = local_seq - repo_seq

    remote_head: str | None = None
    remote_ok = False
    remote_contains: bool | None = None
    mode = "local_only"

    if repo.is_dir() and (repo / ".git").is_dir():
        mode = "local_repo"
        remote = cfg.anchor_repo_remote
        if remote and not remote.startswith(("http", "git@", "ssh://")):
            remote = f"git@github.com:{remote}.git"
        if remote:
            from hg_runtime.external_start_anchor.credentials import git_subprocess_env

            git_env = git_subprocess_env()
            ls = _git(repo, "ls-remote", remote, f"refs/heads/{cfg.anchor_branch}", env=git_env)
            if ls.returncode == 0 and ls.stdout.strip():
                remote_ok = True
                mode = "remote_ls_remote"
                remote_head = ls.stdout.strip().split()[0]
                if repo_head:
                    remote_contains = repo_head == remote_head or remote_head.startswith(repo_head[:7])
            else:
                mode = "remote_unavailable"

    stale = False
    verdict = "GREEN_REMOTE_WITNESS_FRESH"
    detail = "local and remote aligned or remote not checked"

    if gap is not None and gap > 0:
        stale = True
        verdict = "RED_REMOTE_ANCHOR_STALE"
        detail = f"local chain seq {local_seq} ahead of anchor repo seq {repo_seq} by {gap}"
    elif repo_head and remote_head and repo_head != remote_head:
        stale = True
        verdict = "RED_REMOTE_ANCHOR_NOT_PUSHED"
        detail = "local repo HEAD differs from remote branch HEAD"
    elif not remote_ok and cfg.allow_push:
        verdict = "YELLOW_REMOTE_NETWORK_UNAVAILABLE"
        detail = "remote ls-remote unavailable; local state only"
        mode = "remote_unavailable"

    return RemoteWitnessFreshness(
        verification_mode=mode,
        local_chain_sequence=local_seq,
        local_repo_sequence=repo_seq,
        local_repo_head=repo_head,
        remote_head=remote_head,
        remote_available=remote_ok,
        remote_contains_local_head=remote_contains,
        sequence_gap=gap,
        stale=stale,
        verdict=verdict,
        detail=detail,
    )


__all__ = ["RemoteWitnessFreshness", "check_remote_witness_freshness"]
