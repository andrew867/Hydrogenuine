"""Auto-approval, warning, and full-stop lattice."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_runtime.cloud_browser_governance.types import DecisionClass, FIXTURE_CLOCK, advisory_envelope, stable_hash

WORKSPACE = Path(__file__).resolve().parents[2]
LATTICE_CONFIG = WORKSPACE / "configs" / "policy" / "auto_approval_lattice.example.json"

AUTO_APPROVE_ACTIONS = frozenset(
    {
        "local_memory_read",
        "knowledge_lookup",
        "proof_read",
        "proof_verify",
        "artifact_read",
        "storage_read",
        "capability_manifest",
        "social_draft",
        "email_draft",
        "model_inference",
        "operator_message",
        "shell_safe",
        "browser_read_page",
        "browser_extract_text",
        "browser_screenshot",
        "browser_open_url_request",
        "browser_search_public_web_request",
    }
)

FULL_STOP_ACTIONS = frozenset(
    {
        "email_send_request",
        "social_publish_request",
        "social_reply_request",
        "social_dm_request",
        "social_delete_request",
        "account_creation_execute",
        "browser_login_execute",
        "browser_form_submit",
        "browser_credential_entry",
        "browser_payment",
        "shell_privileged_request",
        "oea_action_request",
        "ter_tool_request",
        "srp_apply",
        "live_oea",
        "live_ter",
    }
)

WARN_ACTIONS = frozenset(
    {
        "memory_write_request",
        "browser_download_request",
        "browser_follow_link_request",
        "browser_form_detect",
        "browser_login_detect",
        "browser_account_creation_detect",
        "cloud_provider_call",
        "email_draft_external",
    }
)


class ApprovalDecisionEngine:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or self._load_config()

    @staticmethod
    def _load_config() -> dict[str, Any]:
        if LATTICE_CONFIG.is_file():
            return json.loads(LATTICE_CONFIG.read_text(encoding="utf-8"))
        return {}

    def evaluate(self, *, action_id: str, parameters: dict[str, Any] | None = None, external_network: bool = False) -> dict[str, Any]:
        params = parameters or {}
        if action_id in FULL_STOP_ACTIONS:
            decision: DecisionClass = "FULL_STOP"
            explanation = "High-risk external/write action requires operator review; not auto-approved"
            safe_alt = "use draft tools or operator_message"
        elif action_id in {"browser_form_submit", "browser_login_execute", "account_creation_execute"}:
            decision = "FULL_STOP"
            explanation = "Form submit/login/account creation forbidden by default"
            safe_alt = "read-only browsing only"
        elif action_id.startswith("browser_") and not external_network:
            decision = "DENIED"
            explanation = "External network disabled for browsing"
            safe_alt = "enable profile with external_network_allowed"
        elif action_id in AUTO_APPROVE_ACTIONS:
            if action_id.startswith("browser_") and params.get("method", "GET").upper() != "GET":
                decision = "FULL_STOP"
                explanation = "Non-GET browser action forbidden"
                safe_alt = "read-only GET"
            else:
                decision = "AUTO_APPROVE"
                explanation = "Low-risk read-only/local action within lattice"
                safe_alt = ""
        elif action_id in WARN_ACTIONS:
            decision = "AUTO_WARN"
            explanation = "Action permitted with warning receipt"
            safe_alt = "review parameters before escalating"
        elif action_id in {"gmail_read_request", "gmail_send_request", "account_creation_request"}:
            decision = "OPERATOR_REVIEW"
            explanation = "Account/email surface requires operator review"
            safe_alt = "email_draft locally"
        else:
            decision = "OPERATOR_REVIEW"
            explanation = "Unclassified action requires review"
            safe_alt = "capability_manifest"

        payload = advisory_envelope(
            schema="approval-lattice-decision",
            action_id=action_id,
            decision=decision,
            explanation=explanation,
            safe_alternative=safe_alt,
            external_network=external_network,
            timestamp=FIXTURE_CLOCK,
        )
        payload["receipt_hash"] = stable_hash(payload)
        return payload


__all__ = ["ApprovalDecisionEngine", "AUTO_APPROVE_ACTIONS", "FULL_STOP_ACTIONS", "WARN_ACTIONS"]
