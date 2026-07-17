"""EXCITON contract tests — schema only, no UI."""

from __future__ import annotations

import json
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
EXAMPLE = WORKSPACE / "configs" / "exciton" / "agent0_dev_boot_status.example.json"
SCHEMA = WORKSPACE / "configs" / "exciton" / "agent0_dev_boot_status.schema.json"
CONTRACT = WORKSPACE / "docs" / "planning" / "exciton_productization" / "EXCITON_AGENT0_DEV_BOOT_CONTRACT.md"


def test_example_status_no_permission() -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    assert data["permission_granted"] is False
    assert data["authority_created"] is False
    assert data["exciton_ui_implemented"] is False


def test_schema_and_contract_exist() -> None:
    assert SCHEMA.is_file()
    assert CONTRACT.is_file()
