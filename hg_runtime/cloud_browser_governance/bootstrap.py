"""Agent #0 cloud + tool bootstrap context."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.cloud_browser_governance.budget import ProviderBudgetGovernor
from hg_runtime.cloud_browser_governance.lattice import ApprovalDecisionEngine
from hg_runtime.cloud_browser_governance.routing_profiles import load_routing_profile, profile_summary
from hg_runtime.cloud_browser_governance.secrets import secret_presence_check
from hg_runtime.cloud_browser_governance.types import advisory_envelope
from hg_runtime.cloud_browser_governance.browser import execute_browser_tool
from hg_runtime.model_provider_fabric.adapters.cloud import get_adapter, live_cloud_allowed
from hg_runtime.model_provider_fabric.config_loader import DEFAULT_CONFIG, load_registry
from hg_runtime.tool_capability_fabric.boot_context import build_boot_context
from hg_runtime.tool_capability_fabric.broker import ToolBroker, new_request
from hg_runtime.tool_capability_fabric.registry import load_registry as load_tool_registry

WORKSPACE = Path(__file__).resolve().parents[2]

CLOUD_SYSTEM_ADDENDUM = """
Cloud and browser doctrine:
- You may request cloud models when operator enables HG_CLOUD_PROVIDERS_ENABLED.
- You may request read-only browsing when external network profile allows it.
- Watch token/cost budgets; denials and warnings are normal.
- Email/social send/post/account creation require operator review or full-stop.
- Browser results and search pages are advisory, not proof.
- Never claim an action occurred without a tool/provider receipt.
"""


@dataclass
class Agent0CloudBootstrapContext:
    run_id: str
    routing_profile: dict[str, Any]
    capability_context: dict[str, Any]
    secret_status: dict[str, Any]
    budget_status: dict[str, Any]
    lattice_samples: list[dict[str, Any]]
    demo_results: list[dict[str, Any]]

    def to_payload(self) -> dict[str, Any]:
        return advisory_envelope(
            schema="agent0-cloud-tool-bootstrap",
            run_id=self.run_id,
            routing_profile=profile_summary(self.routing_profile),
            capability_context=self.capability_context,
            secret_status=self.secret_status,
            budget_status=self.budget_status,
            lattice_sample_count=len(self.lattice_samples),
            demo_count=len(self.demo_results),
            demo_results=self.demo_results,
        )


def build_cloud_bootstrap(
    *,
    run_id: str,
    routing_profile_path: str | Path = "configs/runtime/provider-routing-local-first.json",
    run_demos: bool = True,
) -> Agent0CloudBootstrapContext:
    profile = load_routing_profile(WORKSPACE / routing_profile_path)
    tool_ctx = build_boot_context(run_id=run_id, run_tool_demos=False).to_payload()
    secrets = secret_presence_check()
    governor = ProviderBudgetGovernor()
    budget = governor.check_budget(tokens=0, cost_usd=0.0)
    lattice = ApprovalDecisionEngine()
    samples = [
        lattice.evaluate(action_id="knowledge_lookup"),
        lattice.evaluate(action_id="social_draft"),
        lattice.evaluate(action_id="social_publish_request"),
        lattice.evaluate(action_id="email_send_request"),
        lattice.evaluate(action_id="browser_form_submit"),
        lattice.evaluate(action_id="account_creation_request", external_network=profile.get("external_network_allowed", False)),
    ]
    demos: list[dict[str, Any]] = []
    if run_demos:
        broker = ToolBroker(load_tool_registry())
        demos.append(broker.submit(new_request(run_id=run_id, organ_id="organ:Agent0", capability_id="social_draft", requested_action="draft", parameters={"text": "Hydrogenuine dev draft", "platform": "local"})).to_payload())
        demos.append(broker.submit(new_request(run_id=run_id, organ_id="organ:Agent0", capability_id="social_publish_request", requested_action="publish", parameters={"text": "Hydrogenuine dev draft"})).to_payload())
        demos.append(broker.submit(new_request(run_id=run_id, organ_id="organ:Agent0", capability_id="operator_message", requested_action="draft", parameters={"message": "draft email to Andrew (no send)", "subject": "email_draft"})).to_payload())
        demos.append(execute_browser_tool("browser_read_page", {"url": "fixture://local"}))
        demos.append(execute_browser_tool("browser_form_submit", {"url": "https://example.com/login"}))
        reg = load_registry(extra_paths=[WORKSPACE / "configs/model_providers/cloud_providers.example.json"])
        for pid in ("openai-agent0-heavy", "anthropic-agent0-heavy", "xai-agent0-heavy"):
            cfg = reg.get(pid)
            if cfg:
                adapter = get_adapter(cfg.provider_type)
                if adapter:
                    demos.append(adapter.validate_config(cfg))
                    demos.append(adapter.dry_run_health(cfg))
    return Agent0CloudBootstrapContext(
        run_id=run_id,
        routing_profile=profile,
        capability_context=tool_ctx,
        secret_status=secrets,
        budget_status=budget,
        lattice_samples=samples,
        demo_results=demos,
    )


def grounded_cloud_answer(ctx: Agent0CloudBootstrapContext) -> str:
    cloud = "enabled" if ctx.routing_profile.get("cloud_providers_enabled") else "disabled"
    browser = "enabled" if ctx.routing_profile.get("external_network_allowed") else "disabled"
    return (
        f"I can request local and cloud capabilities via the broker (cloud {cloud}, browsing {browser}). "
        "I can draft social posts and emails but cannot send/post/create accounts without operator approval receipts."
    )


__all__ = ["CLOUD_SYSTEM_ADDENDUM", "Agent0CloudBootstrapContext", "build_cloud_bootstrap", "grounded_cloud_answer"]
