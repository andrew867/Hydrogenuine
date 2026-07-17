"""Default LLM provider/model resolution."""

import os
from pathlib import Path

import pytest


def test_default_provider_is_anthropic_without_env(monkeypatch):
    monkeypatch.delenv("HG_DEFAULT_PROVIDER", raising=False)
    monkeypatch.delenv("SAFE_LOCAL_ONLY", raising=False)
    from hg_gateway import llm_defaults

    assert llm_defaults.get_default_provider() == "anthropic"


def test_default_anthropic_model_is_haiku_without_env(monkeypatch):
    monkeypatch.delenv("HG_ANTHROPIC_MODEL", raising=False)
    monkeypatch.delenv("HG_DEFAULT_MODEL", raising=False)
    monkeypatch.delenv("SAFE_LOCAL_ONLY", raising=False)
    from hg_gateway import llm_defaults

    assert llm_defaults.get_default_model("anthropic") == "claude-haiku-4-5"


def test_dag_engage_model_follows_defaults(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.delenv("HG_DAG_ENGAGE_LLM_MODEL", raising=False)
    monkeypatch.delenv("HG_ANTHROPIC_MODEL", raising=False)
    monkeypatch.setenv("HG_DEFAULT_PROVIDER", "anthropic")
    from hg_core.task_graph.native_task_tools import _dag_engage_llm_model

    assert _dag_engage_llm_model() == "claude-haiku-4-5"
