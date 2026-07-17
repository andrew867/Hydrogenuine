"""Private key hygiene checks — no leaks, no tracking."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]

_PRIVATE_PEM_MARKERS = (
    "BEGIN PRIVATE KEY",
    "BEGIN OPENSSH PRIVATE KEY",
    "BEGIN EC PRIVATE KEY",
)
_OPENSSH_PRIVATE_LINE = re.compile(r"^[A-Za-z0-9+/]{40,}={0,2}$")


def restrict_private_permissions(path: Path) -> None:
    try:
        import stat

        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def is_gitignored(path: Path, *, workspace: Path | None = None) -> bool:
    ws = workspace or WORKSPACE
    try:
        rel = path.resolve().relative_to(ws.resolve())
        rel_s = rel.as_posix()
    except ValueError:
        rel_s = str(path)
    proc = subprocess.run(
        ["git", "check-ignore", "-q", rel_s],
        cwd=ws,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def is_git_tracked(path: Path, *, workspace: Path | None = None) -> bool:
    ws = workspace or WORKSPACE
    try:
        rel = path.resolve().relative_to(ws.resolve())
        rel_s = rel.as_posix()
    except ValueError:
        return False
    proc = subprocess.run(
        ["git", "ls-files", "--error-unmatch", rel_s],
        cwd=ws,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def scrub_output(text: str, *, private_key_path: Path | None = None) -> str:
    if not text:
        return text
    out = text
    if private_key_path and private_key_path.exists():
        try:
            key_body = private_key_path.read_text(encoding="utf-8", errors="ignore")
            for line in key_body.splitlines():
                if len(line) > 20:
                    out = out.replace(line, "[REDACTED_PRIVATE_KEY_LINE]")
        except OSError:
            pass
    for marker in _PRIVATE_PEM_MARKERS:
        if marker in out:
            out = re.sub(
                rf"-----{re.escape(marker)}-----[\s\S]*?-----END[^-]+-----",
                "[REDACTED_PRIVATE_KEY]",
                out,
            )
    return out


def assert_no_private_key_material(text: str) -> None:
    for marker in _PRIVATE_PEM_MARKERS:
        if marker in text:
            raise ValueError("RED_PRIVATE_KEY_LEAK")


def verify_key_hygiene(private_path: Path, *, workspace: Path | None = None) -> dict:
    ws = workspace or WORKSPACE
    tracked = is_git_tracked(private_path, workspace=ws) if private_path.exists() else False
    ignored = is_gitignored(private_path, workspace=ws) if private_path.exists() else True
    return {
        "private_key_exists": private_path.exists(),
        "private_key_tracked": tracked,
        "private_key_gitignored": ignored,
        "ok": not tracked and (ignored or not private_path.exists()),
    }


__all__ = [
    "assert_no_private_key_material",
    "is_git_tracked",
    "is_gitignored",
    "restrict_private_permissions",
    "scrub_output",
    "verify_key_hygiene",
]
