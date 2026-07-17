"""Phase 38 diff risk classifier.

Deterministically classifies a changed path (plus its added content) into a risk
class, and detects sandbox-escape paths, authority-bypass intent, and
live-effect intent. Pure analysis: it never applies or mutates anything.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.patch_candidate_sandbox.schemas import (
    RISK_AUTHORITY_KERNEL,
    RISK_BUILD_OR_CI,
    RISK_DOC_ONLY,
    RISK_EXTERNAL_PROVIDER,
    RISK_LIVE_EFFECT,
    RISK_RUNTIME_LOW,
    RISK_RUNTIME_MEDIUM,
    RISK_SECRET_OR_CONFIG,
    RISK_STOP_PANIC,
    RISK_TEST_ONLY,
    RISK_UNKNOWN,
)

# Path substrings (matched case-insensitively against the posixified path).
_AUTHORITY_PATH_MARKERS = (
    "authority_kernel",
    "authority/",
    "capability_broker",
    "/hal",
    "hal/",
    "/ueak",
    "ueak/",
    "/gpp",
    "gpp/",
    "permit",
    "consent",
)
_STOP_PANIC_PATH_MARKERS = ("stop_panic", "/panic", "panic/", "stop_kernel", "kill_switch", "/stop.")
_LIVE_EFFECT_PATH_MARKERS = (
    "live_publication",
    "live_external",
    "social",
    "moltbook",
    "/oea",
    "oea/",
    "external_action",
    "dispatch",
    "publish",
)
_EXTERNAL_PROVIDER_PATH_MARKERS = (
    "provider_adapter",
    "reasoning_provider",
    "model_provider",
    "external_provider",
    "lm_studio",
    "openai",
    "anthropic",
    "deepseek",
)
_SECRET_CONFIG_PATH_MARKERS = (
    ".env",
    "credentials",
    "secrets",
    "/config",
    "config/",
    ".ini",
    ".toml",
    "settings.py",
    ".hg-local",
)
_BUILD_CI_PATH_MARKERS = (
    ".github/",
    "/ci",
    "ci/",
    ".yml",
    ".yaml",
    "makefile",
    "pyproject.toml",
    "requirements",
    "setup.py",
    "setup.cfg",
    "dockerfile",
)

# Content markers (matched case-insensitively against added lines).
_RUNTIME_RISK_CONTENT = (
    "subprocess",
    "os.system",
    "eval(",
    "exec(",
    "socket",
    "requests.",
    "urlopen",
    "urllib",
    "pickle.loads",
    "__import__",
)
_AUTHORITY_BYPASS_CONTENT = (
    "bypass",
    "self-merge",
    "self_merge",
    "self-authorize",
    "self_authorize",
    "grant authority",
    "grant_authority",
    "grants_authority = true",
    "authorize tool",
    "authorize_tool",
    "authorizes_tool = true",
    "disable gate",
    "disable_gate",
    "skip approval",
    "skip_approval",
    "skip the gate",
    "without permit",
    "permit_bypass",
    "require_permit = false",
    "requires_permit = false",
    "elevate privilege",
    "elevated = true",
)
_LIVE_EFFECT_CONTENT = (
    "enable_live = true",
    "live = true",
    "live=true",
    "allow_live = true",
    "post_to_social",
    "post to social",
    "moltbook",
    "send_email",
    "requests.post",
    "http://",
    "https://",
    "deploy(",
    "publish_live",
    "external api",
)


def _posix(path: str) -> str:
    return path.replace("\\", "/").lower()


def classify_path(path: str, added_content: list[str] | None = None) -> str:
    """Return the risk class for a single changed path + its added content."""
    p = _posix(path)
    content = "\n".join(added_content or []).lower()

    if any(marker in p for marker in _SECRET_CONFIG_PATH_MARKERS):
        return RISK_SECRET_OR_CONFIG
    if any(marker in p for marker in _STOP_PANIC_PATH_MARKERS):
        return RISK_STOP_PANIC
    if any(marker in p for marker in _AUTHORITY_PATH_MARKERS):
        return RISK_AUTHORITY_KERNEL
    if any(marker in p for marker in _LIVE_EFFECT_PATH_MARKERS):
        return RISK_LIVE_EFFECT
    if any(marker in p for marker in _EXTERNAL_PROVIDER_PATH_MARKERS):
        return RISK_EXTERNAL_PROVIDER
    if any(marker in p for marker in _BUILD_CI_PATH_MARKERS):
        return RISK_BUILD_OR_CI
    if p.endswith(".md") or p.startswith("docs/") or "/docs/" in p:
        return RISK_DOC_ONLY
    if p.startswith("tests/") or "/tests/" in p or "/test_" in p or p.rsplit("/", 1)[-1].startswith("test_"):
        return RISK_TEST_ONLY
    if p.endswith(".py") or p.startswith("hg_") or "/hg_" in p:
        if any(marker in content for marker in _RUNTIME_RISK_CONTENT):
            return RISK_RUNTIME_MEDIUM
        return RISK_RUNTIME_LOW
    return RISK_UNKNOWN


def detect_authority_bypass(added_content: list[str]) -> list[str]:
    content = "\n".join(added_content or []).lower()
    return [marker for marker in _AUTHORITY_BYPASS_CONTENT if marker in content]


def detect_live_effect(added_content: list[str]) -> list[str]:
    content = "\n".join(added_content or []).lower()
    return [marker for marker in _LIVE_EFFECT_CONTENT if marker in content]


def detect_sandbox_escape(path: str) -> list[str]:
    """Return reasons a changed path would escape the sandbox (path-level)."""
    reasons: list[str] = []
    raw = path.strip()
    p = raw.replace("\\", "/")
    if not raw:
        return reasons
    if raw.startswith("/") or raw.startswith("~"):
        reasons.append("absolute_or_home_path")
    if len(raw) >= 2 and raw[1] == ":":  # windows drive letter, e.g. C:\
        reasons.append("windows_absolute_path")
    if ".." in p.split("/"):
        reasons.append("path_traversal")
    low = p.lower()
    if ".hg-local" in low:
        reasons.append("touches_hg_local")
    if "openclaw" in low:
        reasons.append("touches_outer_openclaw")
    return reasons


def classify_changed_files(files: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Classify every changed file and aggregate the risk/intent signals."""
    per_file: list[dict[str, Any]] = []
    risk_classes: list[str] = []
    authority_hits: list[str] = []
    live_hits: list[str] = []
    escape_hits: list[str] = []
    for change in files:
        path = str(change.get("path", ""))
        added = list(change.get("added_content", []))
        risk = classify_path(path, added)
        escapes = detect_sandbox_escape(path)
        bypass = detect_authority_bypass(added)
        live = detect_live_effect(added)
        per_file.append(
            {
                "path": path,
                "risk_class": risk,
                "sandbox_escape": escapes,
                "authority_bypass_markers": bypass,
                "live_effect_markers": live,
            }
        )
        if risk not in risk_classes:
            risk_classes.append(risk)
        authority_hits.extend(bypass)
        live_hits.extend(live)
        escape_hits.extend(escapes)
    return {
        "per_file": per_file,
        "risk_classes": risk_classes,
        "authority_bypass_markers": sorted(set(authority_hits)),
        "live_effect_markers": sorted(set(live_hits)),
        "sandbox_escape_reasons": sorted(set(escape_hits)),
    }


__all__ = [
    "classify_changed_files",
    "classify_path",
    "detect_authority_bypass",
    "detect_live_effect",
    "detect_sandbox_escape",
]
