"""Canonical paths for GitHub anchor repo init."""

from __future__ import annotations

import os
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]

DEFAULT_DEPLOY_KEY_DIR = WORKSPACE / ".hg-local" / "github_anchor_ssh"
DEFAULT_DEPLOY_KEY_STEM = "id_agent_zero_anchor_ed25519"
DEFAULT_SIGNING_DIR = WORKSPACE / ".hg-local" / "anchor_signing"
DEFAULT_SIGNING_PRIVATE = "agent_zero_anchor_ed25519.pem"
DEFAULT_SIGNING_PUBLIC = "agent_zero_anchor_ed25519.pub.pem"
CANONICAL_ENV = WORKSPACE / ".hg-local" / "secrets" / "github_anchor.env"
LOCAL_ANCHOR_CONFIG = WORKSPACE / "configs" / "external_start_anchor" / "github_anchor.local.json"
EXAMPLE_ANCHOR_CONFIG = WORKSPACE / "configs" / "external_start_anchor" / "github_anchor.local.example.json"


def deploy_key_private() -> Path:
    env = os.environ.get("HG_GITHUB_ANCHOR_SSH_KEY", "").strip()
    if env:
        p = Path(env)
        return p if p.is_absolute() else WORKSPACE / p
    return DEFAULT_DEPLOY_KEY_DIR / DEFAULT_DEPLOY_KEY_STEM


def deploy_key_public() -> Path:
    return Path(str(deploy_key_private()) + ".pub")


def signing_private() -> Path:
    env = os.environ.get("HG_ANCHOR_SIGNING_PRIVATE_KEY_PATH", "").strip()
    if env:
        p = Path(env)
        return p if p.is_absolute() else WORKSPACE / p
    return DEFAULT_SIGNING_DIR / DEFAULT_SIGNING_PRIVATE


def signing_public() -> Path:
    env = os.environ.get("HG_ANCHOR_SIGNING_PUBLIC_KEY_PATH", "").strip()
    if env:
        p = Path(env)
        return p if p.is_absolute() else WORKSPACE / p
    return DEFAULT_SIGNING_DIR / DEFAULT_SIGNING_PUBLIC


def anchor_repo_path() -> Path:
    env = os.environ.get("HG_GITHUB_ANCHOR_REPO_PATH", "").strip()
    if env:
        p = Path(env)
        return p if p.is_absolute() else WORKSPACE / p
    return WORKSPACE.parent / "hydrogenuine-agent-zero-anchor"


def anchor_remote() -> str:
    return os.environ.get("HG_GITHUB_ANCHOR_REPO_REMOTE", "").strip()


def anchor_branch() -> str:
    return os.environ.get("HG_GITHUB_ANCHOR_BRANCH", "main").strip() or "main"


def push_allowed() -> bool:
    return os.environ.get("HG_ANCHOR_ALLOW_PUSH", "").lower() in {"1", "true", "yes"}


def live_ssh_test_enabled() -> bool:
    return os.environ.get("HG_GITHUB_ANCHOR_LIVE_SSH_TEST", "").lower() in {"1", "true", "yes"}


__all__ = [
    "CANONICAL_ENV",
    "DEFAULT_DEPLOY_KEY_DIR",
    "EXAMPLE_ANCHOR_CONFIG",
    "LOCAL_ANCHOR_CONFIG",
    "WORKSPACE",
    "anchor_branch",
    "anchor_remote",
    "anchor_repo_path",
    "deploy_key_private",
    "deploy_key_public",
    "live_ssh_test_enabled",
    "push_allowed",
    "signing_private",
    "signing_public",
]
