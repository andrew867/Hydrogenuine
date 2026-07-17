"""CT-01 IAM registry tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from hg_core.iam.registry import (
    clear_registry_cache,
    compute_registry_hash,
    default_registry_path,
    load_registry,
    resolve_operator_id,
)
from hg_core.iam.types import AGENT_ZERO_ID, reset_iam_event_ledger


@pytest.fixture(autouse=True)
def _reset_iam_state() -> None:
    clear_registry_cache()
    reset_iam_event_ledger()


def test_iam_u1_registry_load_and_hash_anchor() -> None:
    registry = load_registry()
    assert registry.schema == "operator_registry_v1"
    assert registry.mode == "local_single_user"
    assert registry.registry_hash.startswith("sha256:")
    payload = registry.to_payload()
    assert payload["registry_hash"] == registry.registry_hash
    assert compute_registry_hash({k: v for k, v in payload.items() if k != "registry_hash"}) == registry.registry_hash


def test_iam_u7_local_single_user_exactly_one_active() -> None:
    registry = load_registry()
    active = [op for op in registry.operators if op.status == "active"]
    assert len(active) == 1
    assert active[0].operator_id == "op:local"


def test_legacy_alias_resolves() -> None:
    assert resolve_operator_id("human:operator") == "op:local"
    assert resolve_operator_id("operator") == "op:local"


def test_iam_u3_unregistered_operator_refused() -> None:
    assert resolve_operator_id("op:forged") is None
    assert resolve_operator_id("human:unknown") is None


def test_iam_u5_agent_zero_never_resolves() -> None:
    assert resolve_operator_id(AGENT_ZERO_ID) is None


def test_iam_u4_revoked_operator_refused(tmp_path: Path) -> None:
    base = yaml.safe_load(default_registry_path().read_text(encoding="utf-8"))
    base["operators"][0]["status"] = "revoked"
    reg_path = tmp_path / "registry.yaml"
    reg_path.write_text(yaml.dump(base), encoding="utf-8")
    with pytest.raises(ValueError, match="local_single_user_requires_exactly_one_active_operator"):
        load_registry(reg_path, use_cache=False)


def test_registry_schema_validation(tmp_path: Path) -> None:
    reg_path = tmp_path / "bad.yaml"
    reg_path.write_text(yaml.dump({"schema": "wrong"}), encoding="utf-8")
    with pytest.raises(ValueError, match="operator_registry_schema_mismatch"):
        load_registry(reg_path, use_cache=False)


def test_registry_export_roundtrip() -> None:
    registry = load_registry()
    exported = json.loads(json.dumps(registry.to_payload()))
    assert exported["mode"] == "local_single_user"
