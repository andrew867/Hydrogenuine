"""ARM integration types — modules 6-14 safe/static scope."""

from __future__ import annotations

FIXTURE_CLOCK = "2026-06-14T22:30:00.000000Z"

REQUIRED_ARM_BUS_MODULES: tuple[str, ...] = (
    "BRS",
    "HRT",
    "RSP",
    "CIR",
    "DBB",
    "ESB",
    "ISB",
    "RDB",
    "ALC",
)

__all__ = ["FIXTURE_CLOCK", "REQUIRED_ARM_BUS_MODULES"]
