from __future__ import annotations

from pathlib import Path


def persona_template_path(rel: str) -> Path:
    return Path(__file__).resolve().parent / "public_persona_templates" / rel
