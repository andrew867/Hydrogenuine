"""OIR no-authority markers."""

from __future__ import annotations


def advisory_only_marker() -> dict[str, bool]:
    return {
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
        "durable_write_performed": False,
        "oir_is_advisory_only": True,
    }


__all__ = ["advisory_only_marker"]
