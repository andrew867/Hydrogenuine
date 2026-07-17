from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def loads_lenient(text: str, default: Any = None) -> Any:
    raw = text or ""
    try:
        return json.loads(raw)
    except Exception:
        pass

    cleaned = raw
    # Repair legacy over-escaped apostrophes from old file writers.
    cleaned = cleaned.replace("\\'", "'")
    # Remove trailing commas before object/array closes.
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        return default


def load_path_lenient(path: str | Path, default: Any = None) -> Any:
    try:
        return loads_lenient(Path(path).read_text(encoding="utf-8", errors="replace"), default)
    except Exception:
        return default
