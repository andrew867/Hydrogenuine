"""Path parity manifest loader and validation (CT-03 PAR)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_SUBSYSTEMS = (
    "RTC",
    "AEP",
    "CRR",
    "GPP",
    "UEAK",
    "OEA",
    "SRP",
    "HAL",
)


@dataclass(frozen=True)
class SubsystemParity:
    subsystem: str
    demo_handler: str
    integrated_handler: str
    parity_status: str
    shared_tests: tuple[str, ...]
    allowed_event_deltas: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, subsystem: str, raw: dict[str, Any]) -> SubsystemParity:
        return cls(
            subsystem=subsystem,
            demo_handler=str(raw.get("demo_handler", "")),
            integrated_handler=str(raw.get("integrated_handler", "")),
            parity_status=str(raw.get("parity_status", "unknown")),
            shared_tests=tuple(raw.get("shared_tests", [])),
            allowed_event_deltas=tuple(raw.get("allowed_event_deltas", [])),
        )


@dataclass(frozen=True)
class PathParityManifest:
    schema: str
    manifest_hash: str
    subsystems: dict[str, SubsystemParity]
    shared_tests: tuple[str, ...]
    waivers: tuple[dict[str, Any], ...]

    def absent_in_demo(self) -> frozenset[str]:
        return frozenset(
            name
            for name, entry in self.subsystems.items()
            if entry.parity_status == "absent_in_demo"
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "manifest_hash": self.manifest_hash,
            "subsystems": {
                name: {
                    "demo_handler": e.demo_handler,
                    "integrated_handler": e.integrated_handler,
                    "parity_status": e.parity_status,
                    "shared_tests": list(e.shared_tests),
                    "allowed_event_deltas": list(e.allowed_event_deltas),
                }
                for name, e in self.subsystems.items()
            },
            "shared_tests": list(self.shared_tests),
            "waivers": list(self.waivers),
        }


def default_manifest_path(workspace: Path | None = None) -> Path:
    root = workspace or Path(__file__).resolve().parents[2]
    return root / "config" / "path_parity_manifest_v1.json"


def manifest_hash(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "manifest_hash"}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


def load_manifest(path: Path | None = None) -> PathParityManifest:
    manifest_path = path or default_manifest_path()
    if not manifest_path.exists():
        raise FileNotFoundError(f"path parity manifest missing: {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = payload.get("manifest_hash")
    computed = manifest_hash(payload)
    if expected and expected != computed:
        raise ValueError(f"manifest hash mismatch: expected {expected}, got {computed}")
    subsystems: dict[str, SubsystemParity] = {}
    for name in REQUIRED_SUBSYSTEMS:
        raw = payload.get("subsystems", {}).get(name)
        if not raw:
            raise ValueError(f"manifest missing subsystem: {name}")
        subsystems[name] = SubsystemParity.from_dict(name, raw)
    return PathParityManifest(
        schema=str(payload.get("schema", "")),
        manifest_hash=computed,
        subsystems=subsystems,
        shared_tests=tuple(payload.get("shared_tests", [])),
        waivers=tuple(payload.get("waivers", [])),
    )


__all__ = [
    "PathParityManifest",
    "REQUIRED_SUBSYSTEMS",
    "SubsystemParity",
    "default_manifest_path",
    "load_manifest",
    "manifest_hash",
]
