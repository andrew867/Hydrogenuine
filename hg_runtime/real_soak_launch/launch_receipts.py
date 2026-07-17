"""Soak launch receipts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.real_soak_launch.schema import new_id, now_iso, soak_dir


@dataclass
class SoakLaunchReceipt:
    receipt_id: str
    soak_id: str
    event: str
    verdict: str
    created_at: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "soak_id": self.soak_id,
            "event": self.event,
            "verdict": self.verdict,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> SoakLaunchReceipt:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return SoakLaunchReceipt(**{**self.__dict__, "hash": compute_record_hash(body)})


def persist_receipt(receipt: SoakLaunchReceipt, *, base: Path | None = None) -> Path:
    d = soak_dir(receipt.soak_id, base=base) / "receipts"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{receipt.receipt_id}.json"
    path.write_text(json.dumps(receipt.with_hash().to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def make_receipt(soak_id: str, event: str, verdict: str) -> SoakLaunchReceipt:
    return SoakLaunchReceipt(
        receipt_id=new_id("soak-rcpt"),
        soak_id=soak_id,
        event=event,
        verdict=verdict,
        created_at=now_iso(),
    ).with_hash()
