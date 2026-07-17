"""Deterministic source text normalization for SQP duplicate checks."""

from __future__ import annotations

import re

_SPACE_RE = re.compile(r"\s+")


def normalize_source_text(text: str) -> str:
    """Return a conservative comparison form without claiming semantic equality."""

    return _SPACE_RE.sub(" ", text.casefold().strip())
