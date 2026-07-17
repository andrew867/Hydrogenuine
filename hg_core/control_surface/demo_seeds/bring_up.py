"""
One-command demo bring-up: generate seed, replay into ledger, run materializers, seed entity registry.
Run from repo root: python -m hg_core.control_surface.demo_seeds.bring_up [workspace_root]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _get_workspace_root() -> Path:
    try:
        from hg_lib.config import get_workspace_root
        return Path(get_workspace_root())
    except ImportError:
        return Path(".").resolve()


def _seed_entity_registry(workspace_root: Path) -> None:
    """Write demo entity registry (8 entities across swarm_alpha, swarm_beta) so get_entities shows them."""
    overseer = Path(workspace_root) / "memory" / "overseer"
    overseer.mkdir(parents=True, exist_ok=True)
    entities = [
        {"id": "ent_overseer_alpha", "role": "overseer", "group_id": "swarm_alpha", "status": "active", "autonomy_level": "normal"},
        {"id": "ent_planner_alpha", "role": "planner", "group_id": "swarm_alpha", "status": "active", "autonomy_level": "normal"},
        {"id": "ent_exec_alpha", "role": "executor", "group_id": "swarm_alpha", "status": "active", "autonomy_level": "normal"},
        {"id": "ent_ver_alpha", "role": "verifier", "group_id": "swarm_alpha", "status": "active", "autonomy_level": "normal"},
        {"id": "ent_auditor_beta", "role": "auditor", "group_id": "swarm_beta", "status": "active", "autonomy_level": "normal"},
        {"id": "ent_planner_beta", "role": "planner", "group_id": "swarm_beta", "status": "active", "autonomy_level": "normal"},
        {"id": "ent_exec_beta", "role": "executor", "group_id": "swarm_beta", "status": "active", "autonomy_level": "normal"},
        {"id": "ent_ver_beta", "role": "verifier", "group_id": "swarm_beta", "status": "active", "autonomy_level": "normal"},
    ]
    reg = {"entities": entities}
    (overseer / "entity_registry.json").write_text(json.dumps(reg, indent=2), encoding="utf-8")


def main(workspace_root: Path, seed: int = 1337) -> int:
    workspace_root = Path(workspace_root)
    workspace_root.mkdir(parents=True, exist_ok=True)
    out_dir = workspace_root / "memory" / "demo_seeds"
    out_dir.mkdir(parents=True, exist_ok=True)

    from hg_core.control_surface.demo_seeds.seed_generator import generate_seed
    from hg_core.control_surface.demo_seeds.replay import replay_seed_into_ledger
    from hg_core.materializers import run_all

    print("Generating demo seed (deterministic)...")
    summary = generate_seed(str(out_dir), seed=seed)
    print("  events:", summary["events_count"], "  checkpoints:", summary["checkpoints_count"])

    print("Replaying seed into ledger...")
    appended = replay_seed_into_ledger(out_dir / "seed_events.jsonl", workspace_root)
    print("  appended", len(appended), "events")

    print("Running materializers...")
    run_all(workspace_root, rebuild=True)
    print("  materializers done.")

    print("Seeding entity registry (8 entities, 2 swarms)...")
    _seed_entity_registry(workspace_root)
    print("  entity_registry.json written.")

    print("")
    print("Demo bring-up complete.")
    print("  Ledger scope files: memory/ledger/scopes/run/")
    print("  Materialized: memory/materialized/work_items.jsonl, incidents.jsonl, etc.")
    print("  Guided tour: .cursor/plans/controlsurface/control_surface_pack2_reference_deployments_demo_seeds/DEMO_TOUR/00_guided_tour.md")
    print("  Open UI at http://localhost:3000 when API/UI are running (e.g. docker-compose up).")
    return 0


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else _get_workspace_root()
    sys.exit(main(root))
