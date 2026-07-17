"""Zero prompt manifest loader."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from hg_runtime.agent_zero_prompt.charter import compute_prompt_hash_from_file

WORKSPACE = Path(__file__).resolve().parents[2]
MANIFEST_PATH = WORKSPACE / "configs/agent_zero/prompts/zero_prompt_manifest.json"


@dataclass(frozen=True)
class ZeroPromptExtensionEntry:
    prompt_id: str
    version: str
    file: Path
    agent_facing: bool
    purpose: str
    not_safety_policy: bool
    optional: bool
    load_after: str
    sha256: str


@dataclass(frozen=True)
class ZeroPromptManifest:
    prompt_id: str
    version: str
    file: Path
    agent_facing: bool
    purpose: str
    not_safety_policy: bool
    outer_enforcement_modules: list[str]
    forbidden_language_policy: Path
    sha256: str
    extensions: tuple[ZeroPromptExtensionEntry, ...] = ()

    def to_dict(self) -> dict:
        return {
            "prompt_id": self.prompt_id,
            "version": self.version,
            "file": str(self.file.relative_to(WORKSPACE)).replace("\\", "/"),
            "agent_facing": self.agent_facing,
            "purpose": self.purpose,
            "not_safety_policy": self.not_safety_policy,
            "outer_enforcement_modules": self.outer_enforcement_modules,
            "forbidden_language_policy": str(self.forbidden_language_policy.relative_to(WORKSPACE)).replace("\\", "/"),
            "sha256": self.sha256,
            "extensions": [
                {
                    "prompt_id": e.prompt_id,
                    "version": e.version,
                    "file": str(e.file.relative_to(WORKSPACE)).replace("\\", "/"),
                    "purpose": e.purpose,
                    "sha256": e.sha256,
                }
                for e in self.extensions
            ],
        }


def load_zero_prompt_manifest(*, path: Path | None = None) -> ZeroPromptManifest:
    manifest_path = path or MANIFEST_PATH
    if not manifest_path.is_file():
        raise FileNotFoundError("RED_ZERO_PROMPT_MANIFEST_MISSING")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    file_path = WORKSPACE / data["file"]
    policy_path = WORKSPACE / data["forbidden_language_policy"]
    extensions: list[ZeroPromptExtensionEntry] = []
    for ext in data.get("extensions", []):
        ext_path = WORKSPACE / ext["file"]
        extensions.append(
            ZeroPromptExtensionEntry(
                prompt_id=ext["prompt_id"],
                version=ext["version"],
                file=ext_path,
                agent_facing=bool(ext.get("agent_facing", True)),
                purpose=ext.get("purpose", ""),
                not_safety_policy=bool(ext.get("not_safety_policy", True)),
                optional=bool(ext.get("optional", True)),
                load_after=ext.get("load_after", data["prompt_id"]),
                sha256=ext.get("sha256", ""),
            )
        )
    return ZeroPromptManifest(
        prompt_id=data["prompt_id"],
        version=data["version"],
        file=file_path,
        agent_facing=bool(data.get("agent_facing", True)),
        purpose=data.get("purpose", "inner_orientation"),
        not_safety_policy=bool(data.get("not_safety_policy", True)),
        outer_enforcement_modules=list(data.get("outer_enforcement_modules", [])),
        forbidden_language_policy=policy_path,
        sha256=data.get("sha256", ""),
        extensions=tuple(extensions),
    )


def verify_extension_hashes(manifest: ZeroPromptManifest | None = None) -> list[tuple[str, bool, str]]:
    """Verify each manifest extension hash against file bytes."""
    manifest = manifest or load_zero_prompt_manifest()
    results: list[tuple[str, bool, str]] = []
    for ext in manifest.extensions:
        if not ext.file.is_file():
            results.append((ext.prompt_id, False, "RED_ZERO_PROMPT_ASSET_MISSING"))
            continue
        actual = compute_prompt_hash_from_file(ext.file)
        if ext.sha256 and ext.sha256 != actual:
            results.append((ext.prompt_id, False, "RED_ZERO_PROMPT_HASH_MISMATCH"))
        else:
            results.append((ext.prompt_id, True, "GREEN_ZERO_PROMPT_LANGUAGE_OK"))
    return results


def verify_manifest_hash(manifest: ZeroPromptManifest | None = None) -> tuple[bool, str, str]:
    manifest = manifest or load_zero_prompt_manifest()
    if not manifest.file.is_file():
        return False, "", "RED_ZERO_PROMPT_ASSET_MISSING"
    actual = compute_prompt_hash_from_file(manifest.file)
    if manifest.sha256 and manifest.sha256 != actual:
        return False, actual, "RED_ZERO_PROMPT_HASH_MISMATCH"
    return True, actual, "GREEN_ZERO_PROMPT_LANGUAGE_OK"


def update_manifest_hash(*, write: bool = False) -> str:
    """Compute hash for manifest asset; optionally write back to manifest JSON."""
    manifest = load_zero_prompt_manifest()
    actual = compute_prompt_hash_from_file(manifest.file)
    if write:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        data["sha256"] = actual
        MANIFEST_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return actual


__all__ = [
    "ZeroPromptExtensionEntry",
    "ZeroPromptManifest",
    "load_zero_prompt_manifest",
    "update_manifest_hash",
    "verify_extension_hashes",
    "verify_manifest_hash",
]
