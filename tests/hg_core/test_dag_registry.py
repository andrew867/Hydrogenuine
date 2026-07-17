"""Tests for DAG registry: get_dag_path first-run and edge-case behavior."""

from pathlib import Path

import pytest

from hg_core.task_graph.dag_registry import DAG_REGISTRY_PATH, get_dag_path


def test_get_dag_path_missing_file_returns_none(tmp_path: Path):
    """When registry file does not exist, get_dag_path returns None."""
    root = tmp_path
    assert (root / DAG_REGISTRY_PATH).exists() is False
    assert get_dag_path("any-task", workspace_root=root) is None


def test_get_dag_path_invalid_json_returns_none(tmp_path: Path):
    """When registry file contains invalid JSON, get_dag_path returns None."""
    root = tmp_path
    registry_file = root / DAG_REGISTRY_PATH
    registry_file.parent.mkdir(parents=True, exist_ok=True)
    registry_file.write_text("not valid json {", encoding="utf-8")
    assert get_dag_path("any-task", workspace_root=root) is None


def test_get_dag_path_valid_existing_path_returns_path(tmp_path: Path):
    """When registry is valid and mapped path exists, get_dag_path returns that Path."""
    root = tmp_path
    registry_file = root / DAG_REGISTRY_PATH
    registry_file.parent.mkdir(parents=True, exist_ok=True)
    dag_path = root / "memory" / "automation" / "dags" / "my_dag.json"
    dag_path.parent.mkdir(parents=True, exist_ok=True)
    dag_path.write_text("{}", encoding="utf-8")
    registry_file.write_text(
        '{"my-task": "memory/automation/dags/my_dag.json"}',
        encoding="utf-8",
    )
    result = get_dag_path("my-task", workspace_root=root)
    assert result is not None
    assert result == dag_path
    assert result.exists()


def test_get_dag_path_valid_missing_path_returns_none(tmp_path: Path):
    """When registry is valid but mapped path does not exist, get_dag_path returns None."""
    root = tmp_path
    registry_file = root / DAG_REGISTRY_PATH
    registry_file.parent.mkdir(parents=True, exist_ok=True)
    registry_file.write_text(
        '{"my-task": "memory/automation/dags/nonexistent.json"}',
        encoding="utf-8",
    )
    assert (root / "memory" / "automation" / "dags" / "nonexistent.json").exists() is False
    assert get_dag_path("my-task", workspace_root=root) is None


def test_get_dag_path_task_not_in_registry_returns_none(tmp_path: Path):
    """When task_name is not in registry, get_dag_path returns None."""
    root = tmp_path
    registry_file = root / DAG_REGISTRY_PATH
    registry_file.parent.mkdir(parents=True, exist_ok=True)
    registry_file.write_text("{}", encoding="utf-8")
    assert get_dag_path("unknown-task", workspace_root=root) is None
