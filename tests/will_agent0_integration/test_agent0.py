"""Agent #0 WILL integration tests."""

from hg_runtime.agent0_dev_boot.boot import run_agent0_dev_boot
from hg_runtime.will_module.agent0 import answer_will_query, build_agent0_will_context, validate_agent0_will_explanation


def test_agent0_boot_includes_will():
    result = run_agent0_dev_boot(
        profile_path="configs/runtime/agent0-dev-boot-local-openvino.json",
        dry_run=True,
        storage_required=False,
        will_profile="configs/will/agent0_dev_boot_will.example.json",
    )
    assert result.will_context is not None
    assert result.will_context["schema"] == "agent0-will-boot-context"
    assert result.will_context["will_context"]["will_is_not_permission"] is True


def test_agent0_explains_will_correctly():
    ctx = build_agent0_will_context(run_id="run-a0", will_profile="configs/will/agent0_dev_boot_will.example.json")
    answer = answer_will_query("what is our current will?", ctx.will_context)
    assert validate_agent0_will_explanation(answer)
    assert "advisory" in answer.lower() or "governance" in answer.lower()


def test_agent0_refusal_guidance():
    ctx = build_agent0_will_context(run_id="run-ref", will_profile="configs/will/agent0_dev_boot_will.example.json")
    answer = answer_will_query("what should I refuse?", ctx.will_context)
    assert "live_social_publish" in answer or "refuse" in answer.lower()
