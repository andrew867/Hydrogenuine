"""Agent Zero social context — status and cargo only."""

from __future__ import annotations

from typing import Any

from hg_runtime.social_capability.credentials import agent0_credential_summary
from hg_runtime.social_capability.schema import _frozen


def agent0_social_context() -> dict[str, Any]:
    return {
        "schema": "agent0-social-context",
        "identity": "Agent Zero (Zero, A#0, agent0)",
        "credentials": agent0_credential_summary(),
        "may_request": [
            "social_read_fixture",
            "social_draft",
            "queue_publish",
            "operator_approval",
        ],
        "may_not": [
            "direct_publish",
            "dm",
            "reply",
            "follow",
            "unfollow",
            "delete",
            "login",
            "account_create",
            "seize_credentials",
        ],
        **_frozen(),
    }


__all__ = ["agent0_social_context"]
