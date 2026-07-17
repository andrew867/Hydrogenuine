"""OEA append-only effect receipt ledger."""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from hg_core.ledger.canonical_json import canonical_dumps
from hg_oea.types import EffectReceipt


class OEAReceiptLedger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def _last_hash(self) -> Optional[str]:
        lines = [line for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return None
        last = json.loads(lines[-1])
        return str(last.get("receipt_hash", ""))

    def append(self, receipt: EffectReceipt) -> EffectReceipt:
        previous = self._last_hash()
        stored_payload = receipt.to_payload()
        if previous:
            stored_payload["previous_receipt_hash"] = previous
        digest = hashlib.sha256(canonical_dumps(stored_payload)).hexdigest()
        receipt_hash = f"sha256:{digest}"
        stored_payload["receipt_hash"] = receipt_hash
        stored = dataclasses.replace(
            receipt, receipt_hash=receipt_hash, previous_receipt_hash=previous)
        line = canonical_dumps(stored_payload).decode("utf-8") + "\n"
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)
        return stored

    def verify_chain(self) -> dict[str, Any]:
        lines = [line for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
        previous: Optional[str] = None
        for index, line in enumerate(lines):
            record = json.loads(line)
            if previous is not None and record.get("previous_receipt_hash") != previous:
                return {"ok": False, "error": f"chain_break_at_{index}"}
            payload = dict(record)
            stored_hash = payload.pop("receipt_hash", "")
            if payload.get("previous_receipt_hash") != previous:
                return {"ok": False, "error": f"prev_mismatch_at_{index}"}
            digest = hashlib.sha256(canonical_dumps(payload)).hexdigest()
            if stored_hash != f"sha256:{digest}":
                return {"ok": False, "error": f"hash_mismatch_at_{index}"}
            previous = stored_hash
        return {"ok": True, "count": len(lines)}


__all__ = ["OEAReceiptLedger"]
