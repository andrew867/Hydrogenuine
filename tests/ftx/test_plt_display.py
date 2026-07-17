"""CT-05 PLT display fence tests."""

from __future__ import annotations

import pytest

from hg_core.failures.plt_display import format_failure_summary, state_color
from hg_core.failures.registry import clear_registry_cache


@pytest.fixture(autouse=True)
def _reset() -> None:
    clear_registry_cache()


def test_ftx_neg1_unknown_state_color() -> None:
    assert state_color("not_a_real_state") == "unknown"


def test_plt_display_label_from_registry() -> None:
    summary = format_failure_summary("git_push_forbidden")
    assert summary["reason_code"] == "ter.refused.git_push_forbidden"
    assert summary["state"] == "refused"
    assert "Git push" in summary["display_label"]
