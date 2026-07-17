"""WILL + memory write request integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_runtime.tool_capability_fabric.types import advisory_envelope
from hg_runtime.will_module.context import WillContext
from hg_runtime.will_module.policy import will_may_contextualize_tool
from hg_runtime.will_module.receipts import WillTrace
from hg_runtime.will_module.schema import MemoryWriteIntent


@dataclass
class MemoryWriteRequestContext:
    intent: MemoryWriteIntent
    will_context: WillContext | None = None
    write_performed: bool = False

    def to_payload(self) -> dict[str, Any]:
        if self.will_context:
            trace = self.will_context.trace or WillTrace(
                run_id=self.will_context.envelope.run_id,
                will_id=self.will_context.envelope.will_id,
            )
            trace.append(
                "WILL_MEMORY_REQUEST_CONTEXT_ATTACHED",
                region=self.intent.region,
                purpose=self.intent.purpose,
            )
        return advisory_envelope(
            schema="memory-write-request-context",
            intent=self.intent.to_payload(),
            will_id=self.will_context.envelope.will_id if self.will_context else None,
            will_hash=self.will_context.envelope.hash if self.will_context else None,
            write_performed=False,
            result_summary="write request recorded; no mutation performed by WILL",
            will_approved_write=False,
        )


def memory_write_intent_to_request(intent: MemoryWriteIntent, will_context: WillContext | None = None) -> MemoryWriteRequestContext:
    if will_context and not will_may_contextualize_tool(will_context.envelope):
        pass
    return MemoryWriteRequestContext(intent=intent, will_context=will_context, write_performed=False)


__all__ = ["MemoryWriteRequestContext", "memory_write_intent_to_request"]
