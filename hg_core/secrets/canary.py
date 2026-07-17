"""Canary secret markers for CT-02 leak detection sweeps."""

from __future__ import annotations

import os
from typing import Iterable

# Distinct markers — never use in production configs.
CANARY_MARKERS: dict[str, str] = {
    "event": "HG-CANARY-SEC-EVENT-9f3a2b",
    "receipt": "HG-CANARY-SEC-RECEIPT-7c1d4e",
    "ter": "HG-CANARY-SEC-TER-5e8f0a",
    "crash": "HG-CANARY-SEC-CRASH-3b2c1d",
    "bundle": "HG-CANARY-SEC-BUNDLE-1a9e8f",
    "plt": "HG-CANARY-SEC-PLT-4d7c2b",
    "config": "HG-CANARY-SEC-CONFIG-6f1e0d",
}

CANARY_ENV_NAMES: tuple[str, ...] = tuple(f"HG_CANARY_SECRET_{name.upper()}" for name in CANARY_MARKERS)


def all_canary_values() -> frozenset[str]:
    values = set(CANARY_MARKERS.values())
    for name in CANARY_ENV_NAMES:
        env_val = os.environ.get(name, "").strip()
        if env_val:
            values.add(env_val)
    return frozenset(values)


def plant_canary_env() -> dict[str, str]:
    """Plant canaries into environment for gate sweeps (test/gate only)."""
    planted: dict[str, str] = {}
    for env_name, marker in zip(CANARY_ENV_NAMES, CANARY_MARKERS.values(), strict=True):
        os.environ[env_name] = marker
        planted[env_name] = marker
    return planted


def clear_canary_env() -> None:
    for name in CANARY_ENV_NAMES:
        os.environ.pop(name, None)


def contains_canary(text: str) -> bool:
    if not text:
        return False
    for marker in all_canary_values():
        if marker in text:
            return True
    return False


def find_canaries_in_text(text: str) -> list[str]:
    return [marker for marker in all_canary_values() if marker in text]


def find_canaries_in_iterable(values: Iterable[object]) -> list[str]:
    hits: list[str] = []
    for value in values:
        if isinstance(value, str) and contains_canary(value):
            hits.extend(find_canaries_in_text(value))
        elif isinstance(value, dict):
            for item in value.values():
                hits.extend(find_canaries_in_iterable([item]))
        elif isinstance(value, list):
            hits.extend(find_canaries_in_iterable(value))
    return list(dict.fromkeys(hits))


__all__ = [
    "CANARY_ENV_NAMES",
    "CANARY_MARKERS",
    "all_canary_values",
    "clear_canary_env",
    "contains_canary",
    "find_canaries_in_iterable",
    "find_canaries_in_text",
    "plant_canary_env",
]
