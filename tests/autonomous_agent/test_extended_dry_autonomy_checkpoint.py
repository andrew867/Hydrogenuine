"""Extended dry autonomy checkpoint tests."""

from __future__ import annotations

import pytest

from hg_runtime.extended_dry_autonomy.checkpoint import load_checkpoint, resume_from_checkpoint, verify_checkpoint, write_checkpoint
from hg_runtime.extended_dry_autonomy.errors import ExtendedDryAutonomyCheckpointError
from hg_runtime.extended_dry_autonomy.schema import ExtendedDryAutonomyCheckpoint, now_iso
from hg_runtime.agent_zero_state.hashing import hash_record


@pytest.fixture
def env(monkeypatch, tmp_path):
    ext = tmp_path / "ext"
    turns = tmp_path / "turns"
    monkeypatch.setenv("HG_EXTENDED_DRY_AUTONOMY_ROOT", str(ext))
    monkeypatch.setenv("HG_AGENT_TURN_BASE", str(turns))
    return ext, turns


def test_checkpoint_writes_state_and_journal_hashes(env):
    ext, turns = env
    run_id = "ckpt-run"
    (ext / run_id).mkdir(parents=True)
    (ext / run_id / "state.json").write_text('{"iteration_count": 0}', encoding="utf-8")
    cp = write_checkpoint(
        run_id=run_id,
        iteration_index=0,
        turn_result_ref=None,
        heartbeat_hash=hash_record({"hb": 1}),
        extended_base=ext,
        turn_base=turns,
    )
    assert cp.state_hash
    assert cp.journal_head_hash
    assert cp.hash


def test_corrupted_checkpoint_is_red(env):
    ext, turns = env
    cp = ExtendedDryAutonomyCheckpoint(
        checkpoint_id="ckpt-bad",
        run_id="r",
        iteration_index=0,
        turn_result_ref=None,
        state_hash="bad",
        journal_head_hash="bad",
        review_queue_hash="x",
        artifact_manifest_hash="x",
        heartbeat_hash="x",
        created_at=now_iso(),
        hash="invalid",
    )
    ok, reason = verify_checkpoint(cp, extended_base=ext, turn_base=turns)
    assert not ok
    assert "RED_" in reason


def test_resume_without_valid_checkpoint_red(env):
    with pytest.raises(ExtendedDryAutonomyCheckpointError):
        resume_from_checkpoint(
            ExtendedDryAutonomyCheckpoint(
                checkpoint_id="x",
                run_id="missing",
                iteration_index=99,
                turn_result_ref=None,
                state_hash="a",
                journal_head_hash="b",
                review_queue_hash="c",
                artifact_manifest_hash="d",
                heartbeat_hash="e",
                created_at=now_iso(),
                hash="badhash",
            ),
            extended_base=env[0],
            turn_base=env[1],
        )


def test_load_latest_checkpoint(env):
    ext, turns = env
    run_id = "load-run"
    (ext / run_id).mkdir(parents=True)
    (ext / run_id / "state.json").write_text("{}", encoding="utf-8")
    write_checkpoint(
        run_id=run_id,
        iteration_index=1,
        turn_result_ref="ref",
        heartbeat_hash=hash_record({"hb": 2}),
        extended_base=ext,
        turn_base=turns,
    )
    loaded = load_checkpoint(run_id, extended_base=ext)
    assert loaded is not None
    assert loaded.iteration_index == 1
