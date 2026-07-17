"""PLT read-path status cross-check against backend classifier (CT-08 BRG)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_plt.classifier import classify_subsystems
from hg_core.product_bridge.manifest import ProductOrganismBridgeManifest, load_manifest


@dataclass(frozen=True)
class PltCrosscheckResult:
    plt_subsystem_key: str
    manifest_status: str
    backend_status: str
    match: bool

    def to_payload(self) -> dict[str, Any]:
        return {
            "plt_subsystem_key": self.plt_subsystem_key,
            "manifest_status": self.manifest_status,
            "backend_status": self.backend_status,
            "match": self.match,
        }


def crosscheck_plt_statuses(
    manifest: ProductOrganismBridgeManifest | None = None,
    *,
    workspace: Path | None = None,
    replay_ok: bool = True,
) -> list[PltCrosscheckResult]:
    root = workspace or Path(__file__).resolve().parents[2]
    loaded = manifest or load_manifest(workspace=root)
    backend = {s.subsystem: s.status for s in classify_subsystems(replay_ok=replay_ok)}
    results: list[PltCrosscheckResult] = []
    seen: set[str] = set()
    for surface in loaded.surfaces:
        key = surface.plt_subsystem_key
        if not key or key in seen:
            continue
        seen.add(key)
        backend_status = backend.get(key)
        if backend_status is None:
            results.append(
                PltCrosscheckResult(
                    plt_subsystem_key=key,
                    manifest_status=surface.status,
                    backend_status="MISSING",
                    match=False,
                )
            )
            continue
        results.append(
            PltCrosscheckResult(
                plt_subsystem_key=key,
                manifest_status=surface.status,
                backend_status=backend_status,
                match=surface.status == backend_status,
            )
        )
    return results


def plt_crosscheck_ok(results: list[PltCrosscheckResult]) -> bool:
    return bool(results) and all(r.match for r in results)


__all__ = ["PltCrosscheckResult", "crosscheck_plt_statuses", "plt_crosscheck_ok"]
