"""Phase 0 architecture static smoke — authority fences and stub boundaries.

Behavioral integration (replay, UEAK→OEA ordering, SRP cycles) lives in
``test_regulation_integration.py``. This module only asserts static fences
required before advancing past Phase 0.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from hg_aep.types import AUTHORITY_FIELD_NAMES
from hg_crr.executors import EXECUTOR_REGISTRY

pytestmark = pytest.mark.phase0_runtime

PHASE0_STUBS: dict[str, str] = {
    "cognition": "hg_runtime.handlers.stubs.StubCognitionHandler",
    "decision": "hg_runtime.handlers.stubs.StubDecisionHandler",
    "kernel": "hg_runtime.handlers.stubs.StubKernelHandler",
    "memory": "hg_runtime.handlers.stubs.StubMemoryHandler",
    "arousal": "hg_runtime.handlers.stubs.StubArousalReader",
    "recovery": "hg_runtime.handlers.stubs.StubRecoveryHandler",
    "ueak": "hg_ueak.stub.UEAKStub",
    "oea": "hg_oea.stub.OEAStub",
}

REGULATION_PACKAGES = ("hg_crr", "hg_aep", "hg_ueak", "hg_oea", "hg_srp")
RTC_BRIDGE_SUFFIXES = ("rtc_adapter.py", "rtc_bridge.py")
BUS_FORBIDDEN = ("bus.emit(", "EventBus(")
EXTERNAL_IO_TOKENS = ("requests.", "httpx.", "urllib.", "subprocess.", "socket.")
HG_RUNTIME_BUS_ALLOWED = frozenset(
    {
        "hg_runtime/bus.py",
        "hg_runtime/loop.py",
        "hg_runtime/demo.py",
        "hg_runtime/controller.py",
    }
)
REQUIRED_AUTHORITY_BANS = frozenset(
    {"grant", "permit", "verdict", "approval", "authority", "approve", "allow", "deny"}
)


def _package_py_files(package: str) -> list[Path]:
    return sorted(Path(package).rglob("*.py"))


def _is_rtc_bridge(path: Path) -> bool:
    return path.name.endswith(RTC_BRIDGE_SUFFIXES)


@pytest.mark.parametrize("label,import_path", list(PHASE0_STUBS.items()))
def test_phase0_stub_modules_import_and_expose_handler_id(label: str, import_path: str):
    module_name, _, class_name = import_path.rpartition(".")
    module = importlib.import_module(module_name)
    stub_cls = getattr(module, class_name)
    instance = stub_cls()
    assert hasattr(instance, "handler_id"), f"{label} stub must expose handler_id"
    assert (
        "phase0" in instance.handler_id
        or "phase1" in instance.handler_id
        or "stub" in instance.handler_id
    )


def test_no_external_io_outside_oea_boundary_stubs():
    targets = [
        Path("hg_ueak/stub.py"),
        Path("hg_oea/stub.py"),
        Path("hg_runtime/handlers/stubs.py"),
    ]
    for path in targets:
        text = path.read_text(encoding="utf-8")
        for token in EXTERNAL_IO_TOKENS:
            assert token not in text, f"{path} must not perform external IO via {token}"


def test_regulation_modules_do_not_bypass_rtc_bus():
    for package in REGULATION_PACKAGES:
        for path in _package_py_files(package):
            if _is_rtc_bridge(path):
                continue
            text = path.read_text(encoding="utf-8")
            for token in BUS_FORBIDDEN:
                assert token not in text, f"{path} must not bypass RTC bus via {token}"


def test_hg_runtime_modules_use_bus_only_in_spine_files():
    for path in _package_py_files("hg_runtime"):
        rel = path.as_posix()
        if rel in HG_RUNTIME_BUS_ALLOWED:
            continue
        text = path.read_text(encoding="utf-8")
        for token in BUS_FORBIDDEN:
            assert token not in text, f"{path} must route RTC interaction through loop/bus spine only"


def test_aep_schemas_cannot_carry_authority_fields():
    schema = json.loads(Path("docs/schemas/aep_signal_v1.json").read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert REQUIRED_AUTHORITY_BANS.isdisjoint(schema["properties"])
    assert REQUIRED_AUTHORITY_BANS.issubset(AUTHORITY_FIELD_NAMES)


def test_crr_adapters_delegate_without_duplicating_hygiene_logic():
    import re

    call_pattern = re.compile(
        r"\b(run_gc_for_agent|run_retention_job|_evict_expired|compact_session)\s*\("
    )
    implementation_files = [
        path
        for path in Path("hg_crr").glob("*.py")
        if path.name not in {"executors.py", "__init__.py"}
    ]
    for path in implementation_files:
        assert not call_pattern.search(path.read_text(encoding="utf-8")), (
            f"{path} must not invoke hygiene executors directly"
        )
    assert EXECUTOR_REGISTRY
    assert all(ref.phase0_status == "registered_not_invoked" for ref in EXECUTOR_REGISTRY)


def test_cognition_handlers_have_no_tool_handle_surface():
    from hg_runtime.cognition import StreamingCognitionHandler
    from hg_runtime.cognition.fake_provider import FakeModelProvider
    from hg_runtime.handlers.stubs import StubCognitionHandler

    for handler in (StubCognitionHandler(), StreamingCognitionHandler(provider=FakeModelProvider())):
        assert not hasattr(handler, "tools")
        assert not hasattr(handler, "tool_handles")


def test_runtime_loop_documents_no_loop_level_oea_or_srp():
    loop_text = Path("hg_runtime/loop.py").read_text(encoding="utf-8")
    assert "no loop-level OEA call exists" in loop_text
    assert "import hg_srp" not in loop_text
    assert "from hg_srp" not in loop_text
