"""Lifecycle anchor autopilot receipts."""

from __future__ import annotations

import uuid

from hg_runtime.lifecycle_anchor_autopilot.schema import AnchorAutopilotReceipt


def new_receipt_id() -> str:
    return f"aap-{uuid.uuid4().hex[:12]}"


def build_receipt(**kwargs) -> AnchorAutopilotReceipt:
    return AnchorAutopilotReceipt(receipt_id=new_receipt_id(), **kwargs)
