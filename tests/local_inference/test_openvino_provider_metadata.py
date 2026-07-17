"""OpenVINO provider advisory metadata invariants (static analysis)."""

from __future__ import annotations

import ast
import re
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
PROVIDER_PY = WORKSPACE / "scripts" / "windows" / "openvino" / "provider" / "openvino_provider.py"


def test_provider_source_metadata_invariants() -> None:
    source = PROVIDER_PY.read_text(encoding="utf-8")
    assert '"advisory_only": True' in source
    assert '"permission_granted": False' in source
    assert '"authority_created": False' in source
    assert 'BACKEND_TYPE = "openvino_windows"' in source
    assert 'BACKEND_ID = "windows-openvino-igpu"' in source


def test_fallback_stub_text_is_deterministic() -> None:
    source = PROVIDER_PY.read_text(encoding="utf-8")
    match = re.search(r'FALLBACK_STUB_TEXT = "([^"]+)"', source)
    assert match, "FALLBACK_STUB_TEXT constant required"
    assert "dev mode" in match.group(1).lower()


def test_advisory_metadata_function_returns_required_keys() -> None:
    tree = ast.parse(PROVIDER_PY.read_text(encoding="utf-8"))
    fn = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_advisory_metadata"
    )
    returned_keys = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in {
                "backend_id",
                "backend_type",
                "device",
                "model_id",
                "advisory_only",
                "permission_granted",
                "authority_created",
                "fallback_stub",
            }:
                returned_keys.add(node.value)
    for required in (
        "advisory_only",
        "permission_granted",
        "authority_created",
        "fallback_stub",
        "backend_type",
    ):
        assert required in returned_keys, f"missing metadata key {required}"


def test_no_permission_granted_true_in_provider() -> None:
    source = PROVIDER_PY.read_text(encoding="utf-8")
    assert '"permission_granted": True' not in source
    assert '"authority_created": True' not in source
    assert "permission_granted = True" not in source
