"""Turn artifact storage for single-turn engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_state.reducer import persist_agent_state
from hg_runtime.agent_zero_state.state import AgentState
from hg_runtime.agent_zero_state.turn_journal import TurnJournal
from hg_runtime.agent_zero_state.turn_receipt import TurnReceipt
from hg_runtime.agent_turn_engine.schema import AgentTurnStorageRefs


def turns_root(*, base: Path | None = None) -> Path:
    root = base or Path(__file__).resolve().parents[2] / ".hg-local" / "agent_zero" / "turns"
    return root


def run_dir(run_id: str, *, base: Path | None = None) -> Path:
    return turns_root(base=base) / run_id


def agent_state_path(run_id: str, *, base: Path | None = None) -> Path:
    return run_dir(run_id, base=base) / "agent_state.json"


def journal_path(run_id: str, *, base: Path | None = None) -> Path:
    return run_dir(run_id, base=base) / "turn_journal.jsonl"


def observe_dir(run_id: str, *, base: Path | None = None) -> Path:
    return run_dir(run_id, base=base) / "observe_snapshots"


def capability_dir(run_id: str, *, base: Path | None = None) -> Path:
    return run_dir(run_id, base=base) / "capability_menus"


def reasoning_dir(run_id: str, *, base: Path | None = None) -> Path:
    return run_dir(run_id, base=base) / "reasoning"


def broker_dir(run_id: str, *, base: Path | None = None) -> Path:
    return run_dir(run_id, base=base) / "broker"


def dispatch_dir(run_id: str, *, base: Path | None = None) -> Path:
    return run_dir(run_id, base=base) / "dispatch"


def receipts_dir(run_id: str, *, base: Path | None = None) -> Path:
    return run_dir(run_id, base=base) / "receipts"


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def open_journal(run_id: str, *, base: Path | None = None) -> TurnJournal:
    return TurnJournal(journal_path(run_id, base=base))


def storage_refs_for_run(run_id: str, *, base: Path | None = None) -> AgentTurnStorageRefs:
    root = run_dir(run_id, base=base)
    return AgentTurnStorageRefs(
        agent_state_path=str(agent_state_path(run_id, base=base).relative_to(root.parent.parent.parent)),
        journal_path=str(journal_path(run_id, base=base).relative_to(root.parent.parent.parent)),
    )


def persist_turn_artifacts(
    *,
    run_id: str,
    state: AgentState,
    receipt: TurnReceipt,
    journal: TurnJournal,
    artifact_paths: dict[str, Path],
    base: Path | None = None,
    skip_journal_append: bool = False,
) -> AgentTurnStorageRefs:
    run_dir(run_id, base=base).mkdir(parents=True, exist_ok=True)
    if not skip_journal_append:
        journal.append(receipt)
        journal.verify_chain()
    from hg_runtime.agent_turn_engine.turn_storage import turns_root as _turns_root

    persist_agent_state(state, run_id, base=_turns_root(base=base))
    write_json(receipts_dir(run_id, base=base) / f"{receipt.receipt_id}.json", receipt.to_payload())
    refs = AgentTurnStorageRefs(
        agent_state_path=str(agent_state_path(run_id, base=base)),
        journal_path=str(journal_path(run_id, base=base)),
        observe_snapshot_path=str(artifact_paths.get("observe")) if artifact_paths.get("observe") else None,
        capability_menu_path=str(artifact_paths.get("menu")) if artifact_paths.get("menu") else None,
        reasoning_path=str(artifact_paths.get("reasoning")) if artifact_paths.get("reasoning") else None,
        broker_path=str(artifact_paths.get("broker")) if artifact_paths.get("broker") else None,
        dispatch_path=str(artifact_paths.get("dispatch")) if artifact_paths.get("dispatch") else None,
        receipt_path=str(receipts_dir(run_id, base=base) / f"{receipt.receipt_id}.json"),
    )
    return refs


__all__ = [
    "agent_state_path",
    "broker_dir",
    "capability_dir",
    "dispatch_dir",
    "journal_path",
    "observe_dir",
    "open_journal",
    "persist_turn_artifacts",
    "reasoning_dir",
    "receipts_dir",
    "run_dir",
    "storage_refs_for_run",
    "turns_root",
    "write_json",
]
