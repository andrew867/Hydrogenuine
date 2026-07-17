"""EOG fake embodiment growth queue — slice 3, no live dispatch."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hg_core.embodiment_oea_cluster.errors import EOG_FAKE_QUEUE_ENQUEUED
from hg_core.embodiment_oea_cluster.no_authority import advisory_only_marker
from hg_runtime.embodiment_oea_growth.fixtures import load_fixture_bundles
from hg_runtime.embodiment_oea_growth.router import route_growth_bundle
from hg_runtime.embodiment_oea_growth.types import FIXTURE_CLOCK


@dataclass
class FakeEmbodimentGrowthQueue:
    queue_id: str = "eog-fake-queue"
    entries: list[dict[str, Any]] = field(default_factory=list)

    def enqueue_bundle(self, bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
        routed = route_growth_bundle(bundle, observed_at=observed_at)
        entry = {
            "bundle_id": bundle.get("bundle_id"),
            "status": routed.get("status"),
            "fake_queue_only": True,
            "permission_granted": False,
            "external_action_taken": False,
        }
        self.entries.append(entry)
        return entry

    def depth(self) -> int:
        return len(self.entries)


def enqueue_fixture_queue(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    queue = FakeEmbodimentGrowthQueue()
    bundles = load_fixture_bundles()
    for bundle in bundles[:3]:
        queue.enqueue_bundle(bundle, observed_at=observed_at)
    return {
        **advisory_only_marker(),
        "status": "enqueued",
        "reason_code": EOG_FAKE_QUEUE_ENQUEUED,
        "fake_queue_only": True,
        "queue_depth": queue.depth(),
        "entries": queue.entries,
        "live_dispatch": False,
        "permission_granted": False,
    }


__all__ = ["FakeEmbodimentGrowthQueue", "enqueue_fixture_queue"]
