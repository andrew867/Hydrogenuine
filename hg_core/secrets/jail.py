"""TER path-jail exclusions for secret files (CT-02)."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

SECRET_PATH_MARKERS: tuple[str, ...] = (
    ".env",
    ".env.",
    "credentials/",
    "credentials\\",
    "/credentials/",
    "\\credentials\\",
    ".pem",
    "id_rsa",
    "id_ed25519",
    "secrets/",
    "secrets\\",
)

JAIL_VIOLATION_CODE = "TER_JAIL_VIOLATION"


def argv_touches_secret_path(argv: Sequence[str], *, cwd: str | Path | None = None) -> bool:
    joined = " ".join(argv).replace("\\", "/").lower()
    for marker in SECRET_PATH_MARKERS:
        normalized = marker.replace("\\", "/").lower()
        if normalized in joined:
            return True
    if cwd is not None:
        base = Path(cwd)
        for part in argv[1:]:
            if part.startswith("-"):
                continue
            candidate = (base / part).as_posix().lower()
            for marker in SECRET_PATH_MARKERS:
                if marker.replace("\\", "/").lower().strip("/") in candidate:
                    return True
    return False


def check_ter_secret_jail(argv: Sequence[str], *, cwd: str | Path) -> tuple[bool, str]:
    if argv_touches_secret_path(argv, cwd=cwd):
        return False, JAIL_VIOLATION_CODE
    return True, "ok"


__all__ = [
    "JAIL_VIOLATION_CODE",
    "SECRET_PATH_MARKERS",
    "argv_touches_secret_path",
    "check_ter_secret_jail",
]
