"""Agent0 cloud tool bootstrap tests."""

from hg_runtime.cloud_browser_governance.bootstrap import build_cloud_bootstrap, grounded_cloud_answer


def test_bootstrap_builds():
    ctx = build_cloud_bootstrap(run_id="test", run_demos=False)
    assert ctx.routing_profile["cloud_providers_enabled"] is False


def test_grounded_answer():
    ctx = build_cloud_bootstrap(run_id="test", run_demos=False)
    text = grounded_cloud_answer(ctx)
    assert "broker" in text
