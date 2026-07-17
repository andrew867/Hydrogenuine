"""JSON renderer for zero CLI output. Stable, machine-readable."""

from __future__ import annotations

import json


def render_json(data: dict, *, indent: int = 2) -> str:
    return json.dumps(data, indent=indent, sort_keys=True, default=str)
