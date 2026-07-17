"""OpenVINO model helper — downloads disabled by default.

Model downloads require HG_ALLOW_MODEL_DOWNLOADS=true.
Forbidden patterns and 30B-class defaults are rejected.
No downloads during normal container startup.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

from .runtime_config import RuntimeConfig


_FORBIDDEN_DOWNLOAD_PATTERNS = [
    "deepseek", "cybersecurity", "offensive", "uncensored", "30b",
]

_LARGE_MODEL_PATTERNS = ["30b", "33b", "34b", "70b", "72b"]


@dataclass
class ModelProvenance:
    model_id: str
    source: str
    download_requested: bool
    download_performed: bool
    checksum: str = ""
    provenance_file: str = ""
    operator_confirmation_required: bool = True
    rejected: bool = False
    rejection_reason: str = ""


def list_model_dir(cfg: RuntimeConfig) -> list[str]:
    model_dir = Path(cfg.openvino_model_dir)
    if not model_dir.exists():
        return []
    return [p.name for p in model_dir.iterdir() if p.is_dir() or p.suffix in (".xml", ".bin", ".onnx")]


def validate_model_path(model_dir: str) -> bool:
    p = Path(model_dir)
    return p.exists() and p.is_dir()


def is_download_allowed(cfg: RuntimeConfig) -> bool:
    return cfg.allow_model_downloads


def is_model_forbidden(model_id: str) -> bool:
    lower = model_id.lower()
    return any(p in lower for p in _FORBIDDEN_DOWNLOAD_PATTERNS)


def is_large_model(model_id: str) -> bool:
    lower = model_id.lower()
    return any(p in lower for p in _LARGE_MODEL_PATTERNS)


def request_model_download(
    model_id: str,
    source: str,
    cfg: RuntimeConfig,
    dry_run: bool = True,
) -> ModelProvenance:
    if is_model_forbidden(model_id):
        return ModelProvenance(
            model_id=model_id, source=source,
            download_requested=True, download_performed=False,
            rejected=True, rejection_reason=f"Model matches forbidden pattern",
        )
    if is_large_model(model_id):
        return ModelProvenance(
            model_id=model_id, source=source,
            download_requested=True, download_performed=False,
            rejected=True, rejection_reason="30B-class or larger model rejected by default",
        )
    if not is_download_allowed(cfg):
        return ModelProvenance(
            model_id=model_id, source=source,
            download_requested=True, download_performed=False,
            rejected=True, rejection_reason="HG_ALLOW_MODEL_DOWNLOADS is false",
        )

    prov = ModelProvenance(
        model_id=model_id, source=source,
        download_requested=True,
        download_performed=not dry_run,
    )

    if not dry_run:
        prov_dir = Path(cfg.openvino_model_dir)
        prov_dir.mkdir(parents=True, exist_ok=True)
        prov_file = prov_dir / f"{model_id.replace('/', '_')}_provenance.json"
        prov_file.write_text(json.dumps(asdict(prov), indent=2), encoding="utf-8")
        prov.provenance_file = str(prov_file)

    return prov


def write_provenance_receipt(prov: ModelProvenance, output_dir: str) -> str:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{prov.model_id.replace('/', '_')}_provenance.json"
    path.write_text(json.dumps(asdict(prov), indent=2), encoding="utf-8")
    return str(path)
