"""Bridge manifest gate validation (CT-08 BRG)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.product_bridge.manifest import (
    CITATION_RE,
    INTEGRATED_CLAIMS,
    NON_INTEGRATED_STATUSES,
    ProductOrganismBridgeManifest,
    load_manifest,
)


@dataclass(frozen=True)
class ValidationFinding:
    check: str
    verdict: str
    detail: str
    surface_id: str | None = None
    card_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "check": self.check,
            "verdict": self.verdict,
            "detail": self.detail,
        }
        if self.surface_id:
            payload["surface_id"] = self.surface_id
        if self.card_id:
            payload["card_id"] = self.card_id
        return payload


def _evidence_ok(workspace: Path, evidence_path: str, evidence_status: str) -> tuple[bool, str]:
    if evidence_status in {"UNKNOWN", "DEFERRED"}:
        return True, f"explicit {evidence_status}"
    if not evidence_path:
        return False, "missing evidence_path"
    target = workspace / evidence_path
    if target.exists():
        return True, str(target.relative_to(workspace))
    return False, f"evidence path not found: {evidence_path}"


def _source_refs_exist(workspace: Path, refs: tuple[str, ...]) -> tuple[bool, str]:
    missing = [ref for ref in refs if not (workspace / ref).exists()]
    if missing:
        return False, f"missing source refs: {missing}"
    return True, "ok"


def _gate_refs_exist(workspace: Path, refs: tuple[str, ...]) -> tuple[bool, str]:
    missing = [ref for ref in refs if not (workspace / ref).exists()]
    if missing:
        return False, f"missing gate refs: {missing}"
    return True, "ok"


def validate_manifest(
    manifest: ProductOrganismBridgeManifest | None = None,
    *,
    workspace: Path | None = None,
) -> list[ValidationFinding]:
    root = workspace or Path(__file__).resolve().parents[2]
    findings: list[ValidationFinding] = []
    try:
        loaded = manifest or load_manifest(workspace=root)
    except (FileNotFoundError, ValueError) as exc:
        findings.append(
            ValidationFinding(
                check="bridge_manifest_schema",
                verdict="fail",
                detail=str(exc),
            )
        )
        return findings

    findings.append(
        ValidationFinding(
            check="bridge_manifest_schema",
            verdict="pass",
            detail=f"schema={loaded.schema} surfaces={len(loaded.surfaces)} cards={len(loaded.capability_cards)}",
        )
    )

    covered = {s.organism_subsystem for s in loaded.surfaces}
    for subsystem in loaded.organism_subsystems:
        if subsystem not in covered:
            findings.append(
                ValidationFinding(
                    check="organism_subsystem_coverage",
                    verdict="fail",
                    detail=f"no surface maps organism subsystem {subsystem}",
                )
            )

    for surface in loaded.surfaces:
        ok, detail = _evidence_ok(root, surface.evidence_path, surface.evidence_status)
        findings.append(
            ValidationFinding(
                check="surface_evidence",
                verdict="pass" if ok else "fail",
                detail=detail,
                surface_id=surface.surface_id,
            )
        )
        if surface.status in NON_INTEGRATED_STATUSES and surface.integration_claim in INTEGRATED_CLAIMS:
            findings.append(
                ValidationFinding(
                    check="stub_not_integrated",
                    verdict="fail",
                    detail=f"status={surface.status} integration_claim={surface.integration_claim}",
                    surface_id=surface.surface_id,
                )
            )
        else:
            findings.append(
                ValidationFinding(
                    check="stub_not_integrated",
                    verdict="pass",
                    detail=f"status={surface.status} integration_claim={surface.integration_claim}",
                    surface_id=surface.surface_id,
                )
            )
        if surface.demo_only and surface.integration_claim == "integrated":
            findings.append(
                ValidationFinding(
                    check="demo_only_not_integrated",
                    verdict="fail",
                    detail="demo_only surface claims integrated without PAR parity",
                    surface_id=surface.surface_id,
                )
            )
        src_ok, src_detail = _source_refs_exist(root, surface.source_refs)
        findings.append(
            ValidationFinding(
                check="surface_source_refs",
                verdict="pass" if src_ok else "fail",
                detail=src_detail,
                surface_id=surface.surface_id,
            )
        )
        if surface.gate_refs:
            gate_ok, gate_detail = _gate_refs_exist(root, surface.gate_refs)
            findings.append(
                ValidationFinding(
                    check="surface_gate_refs",
                    verdict="pass" if gate_ok else "fail",
                    detail=gate_detail,
                    surface_id=surface.surface_id,
                )
            )

    for card in loaded.capability_cards:
        src_ok, src_detail = _source_refs_exist(root, card.source_refs)
        findings.append(
            ValidationFinding(
                check="card_source_refs",
                verdict="pass" if src_ok else "fail",
                detail=src_detail,
                card_id=card.card_id,
            )
        )
        ok, detail = _evidence_ok(root, card.evidence_path, card.evidence_status)
        findings.append(
            ValidationFinding(
                check="card_evidence",
                verdict="pass" if ok else "fail",
                detail=detail,
                card_id=card.card_id,
            )
        )
        if not CITATION_RE.search(card.product_claim):
            findings.append(
                ValidationFinding(
                    check="product_claim_citation",
                    verdict="fail",
                    detail="product_claim must cite proof bundle, test, or report",
                    card_id=card.card_id,
                )
            )
        else:
            findings.append(
                ValidationFinding(
                    check="product_claim_citation",
                    verdict="pass",
                    detail="citation present",
                    card_id=card.card_id,
                )
            )
        if card.status in NON_INTEGRATED_STATUSES and card.integration_claim in INTEGRATED_CLAIMS:
            findings.append(
                ValidationFinding(
                    check="fake_green_claim",
                    verdict="fail",
                    detail=f"status={card.status} integration_claim={card.integration_claim}",
                    card_id=card.card_id,
                )
            )
        else:
            findings.append(
                ValidationFinding(
                    check="fake_green_claim",
                    verdict="pass",
                    detail=f"status={card.status}",
                    card_id=card.card_id,
                )
            )

    return findings


def findings_ok(findings: list[ValidationFinding]) -> bool:
    return all(f.verdict == "pass" for f in findings)


__all__ = ["ValidationFinding", "findings_ok", "validate_manifest"]
