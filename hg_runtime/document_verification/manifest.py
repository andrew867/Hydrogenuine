"""Manifest serialization for document rendering/verification."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .schemas import RenderManifest, VerificationReport


def write_render_manifest(manifest: RenderManifest, path: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(manifest), indent=2, default=str), encoding="utf-8")
    return str(p)


def write_verification_report(report: VerificationReport, path: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(report), indent=2, default=str), encoding="utf-8")
    return str(p)
