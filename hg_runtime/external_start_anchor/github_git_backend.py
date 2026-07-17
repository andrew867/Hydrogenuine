"""GitHub git backend — operator-run local git CLI witness writes."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.external_start_anchor.public_anchor import public_anchor_txt
from hg_runtime.external_start_anchor.receipts import ExternalStartAnchorReceipt, new_id
from hg_runtime.external_start_anchor.schema import AnchorBackendStatus, GitHubAnchorCommit, GitHubAnchorConfig, PublicAnchorBundle


class GitHistoryRewriteAttempted(Exception):
    code = "RED_GITHUB_HISTORY_REWRITE_ATTEMPTED"


class AnchorRepoDirty(Exception):
    pass


@dataclass
class GitBackendResult:
    status: AnchorBackendStatus
    dry_run: bool
    pushed: bool
    commit: GitHubAnchorCommit | None
    anchor_paths: dict[str, str]
    receipt: ExternalStartAnchorReceipt
    detail: str = ""


def _run_git(args: list[str], cwd: Path, *, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    if any(a in args for a in ("--force", "-f")) and "push" in args:
        raise GitHistoryRewriteAttempted("force push not permitted")
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False, env=env)
    if check and result.returncode != 0:
        from hg_runtime.external_start_anchor.credentials import redact_secrets
        raise RuntimeError(redact_secrets(result.stderr.strip() or result.stdout.strip() or f"git failed: {args}"))
    return result


def _ensure_repo(cfg: GitHubAnchorConfig, workspace: Path) -> Path:
    repo = cfg.resolved_repo_path(workspace)
    if repo.exists() and (repo / ".git").exists():
        return repo
    if not cfg.allow_create_repo:
        raise FileNotFoundError(f"anchor repo missing: {repo}")
    repo.parent.mkdir(parents=True, exist_ok=True)
    _run_git(["init", "-b", cfg.anchor_branch], repo.parent if repo.name == ".git" else repo)
    if not (repo / ".git").exists() and repo.name != ".git":
        _run_git(["init", "-b", cfg.anchor_branch], repo)
    return repo


def _read_latest_sequence(repo: Path, cfg: GitHubAnchorConfig) -> tuple[int, str | None]:
    latest = repo / cfg.sequence_file
    if not latest.exists():
        return -1, None
    data = json.loads(latest.read_text(encoding="utf-8"))
    return int(data.get("anchor_sequence", -1)), data.get("boot_bundle_sha256")


def write_anchor_files(
    repo: Path,
    cfg: GitHubAnchorConfig,
    public: PublicAnchorBundle,
    *,
    payload_override: dict | None = None,
) -> dict[str, str]:
    public_dir = repo / cfg.anchor_public_dir
    history_dir = repo / cfg.history_dir
    public_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)
    seq = public.anchor_sequence
    seq_name = f"sequence-{seq:06d}"
    paths = {
        "latest_json": str((repo / cfg.sequence_file).relative_to(repo)),
        "latest_txt": str((public_dir / "latest.txt").relative_to(repo)),
        "history_json": str((history_dir / f"{seq_name}.json").relative_to(repo)),
        "history_txt": str((history_dir / f"{seq_name}.txt").relative_to(repo)),
    }
    latest_json = repo / paths["latest_json"]
    latest_txt = repo / paths["latest_txt"]
    history_json = repo / paths["history_json"]
    history_txt = repo / paths["history_txt"]
    payload_dict = payload_override if payload_override is not None else public.to_dict()
    payload = json.dumps(payload_dict, indent=2, sort_keys=True) + "\n"
    txt = public_anchor_txt(public)
    for path in (latest_json, history_json):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
    for path in (latest_txt, history_txt):
        path.write_text(txt, encoding="utf-8")
    readme = repo / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Hydrogenuine Agent Zero GitHub Witness Anchor\n\n"
            "Public continuity evidence only. Not authority. Not memory. Not consent.\n",
            encoding="utf-8",
        )
    return paths


class GitHubGitBackend:
    def __init__(self, cfg: GitHubAnchorConfig, *, workspace: Path | None = None) -> None:
        self.cfg = cfg
        self.workspace = workspace or Path.cwd()

    def next_sequence(self, explicit: int | str | None) -> int:
        repo = self.cfg.resolved_repo_path(self.workspace)
        if explicit not in (None, "auto", ""):
            return int(explicit)
        if not repo.exists():
            return 0
        latest_seq, _ = _read_latest_sequence(repo, self.cfg)
        return latest_seq + 1

    def prepare_repo(self) -> Path:
        repo = _ensure_repo(self.cfg, self.workspace)
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

    def publish(
        self,
        public: PublicAnchorBundle,
        *,
        dry_run: bool = False,
        push: bool = False,
        run_id: str = "",
        signed_payload: dict | None = None,
    ) -> GitBackendResult:
        cfg = self.cfg
        allow_push = push and cfg.allow_push and not dry_run
        receipt = ExternalStartAnchorReceipt(
            receipt_id=new_id("esar"),
            run_id=run_id or new_id("run"),
            anchor_sequence=public.anchor_sequence,
            boot_bundle_sha256=public.boot_bundle_sha256,
            public_anchor_sha256=public.public_anchor_sha256,
            dry_run=dry_run or not allow_push,
        )
        if dry_run or not allow_push:
            local = self.workspace / ".hg-local" / "external_start_anchor" / "dry_run_repo"
            if local.exists():
                shutil.rmtree(local)
            local.mkdir(parents=True, exist_ok=True)
            _run_git(["init", "-b", cfg.anchor_branch], local)
            paths = write_anchor_files(local, cfg, public, payload_override=signed_payload)
            receipt.pushed = False
            return GitBackendResult(
                status=AnchorBackendStatus.PUSH_SKIPPED if dry_run else AnchorBackendStatus.DRY_RUN,
                dry_run=True,
                pushed=False,
                commit=None,
                anchor_paths=paths,
                receipt=receipt,
                detail="dry-run/local draft only",
            )

        repo = self.prepare_repo()
        paths = write_anchor_files(repo, cfg, public, payload_override=signed_payload)
        from hg_runtime.external_start_anchor.credentials import git_subprocess_env

        git_env = git_subprocess_env()
        _run_git(["add", "README.md", cfg.anchor_public_dir], repo, env=git_env)
        short = public.boot_bundle_sha256[:12]
        msg = f"anchor(agent0): sequence {public.anchor_sequence} {short}"
        _run_git(["commit", "-m", msg], repo, env=git_env)
        head = _run_git(["rev-parse", "HEAD"], repo, env=git_env).stdout.strip()
        public.github_anchor_commit = head
        receipt.github_commit_sha = head
        _run_git(["push", "-u", "origin", cfg.anchor_branch], repo, env=git_env)
        receipt.pushed = True
        commit = GitHubAnchorCommit(
            commit_sha=head,
            branch=cfg.anchor_branch,
            message=msg,
            anchor_file_path=paths["latest_json"],
            commit_url=f"{cfg.anchor_repo_remote.replace('.git', '')}/commit/{head}" if cfg.anchor_repo_remote.startswith("http") else None,
        )
        return GitBackendResult(
            status=AnchorBackendStatus.READY,
            dry_run=False,
            pushed=True,
            commit=commit,
            anchor_paths=paths,
            receipt=receipt,
            detail="pushed",
        )

    def read_committed_public(self, commit_sha: str | None = None) -> dict[str, Any]:
        repo = self.cfg.resolved_repo_path(self.workspace)
        path = self.cfg.sequence_file
        if commit_sha:
            from hg_runtime.external_start_anchor.credentials import git_subprocess_env

            raw = _run_git(["show", f"{commit_sha}:{path}"], repo, env=git_subprocess_env()).stdout
        else:
            raw = (repo / path).read_text(encoding="utf-8")
        return json.loads(raw)


__all__ = [
    "AnchorRepoDirty",
    "GitBackendResult",
    "GitHistoryRewriteAttempted",
    "GitHubGitBackend",
    "write_anchor_files",
]
