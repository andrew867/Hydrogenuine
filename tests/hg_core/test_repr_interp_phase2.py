"""
Tests for Layer 8 Phase 2: integration with executor/Ch3 (opt-in capture).
"""
import os
from pathlib import Path

import pytest

from hg_core.repr_interp import (
    is_repr_interp_capture_enabled,
    capture_context,
    read_captured_contexts,
)


def test_capture_disabled_by_default(tmp_path: Path) -> None:
    assert is_repr_interp_capture_enabled(tmp_path) is False


def test_capture_enabled_via_run_config(tmp_path: Path) -> None:
    assert is_repr_interp_capture_enabled(tmp_path, {"repr_interp_capture": True}) is True
    assert is_repr_interp_capture_enabled(tmp_path, {"repr_interp_capture": False}) is False


def test_capture_enabled_via_env(tmp_path: Path) -> None:
    orig = os.environ.get("REPR_INTERP_CAPTURE")
    try:
        os.environ["REPR_INTERP_CAPTURE"] = "1"
        assert is_repr_interp_capture_enabled(tmp_path) is True
        os.environ["REPR_INTERP_CAPTURE"] = "0"
        assert is_repr_interp_capture_enabled(tmp_path) is False
    finally:
        if orig is not None:
            os.environ["REPR_INTERP_CAPTURE"] = orig
        else:
            os.environ.pop("REPR_INTERP_CAPTURE", None)


def test_capture_context_when_disabled_does_not_write(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    capture_context(tmp_path, "run-1", run_dir, "n1", "agent", context_ref={"run_id": "run-1"})
    assert read_captured_contexts(run_dir) == []


def test_capture_context_when_enabled_writes_and_read_back(tmp_path: Path) -> None:
    orig = os.environ.get("REPR_INTERP_CAPTURE")
    try:
        os.environ["REPR_INTERP_CAPTURE"] = "1"
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        capture_context(
            tmp_path,
            "run-1",
            run_dir,
            "node-1",
            "agent",
            context_ref={"run_id": "run-1", "graph_id": "g1"},
        )
        records = read_captured_contexts(run_dir)
        assert len(records) == 1
        assert records[0]["run_id"] == "run-1"
        assert records[0]["node_id"] == "node-1"
        assert records[0]["node_type"] == "agent"
        assert records[0]["context_ref"]["graph_id"] == "g1"
    finally:
        if orig is not None:
            os.environ["REPR_INTERP_CAPTURE"] = orig
        else:
            os.environ.pop("REPR_INTERP_CAPTURE", None)


def test_read_captured_contexts_empty_dir(tmp_path: Path) -> None:
    assert read_captured_contexts(tmp_path) == []


def test_capture_context_append_multiple(tmp_path: Path) -> None:
    orig = os.environ.get("REPR_INTERP_CAPTURE")
    try:
        os.environ["REPR_INTERP_CAPTURE"] = "1"
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        capture_context(tmp_path, "r1", run_dir, "n1", "agent", context_ref={})
        capture_context(tmp_path, "r1", run_dir, "n2", "tool", context_ref={})
        records = read_captured_contexts(run_dir)
        assert len(records) == 2
        assert records[0]["node_id"] == "n1"
        assert records[1]["node_id"] == "n2"
    finally:
        if orig is not None:
            os.environ["REPR_INTERP_CAPTURE"] = orig
        else:
            os.environ.pop("REPR_INTERP_CAPTURE", None)


def test_executor_capture_hook_callable(tmp_path: Path) -> None:
    """Executor _repr_interp_capture_after_node is wired and callable (no-op when disabled)."""
    from hg_core.task_graph.executor import _repr_interp_capture_after_node

    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    _repr_interp_capture_after_node(
        tmp_path,
        "run-1",
        run_dir,
        {"run_config": {}},
        "node-1",
        "agent",
        "graph-1",
    )
    assert read_captured_contexts(run_dir) == []
