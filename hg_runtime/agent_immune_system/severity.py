"""AIS severity enums and validation."""

from __future__ import annotations

from hg_runtime.agent_immune_system.schemas import AISImmuneError, SEVERITIES


def validate_severity(value: str) -> str:
    if value not in SEVERITIES:
        raise AISImmuneError(f"invalid_severity:{value}")
    return value


def severity_rank(value: str) -> int:
    return SEVERITIES.index(validate_severity(value))
