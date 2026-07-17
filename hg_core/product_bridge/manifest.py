"""Product↔organism bridge manifest loader (CT-08 BRG)."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_ORGANISM_SUBSYSTEMS = (
    "PLT",
    "Agent #0",
    "RTC",
    "SRP",
    "OEA",
    "TER",
    "MEL",
    "DEP",
)

ALLOWED_SURFACE_STATUSES = frozenset(
    {
        "REAL",
        "SCAFFOLD",
        "STUB",
        "GATED",
        "DISABLED",
        "DEMO_ONLY",
        "DEFERRED",
        "UNKNOWN",
        "FUTURE_PHASE",
        "DEGRADED",
        "FAILED",
    }
)

ALLOWED_INTEGRATION_CLAIMS = frozenset(
    {
        "integrated",
        "demo_only",
        "scaffolded",
        "stub",
        "not_wired",
        "gated",
        "deferred",
    }
)

ALLOWED_EVIDENCE_STATUSES = frozenset({"present", "UNKNOWN", "DEFERRED"})

INTEGRATED_CLAIMS = frozenset({"integrated", "gated"})

NON_INTEGRATED_STATUSES = frozenset(
    {"STUB", "SCAFFOLD", "DISABLED", "FUTURE_PHASE", "DEMO_ONLY", "DEFERRED", "UNKNOWN"}
)

CITATION_RE = re.compile(
    r"(docs/proofs/|tests/|docs/reports/|scripts/evals/)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CapabilityCard:
    card_id: str
    title: str
    organism_subsystem: str
    status: str
    integration_claim: str
    source_refs: tuple[str, ...]
    gate_refs: tuple[str, ...]
    evidence_path: str
    evidence_status: str
    caveats: tuple[str, ...]
    product_claim: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> CapabilityCard:
        return cls(
            card_id=str(raw["card_id"]),
            title=str(raw["title"]),
            organism_subsystem=str(raw["organism_subsystem"]),
            status=str(raw["status"]),
            integration_claim=str(raw["integration_claim"]),
            source_refs=tuple(raw.get("source_refs", [])),
            gate_refs=tuple(raw.get("gate_refs", [])),
            evidence_path=str(raw.get("evidence_path", "")),
            evidence_status=str(raw.get("evidence_status", "UNKNOWN")),
            caveats=tuple(raw.get("caveats", [])),
            product_claim=str(raw.get("product_claim", "")),
        )


@dataclass(frozen=True)
class BridgeSurface:
    surface_id: str
    operator_name: str
    organism_subsystem: str
    organism_modules: tuple[str, ...]
    status: str
    integration_claim: str
    path_label: str
    demo_only: bool
    source_refs: tuple[str, ...]
    gate_refs: tuple[str, ...]
    evidence_path: str
    evidence_status: str
    plt_subsystem_key: str | None
    caveats: tuple[str, ...]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> BridgeSurface:
        return cls(
            surface_id=str(raw["surface_id"]),
            operator_name=str(raw["operator_name"]),
            organism_subsystem=str(raw["organism_subsystem"]),
            organism_modules=tuple(raw.get("organism_modules", [])),
            status=str(raw["status"]),
            integration_claim=str(raw["integration_claim"]),
            path_label=str(raw.get("path_label", "unknown")),
            demo_only=bool(raw.get("demo_only", False)),
            source_refs=tuple(raw.get("source_refs", [])),
            gate_refs=tuple(raw.get("gate_refs", [])),
            evidence_path=str(raw.get("evidence_path", "")),
            evidence_status=str(raw.get("evidence_status", "UNKNOWN")),
            plt_subsystem_key=raw.get("plt_subsystem_key"),
            caveats=tuple(raw.get("caveats", [])),
        )


@dataclass(frozen=True)
class ProductOrganismBridgeManifest:
    schema: str
    manifest_hash: str
    organism_subsystems: tuple[str, ...]
    surfaces: tuple[BridgeSurface, ...]
    capability_cards: tuple[CapabilityCard, ...]

    def surface_by_id(self, surface_id: str) -> BridgeSurface | None:
        for surface in self.surfaces:
            if surface.surface_id == surface_id:
                return surface
        return None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "manifest_hash": self.manifest_hash,
            "organism_subsystems": list(self.organism_subsystems),
            "surfaces": [
                {
                    "surface_id": s.surface_id,
                    "operator_name": s.operator_name,
                    "organism_subsystem": s.organism_subsystem,
                    "organism_modules": list(s.organism_modules),
                    "status": s.status,
                    "integration_claim": s.integration_claim,
                    "path_label": s.path_label,
                    "demo_only": s.demo_only,
                    "source_refs": list(s.source_refs),
                    "gate_refs": list(s.gate_refs),
                    "evidence_path": s.evidence_path,
                    "evidence_status": s.evidence_status,
                    "plt_subsystem_key": s.plt_subsystem_key,
                    "caveats": list(s.caveats),
                }
                for s in self.surfaces
            ],
            "capability_cards": [
                {
                    "card_id": c.card_id,
                    "title": c.title,
                    "organism_subsystem": c.organism_subsystem,
                    "status": c.status,
                    "integration_claim": c.integration_claim,
                    "source_refs": list(c.source_refs),
                    "gate_refs": list(c.gate_refs),
                    "evidence_path": c.evidence_path,
                    "evidence_status": c.evidence_status,
                    "caveats": list(c.caveats),
                    "product_claim": c.product_claim,
                }
                for c in self.capability_cards
            ],
        }


def default_manifest_path(workspace: Path | None = None) -> Path:
    root = workspace or Path(__file__).resolve().parents[2]
    return root / "config" / "product_organism_bridge_manifest_v1.json"


def manifest_hash(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "manifest_hash"}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


def _validate_surface_raw(raw: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("surface_id", "operator_name", "organism_subsystem", "status", "integration_claim"):
        if field not in raw:
            errors.append(f"missing field: {field}")
    status = str(raw.get("status", ""))
    if status and status not in ALLOWED_SURFACE_STATUSES:
        errors.append(f"invalid status: {status}")
    claim = str(raw.get("integration_claim", ""))
    if claim and claim not in ALLOWED_INTEGRATION_CLAIMS:
        errors.append(f"invalid integration_claim: {claim}")
    evidence_status = str(raw.get("evidence_status", "UNKNOWN"))
    if evidence_status not in ALLOWED_EVIDENCE_STATUSES:
        errors.append(f"invalid evidence_status: {evidence_status}")
    if status in NON_INTEGRATED_STATUSES and claim in INTEGRATED_CLAIMS:
        errors.append(f"stub/scaffold surface cannot claim integrated: {raw.get('surface_id')}")
    if raw.get("demo_only") and claim == "integrated" and not raw.get("parity_proven"):
        errors.append(f"demo_only surface cannot claim integrated without parity_proven: {raw.get('surface_id')}")
    return errors


def _validate_card_raw(raw: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("card_id", "title", "organism_subsystem", "status", "integration_claim", "product_claim"):
        if field not in raw:
            errors.append(f"missing field: {field}")
    status = str(raw.get("status", ""))
    claim = str(raw.get("integration_claim", ""))
    if status in NON_INTEGRATED_STATUSES and claim in INTEGRATED_CLAIMS:
        errors.append(f"capability card cannot claim integrated for status {status}: {raw.get('card_id')}")
    product_claim = str(raw.get("product_claim", ""))
    if product_claim and not CITATION_RE.search(product_claim):
        errors.append(f"product_claim missing citation: {raw.get('card_id')}")
    return errors


def load_manifest(path: Path | None = None, *, workspace: Path | None = None) -> ProductOrganismBridgeManifest:
    manifest_path = path or default_manifest_path(workspace)
    if not manifest_path.exists():
        raise FileNotFoundError(f"bridge manifest missing: {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema = str(payload.get("schema", ""))
    if schema != "product_organism_bridge_manifest_v1":
        raise ValueError(f"unsupported schema: {schema}")
    expected = payload.get("manifest_hash")
    computed = manifest_hash(payload)
    if expected and expected != computed:
        raise ValueError(f"manifest hash mismatch: expected {expected}, got {computed}")
    organism = tuple(payload.get("organism_subsystems", []))
    missing = [name for name in REQUIRED_ORGANISM_SUBSYSTEMS if name not in organism]
    if missing:
        raise ValueError(f"manifest missing organism subsystems: {missing}")
    surfaces_raw = payload.get("surfaces", [])
    if not surfaces_raw:
        raise ValueError("manifest surfaces empty")
    schema_errors: list[str] = []
    surfaces: list[BridgeSurface] = []
    for raw in surfaces_raw:
        schema_errors.extend(_validate_surface_raw(raw))
        surfaces.append(BridgeSurface.from_dict(raw))
    cards_raw = payload.get("capability_cards", [])
    if not cards_raw:
        raise ValueError("manifest capability_cards empty")
    cards: list[CapabilityCard] = []
    for raw in cards_raw:
        schema_errors.extend(_validate_card_raw(raw))
        cards.append(CapabilityCard.from_dict(raw))
    if schema_errors:
        raise ValueError("; ".join(schema_errors))
    return ProductOrganismBridgeManifest(
        schema=schema,
        manifest_hash=computed,
        organism_subsystems=organism,
        surfaces=tuple(surfaces),
        capability_cards=tuple(cards),
    )


__all__ = [
    "ALLOWED_EVIDENCE_STATUSES",
    "ALLOWED_INTEGRATION_CLAIMS",
    "ALLOWED_SURFACE_STATUSES",
    "BridgeSurface",
    "CapabilityCard",
    "CITATION_RE",
    "INTEGRATED_CLAIMS",
    "NON_INTEGRATED_STATUSES",
    "ProductOrganismBridgeManifest",
    "REQUIRED_ORGANISM_SUBSYSTEMS",
    "default_manifest_path",
    "load_manifest",
    "manifest_hash",
]
