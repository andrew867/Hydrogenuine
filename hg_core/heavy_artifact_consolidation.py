from __future__ import annotations

import hashlib
from pathlib import Path


def artifact_id(path: str | Path) -> str:
    p = Path(path)
    return hashlib.sha256(str(p).encode("utf-8")).hexdigest()
