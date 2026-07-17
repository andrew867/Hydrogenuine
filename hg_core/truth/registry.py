"""Truth gate registry loader and orphan detection (CT-04 OBT)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class GateEntry:
    gate_id: str
    script: str
    pack: str
    tier: str  # wave1 | runtime | subsystem | self
    critical: bool
    run_policy: str  # always | wave1 | deferred
    enabled: bool
    skip_reason: str | None = None

    @property
    def script_path(self) -> Path:
        return Path(self.script)

    def is_ct_required(self) -> bool:
        if self.gate_id in {"ct_crosspack", "ct_proof_command_log", "ct_v1_final_audit"}:
            return True
        return self.pack.startswith("CT-") and self.run_policy == "always"

    def should_run(self, *, fast: bool, include_all: bool, strict_ct: bool = False) -> bool:
        if not self.enabled:
            return False
        if self.gate_id == "ct_v1_final_audit":
            return False  # self-hosting final audit; invoked separately after OBT strict green
        if fast:
            return False  # fast mode: orphan check only; gates deferred
        if strict_ct:
            return self.is_ct_required()
        if include_all:
            return True
        if self.run_policy == "always":
            return True
        if self.run_policy == "wave1":
            return self.tier in {"wave1", "runtime"}
        return False


@dataclass(frozen=True)
class TruthGateRegistry:
    schema: str
    gates: tuple[GateEntry, ...]
    registry_path: Path
    registry_hash: str

    def gate_by_id(self, gate_id: str) -> GateEntry | None:
        for gate in self.gates:
            if gate.gate_id == gate_id:
                return gate
        return None

    def orphan_scripts(self, evals_dir: Path) -> list[str]:
        """Return gate script basenames on disk but absent from registry."""
        registered = {Path(g.script).name for g in self.gates}
        registered.add("hg_full_truth_gate.py")
        orphans: list[str] = []
        for path in sorted(evals_dir.glob("*_gate.py")):
            if path.name not in registered:
                orphans.append(path.name)
        return orphans

    def missing_scripts(self, workspace: Path) -> list[str]:
        missing: list[str] = []
        for gate in self.gates:
            if not (workspace / gate.script).is_file():
                missing.append(gate.script)
        return missing

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "registry_hash": self.registry_hash,
            "gates": [
                {
                    "gate_id": g.gate_id,
                    "script": g.script,
                    "pack": g.pack,
                    "tier": g.tier,
                    "critical": g.critical,
                    "run_policy": g.run_policy,
                    "enabled": g.enabled,
                    "skip_reason": g.skip_reason,
                }
                for g in self.gates
            ],
        }


def default_registry_path(workspace: Path | None = None) -> Path:
    root = workspace or Path(__file__).resolve().parents[2]
    return root / "config" / "truth_gate_registry.yaml"


def load_registry(path: Path | None = None) -> TruthGateRegistry:
    import hashlib

    registry_path = path or default_registry_path()
    raw = registry_path.read_bytes()
    registry_hash = f"sha256:{hashlib.sha256(raw).hexdigest()}"
    data = yaml.safe_load(raw)
    if not isinstance(data, dict) or "gates" not in data:
        raise ValueError(f"malformed truth gate registry: {registry_path}")
    gates: list[GateEntry] = []
    for item in data["gates"]:
        if not isinstance(item, dict):
            raise ValueError("gate entry must be a mapping")
        gates.append(
            GateEntry(
                gate_id=str(item["gate_id"]),
                script=str(item["script"]),
                pack=str(item.get("pack", "unknown")),
                tier=str(item.get("tier", "subsystem")),
                critical=bool(item.get("critical", False)),
                run_policy=str(item.get("run_policy", "deferred")),
                enabled=bool(item.get("enabled", True)),
                skip_reason=item.get("skip_reason"),
            )
        )
    return TruthGateRegistry(
        schema=str(data.get("schema", "truth_gate_registry_v1")),
        gates=tuple(gates),
        registry_path=registry_path,
        registry_hash=registry_hash,
    )


__all__ = ["GateEntry", "TruthGateRegistry", "default_registry_path", "load_registry"]
