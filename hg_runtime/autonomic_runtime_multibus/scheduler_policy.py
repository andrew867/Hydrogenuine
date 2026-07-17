"""Static inference scheduler policy — no live backends."""

from __future__ import annotations

from typing import Any

_FORBIDDEN_BACKEND_TOKENS = (
    "vllm",
    "openai",
    "anthropic",
    "ollama",
    "live_gpu",
    "http://",
    "https://",
)


def validate_scheduler_fixture(profile: dict[str, Any]) -> dict[str, object]:
    """Verify scheduler profile uses fixture/static backends only."""
    backend = str(profile.get("backend", "")).lower()
    live_invocation = bool(profile.get("live_invocation", False))
    violations: list[str] = []
    if live_invocation:
        violations.append("live_invocation_forbidden")
    for token in _FORBIDDEN_BACKEND_TOKENS:
        if token in backend:
            violations.append(f"forbidden_backend:{token}")
    ok = not violations
    return {
        "status": "validated" if ok else "rejected",
        "scheduler_is_advisory_only": True,
        "live_backend_blocked": not ok or backend == "fixture_static",
        "permission_granted": False,
        "authority_created": False,
        "violations": violations,
        "backend": backend or "fixture_static",
    }


__all__ = ["validate_scheduler_fixture"]
