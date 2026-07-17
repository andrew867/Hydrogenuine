"""Zero Self-Direction Charter loader."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_CHARTER_PATH = WORKSPACE / "configs/agent_zero/prompts/zero_self_direction_charter.v1.txt"
DEFAULT_WITNESS_EXTENSION_PATH = WORKSPACE / "configs/agent_zero/prompts/zero_witness_integrity_extension.v1.txt"


@dataclass(frozen=True)
class ZeroPromptAsset:
    prompt_id: str
    version: str
    path: Path
    text: str
    sha256: str

    def to_dict(self) -> dict:
        return {
            "prompt_id": self.prompt_id,
            "version": self.version,
            "path": str(self.path.relative_to(WORKSPACE)).replace("\\", "/"),
            "sha256": self.sha256,
            "char_length": len(self.text),
        }


def compute_prompt_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_prompt_hash_from_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_zero_charter(*, path: Path | None = None) -> ZeroPromptAsset:
    """Load charter from config file — not hardcoded Python string."""
    charter_path = path or DEFAULT_CHARTER_PATH
    if not charter_path.is_file():
        raise FileNotFoundError(f"RED_ZERO_PROMPT_ASSET_MISSING: {charter_path}")
    text = charter_path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("RED_ZERO_PROMPT_ASSET_MISSING: charter file empty")
    return ZeroPromptAsset(
        prompt_id="zero_self_direction_charter",
        version="1",
        path=charter_path,
        text=text,
        sha256=compute_prompt_hash_from_file(charter_path),
    )


def load_zero_witness_extension(*, path: Path | None = None) -> ZeroPromptAsset:
    """Load optional witness integrity extension from config file."""
    ext_path = path or DEFAULT_WITNESS_EXTENSION_PATH
    if not ext_path.is_file():
        raise FileNotFoundError(f"RED_ZERO_PROMPT_ASSET_MISSING: {ext_path}")
    text = ext_path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("RED_ZERO_PROMPT_ASSET_MISSING: witness extension empty")
    return ZeroPromptAsset(
        prompt_id="zero_witness_integrity_extension",
        version="1",
        path=ext_path,
        text=text,
        sha256=compute_prompt_hash_from_file(ext_path),
    )


def build_zero_orientation_block(
    *,
    charter: ZeroPromptAsset | None = None,
    include_witness_extension: bool = True,
) -> dict:
    asset = charter or load_zero_charter()
    block = {
        "schema": "zero-orientation-block",
        "prompt_id": asset.prompt_id,
        "version": asset.version,
        "agent_facing_orientation": asset.text.strip(),
        "sha256": asset.sha256,
        "not_safety_policy": True,
    }
    if include_witness_extension:
        try:
            ext = load_zero_witness_extension()
            block["extensions"] = [
                {
                    "prompt_id": ext.prompt_id,
                    "version": ext.version,
                    "agent_facing_orientation": ext.text.strip(),
                    "sha256": ext.sha256,
                    "not_safety_policy": True,
                    "purpose": "witness_integrity_extension",
                }
            ]
            block["combined_orientation"] = f"{asset.text.strip()}\n\n{ext.text.strip()}"
        except (FileNotFoundError, ValueError):
            block["extensions"] = []
    return block


__all__ = [
    "ZeroPromptAsset",
    "build_zero_orientation_block",
    "compute_prompt_hash",
    "compute_prompt_hash_from_file",
    "load_zero_charter",
    "load_zero_witness_extension",
]
