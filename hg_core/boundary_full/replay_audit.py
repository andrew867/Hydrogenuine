"""Passive replay audit over RTC JSONL segments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterator


def read_jsonl_events(path: Path) -> Iterator[dict[str, Any]]:
    if not path.is_file():
        return iter(())
    lines = path.read_text(encoding="utf-8").splitlines()

    def _gen() -> Iterator[dict[str, Any]]:
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue

    return _gen()


def classify_event_log(
    paths: list[Path],
    *,
    type_prefix: str,
    handler: Callable[[dict[str, Any]], dict[str, Any] | None],
) -> dict[str, object]:
    """Classify historical events matching type_prefix; report only, no mutation."""
    matched = 0
    results: list[dict[str, Any]] = []
    for path in paths:
        for event in read_jsonl_events(path):
            event_type = str(event.get("type", event.get("event_type", "")))
            if not event_type.startswith(type_prefix):
                continue
            matched += 1
            payload = event.get("payload", {})
            if isinstance(payload, dict):
                result = handler(payload)
                if result:
                    results.append(result)
    return {
        "matched_events": matched,
        "classified": len(results),
        "results": results,
        "replay_audit_only": True,
        "permission_granted": False,
    }


__all__ = ["classify_event_log", "read_jsonl_events"]
