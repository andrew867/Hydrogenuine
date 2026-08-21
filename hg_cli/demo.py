"""Deterministic Community proof/receipt demo used by ``hg demo`` and doctor."""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path
from typing import Any


def run_demo(config: dict[str, Any]) -> dict[str, Any]:
    prior_data_dir = os.environ.get("HG_COMMUNITY_DATA_DIR")
    try:
        with tempfile.TemporaryDirectory(prefix="hg-community-demo-") as temp_dir:
            os.environ["HG_COMMUNITY_DATA_DIR"] = str(Path(temp_dir) / "community")
            from hg_gateway.community import approve_plan, create_plan, list_receipts
            from hg_llm.abstraction import CompletionRequest
            from hg_llm.adapters.stub_adapter import StubCompletionAdapter

            prompt = "Show the local review boundary."
            completion = StubCompletionAdapter().complete(
                CompletionRequest(
                    messages=[{"role": "user", "content": prompt}],
                    model="local-deterministic",
                    provider="stub",
                )
            )
            plan = create_plan({"request": "Create a local review checklist"})["plan"]
            approve_plan(plan["plan_id"])
            receipts = list_receipts()["receipts"]
            return {
                "ok": True,
                "network_used": False,
                "provider": "stub",
                "chat_id": "demo-" + uuid.uuid4().hex[:12],
                "assistant_preview": completion.content[:120],
                "plan_id": plan["plan_id"],
                "receipt_count": len(receipts),
                "claim_boundary": "The demo proves the deterministic local path executed; it does not validate external facts.",
            }
    finally:
        if prior_data_dir is None:
            os.environ.pop("HG_COMMUNITY_DATA_DIR", None)
        else:
            os.environ["HG_COMMUNITY_DATA_DIR"] = prior_data_dir
