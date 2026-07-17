from __future__ import annotations

import json
from pathlib import Path

from hg_core.metacognition import write_reflection_artifact
from hg_gateway.artifact_registry import ARTIFACT_CLASS_DEFINITIONS, get_artifact_registry_entry, list_artifact_inventory
from hg_gateway.db import get_connection


def test_reflection_artifact_store_persists_typed_payload(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "memory").mkdir(parents=True, exist_ok=True)

    out = write_reflection_artifact(
        workspace,
        "reflection:entity:phase4:001",
        {
            "summary": "Phase 4 is ready for review.",
            "findings_json": {"summary": "Phase 4 is ready for review."},
            "source_links": [{"kind": "run", "href": "#/runs/run-social-1", "label": "run-social-1"}],
        },
        source_event_ids=["evt-1"],
        source_memory_ids=["mem-1"],
        confidence=0.75,
        verification_status="provisional",
        reviewed_by="operator",
        promoted_at=None,
        title="Operator phase 4 reflection",
        change_summary="seed reflection artifact",
    )

    db_path = workspace / "memory" / "gateway.sqlite3"
    with get_connection(str(db_path)) as conn:
        entry = get_artifact_registry_entry(conn, "reflection:entity:phase4:001")
        assert entry is not None
        assert entry["class_key"] == "reflection"
        assert entry["latest_status"] == "provisional"
        assert entry["payload_json"]
        payload = json.loads(entry["payload_json"])
        assert payload["confidence"] == 0.75
        assert payload["source_event_ids"] == ["evt-1"]
        assert payload["source_memory_ids"] == ["mem-1"]
        assert payload["source_links"][0]["href"] == "#/runs/run-social-1"
        assert len(entry["versions"]) == 1

        inventory = list_artifact_inventory(conn, "reflection")
        assert len(inventory) == 1
        assert inventory[0]["artifact_id"] == "reflection:entity:phase4:001"

    assert out["artifact_id"] == "reflection:entity:phase4:001"
    assert any(defn.class_key == "reflection" for defn in ARTIFACT_CLASS_DEFINITIONS)
