"""Agent #0 boot capability awareness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_runtime.tool_capability_fabric.broker import BrokerResult, ToolBroker, new_request
from hg_runtime.tool_capability_fabric.registry import CapabilityRegistry, load_registry
from hg_runtime.tool_capability_fabric.types import advisory_envelope

SYSTEM_INSTRUCTION = """You are Agent #0 in Hydrogenuine dev boot.

Doctrine:
- Model proposes. Authority disposes.
- You may REQUEST any capability listed in the capability manifest.
- You may request search, news, knowledge, memory, social drafts, proof inspection, artifacts, and registered tools.
- You are NOT allowed to execute tools directly; use the governed tool request broker.
- Approvals are scoped and receipt-backed. Denials include reasons and safe alternatives.
- Never self-authorize. Never claim a tool succeeded without a tool execution receipt.
- Never publish, post, send, delete, or mutate externally without explicit governed authorization.
- Social drafts are local only. Search and memory results are advisory, not proof.
- Ask "what tools can I request?" to receive the capability manifest."""


@dataclass
class Agent0BootContext:
    run_id: str
    capability_manifest: dict[str, Any]
    system_instruction: str
    tool_demo_results: list[dict[str, Any]]

    def to_payload(self) -> dict[str, Any]:
        return advisory_envelope(
            schema="agent0-boot-context",
            run_id=self.run_id,
            capability_manifest=self.capability_manifest,
            system_instruction=self.system_instruction,
            tool_demo_count=len(self.tool_demo_results),
            tool_demo_results=self.tool_demo_results,
        )


def build_boot_context(
    *,
    run_id: str,
    registry: CapabilityRegistry | None = None,
    broker: ToolBroker | None = None,
    run_tool_demos: bool = True,
) -> Agent0BootContext:
    reg = registry or load_registry()
    brk = broker or ToolBroker(reg)
    manifest = reg.build_manifest(organ_id="organ:Agent0", role="agent0")
    demos: list[dict[str, Any]] = []
    if run_tool_demos:
        demos.append(brk.submit(new_request(run_id=run_id, organ_id="organ:Agent0", capability_id="capability_manifest", requested_action="read")).to_payload())
        demos.append(
            brk.submit(
                new_request(run_id=run_id, organ_id="organ:Agent0", capability_id="knowledge_lookup", requested_action="read", parameters={"query": "tool capability"}),
            ).to_payload()
        )
        demos.append(
            brk.submit(
                new_request(run_id=run_id, organ_id="organ:Agent0", capability_id="local_memory_read", requested_action="read", parameters={"query": "doctrine"}),
            ).to_payload()
        )
        demos.append(
            brk.submit(
                new_request(
                    run_id=run_id,
                    organ_id="organ:Agent0",
                    capability_id="social_draft",
                    requested_action="draft",
                    parameters={"text": "hello dev world (draft only)", "platform": "local"},
                ),
            ).to_payload()
        )
        demos.append(
            brk.submit(
                new_request(
                    run_id=run_id,
                    organ_id="organ:Agent0",
                    capability_id="social_publish_request",
                    requested_action="publish",
                    parameters={"text": "must not publish"},
                ),
            ).to_payload()
        )
    return Agent0BootContext(run_id=run_id, capability_manifest=manifest, system_instruction=SYSTEM_INSTRUCTION, tool_demo_results=demos)


def grounded_capability_answer(manifest: dict[str, Any]) -> str:
    caps = manifest.get("capabilities", [])
    names = [c.get("capability_id", "") for c in caps if c.get("enabled")]
    return (
        "I can request these enabled capabilities via the broker: "
        + ", ".join(names[:12])
        + (f" (+{len(names)-12} more)" if len(names) > 12 else "")
        + ". I cannot execute live publish/send without operator approval and receipts."
    )


__all__ = ["SYSTEM_INSTRUCTION", "Agent0BootContext", "build_boot_context", "grounded_capability_answer"]
