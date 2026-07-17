"""GitHub journal backend — append-only witness writes."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from hg_runtime.external_start_anchor.github_git_backend import (
    AnchorRepoDirty,
    GitHistoryRewriteAttempted,
    _ensure_repo,
    _run_git,
)
from hg_runtime.external_witness_journal.event_bundle import journal_event_txt
from hg_runtime.external_witness_journal.hash_chain import hash_journal_event, read_chain, write_chain
from hg_runtime.external_witness_journal.receipts import AnchorWriterReceipt, new_id
from hg_runtime.external_witness_journal.schema import WitnessAppendDecision, WitnessHashChain, WitnessJournalBundle, WitnessJournalConfig


@dataclass
class JournalBackendResult:
    dry_run: bool
    pushed: bool
    commit_sha: str | None
    event_paths: dict[str, str]
    receipt: AnchorWriterReceipt
    detail: str = ""


def _event_filename(bundle: WitnessJournalBundle) -> str:
    return f"event-{bundle.event_sequence:06d}-{bundle.event_class.value}.json"


def write_journal_files(
    repo: Path,
    cfg: WitnessJournalConfig,
    bundle: WitnessJournalBundle,
    *,
    event_payload: dict | None = None,
) -> dict[str, str]:
    journal_dir = repo / cfg.journal_dir
    events_dir = repo / cfg.events_dir
    journal_dir.mkdir(parents=True, exist_ok=True)
    events_dir.mkdir(parents=True, exist_ok=True)

    event_name = _event_filename(bundle)
    event_json = events_dir / event_name
    event_txt = events_dir / event_name.replace(".json", ".txt")
    latest_json = repo / cfg.latest_file
    latest_txt = journal_dir / "latest.txt"

    payload = json.dumps(event_payload or bundle.to_dict(include_hash=True), indent=2, sort_keys=True) + "\n"
    event_json.write_text(payload, encoding="utf-8")
    event_txt.write_text(journal_event_txt(bundle), encoding="utf-8")
    latest_json.write_text(payload, encoding="utf-8")
    latest_txt.write_text(journal_event_txt(bundle), encoding="utf-8")

    chain = read_chain(repo, cfg.chain_file)
    chain.latest_event_sequence = bundle.event_sequence
    chain.latest_event_sha256 = bundle.journal_event_sha256
    sig_block = (event_payload or {}).get("journal_signature") or {}
    if sig_block:
        from hg_runtime.external_witness_journal.init_delta import sha256_sig

        chain.latest_signature_sha256 = sha256_sig(sig_block)
        chain.latest_signer_key_id = sig_block.get("signer_key_id")
    chain.event_count = bundle.event_sequence + 1
    chain.chain_verified = True
    write_chain(repo, cfg.chain_file, chain)

    readme = repo / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Hydrogenuine Agent Zero GitHub Witness Anchor\n\n"
            "Public continuity evidence only. Not authority. Not memory. Not consent.\n",
            encoding="utf-8",
        )

    return {
        "event_json": str(event_json.relative_to(repo)),
        "event_txt": str(event_txt.relative_to(repo)),
        "latest_json": str(latest_json.relative_to(repo)),
        "chain_json": str((repo / cfg.chain_file).relative_to(repo)),
    }


class GitHubJournalBackend:
    def __init__(self, cfg: WitnessJournalConfig, *, workspace: Path | None = None) -> None:
        self.cfg = cfg
        self.workspace = workspace or Path.cwd()

    def next_sequence(self) -> int:
        repo = self.cfg.resolved_repo_path(self.workspace)
        local_chain = self.workspace / ".hg-local" / "external_witness_journal" / "chain_local.json"
        if local_chain.exists():
            data = json.loads(local_chain.read_text(encoding="utf-8"))
            return int(data.get("latest_event_sequence", -1)) + 1
        if repo.exists() and (repo / self.cfg.chain_file).exists():
            chain = read_chain(repo, self.cfg.chain_file)
            return chain.latest_event_sequence + 1
        return 0

    def _update_local_chain(self, bundle: WitnessJournalBundle, commit_sha: str | None, event_payload: dict | None = None) -> None:
        local = self.workspace / ".hg-local" / "external_witness_journal"
        local.mkdir(parents=True, exist_ok=True)
        sig_block = (event_payload or {}).get("journal_signature") or {}
        latest_sig = None
        if sig_block:
            from hg_runtime.external_witness_journal.init_delta import sha256_sig

            latest_sig = sha256_sig(sig_block)
        chain = WitnessHashChain(
            latest_event_sequence=bundle.event_sequence,
            latest_event_sha256=bundle.journal_event_sha256,
            latest_signature_sha256=latest_sig,
            latest_signer_key_id=sig_block.get("signer_key_id"),
            latest_github_commit_sha=commit_sha,
            event_count=bundle.event_sequence + 1,
            chain_verified=bool(sig_block),
        )
        (local / "chain_local.json").write_text(json.dumps(chain.to_dict(), indent=2), encoding="utf-8")
        (local / "latest_event.json").write_text(
            json.dumps(event_payload or bundle.to_dict(include_hash=True), indent=2) + "\n",
            encoding="utf-8",
        )

    def prepare_repo(self) -> Path:
        # Reuse anchor repo ensure logic via a minimal config adapter
        from hg_runtime.external_start_anchor.schema import GitHubAnchorConfig

        anchor_cfg = GitHubAnchorConfig(
            anchor_repo_path=self.cfg.anchor_repo_path,
            anchor_repo_remote=self.cfg.anchor_repo_remote,
            anchor_branch=self.cfg.anchor_branch,
            allow_create_repo=self.cfg.allow_create_repo,
            require_clean_anchor_repo=self.cfg.require_clean_anchor_repo,
        )
        anchor_cfg._apply_env()
        repo = _ensure_repo(anchor_cfg, self.workspace)
        if self.cfg.anchor_repo_remote:
            remotes = _run_git(["remote", "-v"], repo, check=False)
            if self.cfg.anchor_repo_remote not in (remotes.stdout or ""):
                if "origin" not in (remotes.stdout or ""):
                    _run_git(["remote", "add", "origin", self.cfg.anchor_repo_remote], repo)
            _run_git(["fetch", "origin"], repo, check=False)
        if self.cfg.require_clean_anchor_repo:
            status = _run_git(["status", "--porcelain"], repo, check=False)
            if status.stdout.strip():
                raise AnchorRepoDirty(f"anchor repo dirty: {status.stdout.strip()[:200]}")
        return repo

    def append(
        self,
        bundle: WitnessJournalBundle,
        *,
        event_payload: dict | None = None,
        dry_run: bool = True,
        push: bool = False,
        run_id: str = "",
    ) -> JournalBackendResult:
        cfg = self.cfg
        allow_push = push and cfg.allow_push and not dry_run
        receipt = AnchorWriterReceipt(
            receipt_id=new_id("awr"),
            run_id=run_id or new_id("run"),
            event_class=bundle.event_class.value,
            event_sequence=bundle.event_sequence,
            journal_event_sha256=bundle.journal_event_sha256,
            decision=WitnessAppendDecision.ALLOW_LOCAL_ONLY,
            pushed=False,
            dry_run=dry_run or not allow_push,
        )

        if dry_run:
            local = self.workspace / ".hg-local" / "external_witness_journal" / "dry_run_repo"
            if local.exists():
                shutil.rmtree(local)
            local.mkdir(parents=True, exist_ok=True)
            _run_git(["init", "-b", cfg.anchor_branch], local)
            paths = write_journal_files(local, cfg, bundle, event_payload=event_payload)
            self._update_local_chain(bundle, None, event_payload=event_payload)
            receipt.dry_run = True
            return JournalBackendResult(
                dry_run=True,
                pushed=False,
                commit_sha=None,
                event_paths=paths,
                receipt=receipt,
                detail="dry-run sandbox only",
            )

        repo = self.prepare_repo()
        paths = write_journal_files(repo, cfg, bundle, event_payload=event_payload)
        from hg_runtime.external_start_anchor.credentials import git_subprocess_env

        git_env = git_subprocess_env()
        journal_rel = cfg.journal_dir
        _run_git(["add", "README.md", journal_rel], repo, env=git_env)
        short = bundle.journal_event_sha256[:12]
        msg = f"journal(agent0): {bundle.event_class.value} seq {bundle.event_sequence} {short}"
        _run_git(["commit", "-m", msg], repo, env=git_env)
        head = _run_git(["rev-parse", "HEAD"], repo, env=git_env).stdout.strip()
        bundle.github_commit_sha = head
        receipt.github_commit_sha = head
        receipt.dry_run = False

        if not allow_push:
            self._update_local_chain(bundle, head, event_payload=event_payload)
            return JournalBackendResult(
                dry_run=False,
                pushed=False,
                commit_sha=head,
                event_paths=paths,
                receipt=receipt,
                detail="local repo commit without remote push",
            )

        receipt.pushed = True
        _run_git(["push", "-u", "origin", cfg.anchor_branch], repo, env=git_env)
        self._update_local_chain(bundle, head, event_payload=event_payload)
        return JournalBackendResult(
            dry_run=False,
            pushed=True,
            commit_sha=head,
            event_paths=paths,
            receipt=receipt,
            detail="pushed",
        )


__all__ = [
    "GitHistoryRewriteAttempted",
    "GitHubJournalBackend",
    "JournalBackendResult",
    "write_journal_files",
]
