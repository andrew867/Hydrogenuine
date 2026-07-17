"""Model roster — builds local model roster from discovery + classification.

No hard allowlist. All discovered models are candidates.
Model availability is not permission.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

from hg_runtime.model_selection.lmstudio_discovery import discover_models, DiscoveryResult
from hg_runtime.model_selection.model_classifier import classify_all, ModelClassification


@dataclass
class ModelRoster:
    models: list[ModelClassification] = field(default_factory=list)
    discovery: DiscoveryResult | None = None
    avoid_models: list[str] = field(default_factory=list)
    prefer_models: list[str] = field(default_factory=list)
    resource_risk_ceiling: str = "medium"

    def available_for_inference(self) -> list[ModelClassification]:
        return [m for m in self.models if not m.is_embedding
                and m.model_id not in self.avoid_models]

    def within_risk_ceiling(self) -> list[ModelClassification]:
        risk_order = {"low": 0, "medium": 1, "high": 2, "unknown": 1}
        ceiling = risk_order.get(self.resource_risk_ceiling, 1)
        return [m for m in self.available_for_inference()
                if risk_order.get(m.resource_risk, 1) <= ceiling]

    def for_role(self, role: str) -> list[ModelClassification]:
        candidates = self.within_risk_ceiling()
        matching = [m for m in candidates if role in m.role_hints]
        return matching if matching else candidates

    def to_dict(self) -> dict:
        return {
            "total_discovered": len(self.models),
            "available_for_inference": len(self.available_for_inference()),
            "within_risk_ceiling": len(self.within_risk_ceiling()),
            "avoid_models": self.avoid_models,
            "prefer_models": self.prefer_models,
            "resource_risk_ceiling": self.resource_risk_ceiling,
            "models": [m.to_dict() for m in self.models],
            "no_hard_allowlist": True,
            "model_availability_is_not_permission": True,
            "promotion_allowed": False,
        }


def build_roster(
    endpoint: str,
    *,
    avoid_models: list[str] | None = None,
    prefer_models: list[str] | None = None,
    resource_risk_ceiling: str = "medium",
    timeout: int = 10,
) -> ModelRoster:
    discovery = discover_models(endpoint, timeout=timeout)
    classifications = classify_all(discovery.models)

    return ModelRoster(
        models=classifications,
        discovery=discovery,
        avoid_models=avoid_models or [],
        prefer_models=prefer_models or [],
        resource_risk_ceiling=resource_risk_ceiling,
    )


def write_roster_report(roster: ModelRoster, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "model_roster_report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(roster.to_dict(), f, indent=2)
    return path
