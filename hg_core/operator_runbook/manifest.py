"""Operator runbook manifest loader (CT-15 RUN)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REQUIRED_PROCEDURES = (
    "freeze_queues",
    "disable_oea_real",
    "disable_ter",
    "revoke_live_cognition",
    "enter_safe_mode",
    "recover_lockdown",
    "restore_from_bundle",
    "export_incident",
    "replay_check",
    "ops_status",
)


@dataclass(frozen=True)
class OperatorProcedure:
    procedure_id: str
    script: str
    scope: str
    requires_confirm: bool
    mutating: bool

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> OperatorProcedure:
        return cls(
            procedure_id=str(raw["procedure_id"]),
            script=str(raw["script"]),
            scope=str(raw["scope"]),
            requires_confirm=bool(raw.get("requires_confirm", False)),
            mutating=bool(raw.get("mutating", False)),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "procedure_id": self.procedure_id,
            "script": self.script,
            "scope": self.scope,
            "requires_confirm": self.requires_confirm,
            "mutating": self.mutating,
        }


@dataclass(frozen=True)
class OperatorRunbookManifest:
    schema: str
    manifest_hash: str
    authority_note: str
    runbook_doc: str
    break_glass_policy_doc: str
    ops_state_path: str
    emergency_receipts_path: str
    required_runbook_sections: tuple[str, ...]
    forbidden_bypass_phrases: tuple[str, ...]
    procedures: tuple[OperatorProcedure, ...]

    def by_id(self, procedure_id: str) -> OperatorProcedure | None:
        for item in self.procedures:
            if item.procedure_id == procedure_id:
                return item
        return None


def default_manifest_path(workspace: Path | None = None) -> Path:
    root = workspace or Path(__file__).resolve().parents[2]
    return root / "config" / "operator_runbook_manifest_v1.yaml"


def manifest_hash(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "manifest_hash"}
    raw = yaml.safe_dump(body, sort_keys=True, allow_unicode=True)
    return f"sha256:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


def load_manifest(path: Path | None = None, *, workspace: Path | None = None) -> OperatorRunbookManifest:
    manifest_path = path or default_manifest_path(workspace)
    if not manifest_path.exists():
        raise FileNotFoundError(f"operator runbook manifest missing: {manifest_path}")
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    schema = str(payload.get("schema", ""))
    if schema != "operator_runbook_manifest_v1":
        raise ValueError(f"unsupported manifest schema: {schema}")
    expected = payload.get("manifest_hash")
    computed = manifest_hash(payload)
    if expected and expected != computed:
        raise ValueError(f"manifest hash mismatch: expected {expected}, got {computed}")
    procedures = tuple(OperatorProcedure.from_dict(item) for item in payload.get("procedures", ()))
    found = {p.procedure_id for p in procedures}
    missing = [pid for pid in REQUIRED_PROCEDURES if pid not in found]
    if missing:
        raise ValueError(f"missing required procedures: {missing}")
    return OperatorRunbookManifest(
        schema=schema,
        manifest_hash=computed,
        authority_note=str(payload.get("authority_note", "")),
        runbook_doc=str(payload.get("runbook_doc", "")),
        break_glass_policy_doc=str(payload.get("break_glass_policy_doc", "")),
        ops_state_path=str(payload.get("ops_state_path", "runtime/ops/ops_state_v1.json")),
        emergency_receipts_path=str(
            payload.get("emergency_receipts_path", "runtime/ops/emergency_receipts.jsonl")
        ),
        required_runbook_sections=tuple(str(x) for x in payload.get("required_runbook_sections", ())),
        forbidden_bypass_phrases=tuple(str(x) for x in payload.get("forbidden_bypass_phrases", ())),
        procedures=procedures,
    )


__all__ = [
    "OperatorProcedure",
    "OperatorRunbookManifest",
    "REQUIRED_PROCEDURES",
    "default_manifest_path",
    "load_manifest",
    "manifest_hash",
]
