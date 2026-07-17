"""Quality receipt I/O — append-only emission."""

from __future__ import annotations

import json
import os


def write_receipt(receipt: dict, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(receipt, separators=(",", ":")) + "\n")


def read_receipts(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    receipts = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                receipts.append(json.loads(line))
    return receipts
