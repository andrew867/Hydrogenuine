"""Agent0 tool awareness tests."""

from hg_runtime.agent0_dev_boot.boot import run_agent0_dev_boot
from hg_runtime.tool_capability_fabric.boot_context import build_boot_context, grounded_capability_answer
from hg_runtime.tool_capability_fabric.registry import load_registry
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]


def test_boot_context_includes_manifest():
    ctx = build_boot_context(run_id="test", registry=load_registry())
    assert ctx.capability_manifest["advisory_only"] is True
    assert ctx.system_instruction


def test_grounded_answer_mentions_broker():
    reg = load_registry()
    text = grounded_capability_answer(reg.build_manifest(organ_id="organ:Agent0"))
    assert "broker" in text


def test_dry_run_boot_tool_context():
    result = run_agent0_dev_boot(
        profile_path=WORKSPACE / "configs/runtime/dev-fallback-stub.json",
        dry_run=True,
        storage_required=False,
        allow_tool_requests=True,
    )
    assert result.capability_manifest is not None
    assert result.tool_context is not None
