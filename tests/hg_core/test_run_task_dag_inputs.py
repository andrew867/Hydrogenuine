"""Tests for run_task DAG inputs and memory_profile propagation."""

import json
import os
import sys
import pytest

from hg_core.run_task import _read_dag_inputs


def test_read_dag_inputs_from_env(monkeypatch):
    """_read_dag_inputs reads HG_DAG_INPUTS from env when set."""
    monkeypatch.setenv("HG_DAG_INPUTS", json.dumps({"payload": "from_env", "topic": "memory"}))
    # Ensure --inputs is not in argv so we use env
    argv = [sys.argv[0], "some-task"]
    monkeypatch.setattr(sys, "argv", argv)
    result = _read_dag_inputs()
    assert result == {"payload": "from_env", "topic": "memory"}


def test_read_dag_inputs_from_file(tmp_path, monkeypatch):
    """_read_dag_inputs reads from --inputs file when path exists and takes precedence over env."""
    inputs_file = tmp_path / "inputs.json"
    inputs_file.write_text(json.dumps({"from": "file", "key": "value"}), encoding="utf-8")
    monkeypatch.setenv("HG_DAG_INPUTS", json.dumps({"from": "env"}))
    argv = [sys.argv[0], "some-task", "--inputs", str(inputs_file)]
    monkeypatch.setattr(sys, "argv", argv)
    result = _read_dag_inputs()
    assert result == {"from": "file", "key": "value"}


def test_read_dag_inputs_empty_when_no_env_or_file(monkeypatch):
    """_read_dag_inputs returns {} when HG_DAG_INPUTS is unset and no --inputs file."""
    monkeypatch.delenv("HG_DAG_INPUTS", raising=False)
    argv = [sys.argv[0], "some-task"]
    monkeypatch.setattr(sys, "argv", argv)
    result = _read_dag_inputs()
    assert result == {}
