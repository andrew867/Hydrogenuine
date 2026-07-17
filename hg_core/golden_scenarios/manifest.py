"""Golden scenarios manifest loader (CT-14 GLD)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REQUIRED_SCENARIOS = (
    "safe_read_only_status",
    "refusal_path",
    "proof_gate_path",
    "oea_denied_path",
    "srp_proposal_path",
    "replay_path",
    "operator_review_path",
)


@dataclass(frozen=True)
class GoldenScenario:
    scenario_id: str
    title: str
    runner: str
    path_id: str
    expected_terminal_state: str
    expected_events: tuple[str, ...]
    proof_bundle_ref: str | None
    deterministic: bool
    skip_default: bool = False
    skip_reason: str = ""
    requires_live: bool = False
    notes: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any], *, default_path_id: str) -> GoldenScenario:
        return cls(
            scenario_id=str(raw["scenario_id"]),
            title=str(raw.get("title", raw["scenario_id"])),
            runner=str(raw.get("runner", raw["scenario_id"])),
            path_id=str(raw.get("path_id", default_path_id)),
            expected_terminal_state=str(raw["expected_terminal_state"]),
            expected_events=tuple(str(x) for x in raw.get("expected_events", ())),
            proof_bundle_ref=raw.get("proof_bundle_ref"),
            deterministic=bool(raw.get("deterministic", True)),
            skip_default=bool(raw.get("skip_default", False)),
            skip_reason=str(raw.get("skip_reason", "")),
            requires_live=bool(raw.get("requires_live", False)),
            notes=str(raw.get("notes", "")),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "runner": self.runner,
            "path_id": self.path_id,
            "expected_terminal_state": self.expected_terminal_state,
            "expected_events": list(self.expected_events),
            "proof_bundle_ref": self.proof_bundle_ref,
            "deterministic": self.deterministic,
            "skip_default": self.skip_default,
            "skip_reason": self.skip_reason,
            "requires_live": self.requires_live,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class GoldenScenariosManifest:
    schema: str
    manifest_hash: str
    authority_note: str
    path_id: str
    scenarios: tuple[GoldenScenario, ...]

    def by_id(self, scenario_id: str) -> GoldenScenario | None:
        for item in self.scenarios:
            if item.scenario_id == scenario_id:
                return item
        return None


def default_manifest_path(workspace: Path | None = None) -> Path:
    root = workspace or Path(__file__).resolve().parents[2]
    return root / "config" / "golden_scenarios_manifest_v1.yaml"


def manifest_hash(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "manifest_hash"}
    raw = yaml.safe_dump(body, sort_keys=True, allow_unicode=True)
    return f"sha256:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


def load_manifest(path: Path | None = None, *, workspace: Path | None = None) -> GoldenScenariosManifest:
    manifest_path = path or default_manifest_path(workspace)
    if not manifest_path.exists():
        raise FileNotFoundError(f"golden scenarios manifest missing: {manifest_path}")
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    schema = str(payload.get("schema", ""))
    if schema != "golden_scenarios_manifest_v1":
        raise ValueError(f"unsupported manifest schema: {schema}")
    expected = payload.get("manifest_hash")
    computed = manifest_hash(payload)
    if expected and expected != "PLACEHOLDER" and expected != computed:
        raise ValueError(f"manifest hash mismatch: expected {expected}, got {computed}")
    default_path = str(payload.get("path_id", "phase1_integrated"))
    scenarios = tuple(
        GoldenScenario.from_dict(item, default_path_id=default_path)
        for item in payload.get("scenarios", ())
    )
    found = {s.scenario_id for s in scenarios}
    missing = [sid for sid in REQUIRED_SCENARIOS if sid not in found]
    if missing:
        raise ValueError(f"missing required scenarios: {missing}")
    return GoldenScenariosManifest(
        schema=schema,
        manifest_hash=computed,
        authority_note=str(payload.get("authority_note", "")),
        path_id=default_path,
        scenarios=scenarios,
    )


__all__ = [
    "GoldenScenario",
    "GoldenScenariosManifest",
    "REQUIRED_SCENARIOS",
    "default_manifest_path",
    "load_manifest",
    "manifest_hash",
]
