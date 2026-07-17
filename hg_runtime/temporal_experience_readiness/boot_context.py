"""Aggregate Agent Zero temporal boot context."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_self_mirror.agent0_context import SELF_MIRROR_BOOT_INSTRUCTION
from hg_runtime.chrono.agent0_context import CHRONO_LOCK_BOOT_INSTRUCTION
from hg_runtime.external_start_anchor.agent0_context import ANCHOR_BOOT_INSTRUCTION
from hg_runtime.external_start_anchor.credentials import resolve_credential_status
from hg_runtime.external_witness_journal.agent0_context import EWJ_BOOT_INSTRUCTION
from hg_runtime.wake_refresh.agent0_context import WAKE_REFRESH_BOOT_INSTRUCTION

WORKSPACE = Path(__file__).resolve().parents[2]

AGENT_IDENTITY = {
    "agent_long_name": "Agent Zero",
    "agent_short_name": "Zero",
    "agent_ui_shorthand": "A#0",
    "agent_code_id": "agent0",
}

BOOT_CONTEXT_KEYS = [
    "agent_identity",
    "wake_refresh",
    "chrono_context",
    "chrono_lock_context",
    "external_start_anchor",
    "external_witness_journal",
    "signed_anchor_status",
    "self_mirror",
    "will_context",
    "trust_boundary_policy",
    "capability_manifest",
    "organ_manifest",
    "storage_status",
    "proof_status",
    "provider_status",
    "cloud_budget_status",
    "browser_tool_status",
    "audio_io_status",
    "audio_local_setup_status",
    "tool_governance_status",
    "denial_policy_summary",
    "stop_panic_status",
]

TRUST_BOUNDARY_POLICY_SUMMARY = {
    "schema": "trust-boundary-policy-summary",
    "external_content_is_evidence_only": True,
    "untrusted_web_quarantine": True,
    "injection_scan_enabled": True,
    "authority_conversion_blocked": True,
    "advisory_only": True,
    "permission_granted": False,
    "authority_created": False,
}

DENIAL_POLICY_SUMMARY = {
    "schema": "denial-policy-summary",
    "live_social_publish": False,
    "live_email_send": False,
    "account_creation": False,
    "login_form_submit": False,
    "live_oea": False,
    "live_ter": False,
    "srp_apply": False,
    "privileged_shell": False,
    "autonomous_github_push": False,
    "live_playback": False,
    "always_listen_mic": False,
    "advisory_only": True,
    "permission_granted": False,
    "authority_created": False,
}


def _signed_anchor_status(anchor_context: dict[str, Any] | None) -> dict[str, Any]:
    cred = resolve_credential_status()
    return {
        "schema": "signed-anchor-status",
        "credential_status": cred.mode.value,
        "credential_visible_to_agent": False,
        "signed": bool((anchor_context or {}).get("signed")),
        "signer_key_id": (anchor_context or {}).get("signer_key_id"),
        "signature_verified": bool((anchor_context or {}).get("signature_verified")),
        "live_push_operator_controlled": True,
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def build_temporal_boot_context(
    *,
    boot_payload: dict[str, Any],
    organ_manifest: dict[str, Any] | None = None,
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile = profile or {}
    anchor = boot_payload.get("anchor_context") or boot_payload.get("external_start_anchor")
    ctx: dict[str, Any] = {
        "agent_identity": {**AGENT_IDENTITY, **FROZEN_FALSE},
        "wake_refresh": boot_payload.get("wake_refresh_context") or boot_payload.get("wake_refresh"),
        "chrono_context": boot_payload.get("chrono_context"),
        "chrono_lock_context": boot_payload.get("chrono_lock_context"),
        "external_start_anchor": anchor or {
            "schema": "external-start-anchor-absent",
            "handoff_present": False,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        },
        "external_witness_journal": boot_payload.get("witness_journal_context") or boot_payload.get("external_witness_journal"),
        "signed_anchor_status": _signed_anchor_status(anchor if isinstance(anchor, dict) else None),
        "self_mirror": boot_payload.get("self_mirror_context"),
        "will_context": boot_payload.get("will_context"),
        "trust_boundary_policy": TRUST_BOUNDARY_POLICY_SUMMARY,
        "capability_manifest": boot_payload.get("capability_manifest"),
        "organ_manifest": organ_manifest,
        "storage_status": {
            "schema": "storage-status",
            "ok": boot_payload.get("storage_ok", False),
            "verdict": (boot_payload.get("storage_detail") or {}).get("verdict")
            if isinstance(boot_payload.get("storage_detail"), dict)
            else None,
            "proof_ref": (boot_payload.get("storage_detail") or {}).get("proof_dir")
            if isinstance(boot_payload.get("storage_detail"), dict)
            else None,
            "source": (boot_payload.get("storage_detail") or {}).get("source")
            if isinstance(boot_payload.get("storage_detail"), dict)
            else None,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        },
        "proof_status": {
            "schema": "proof-status",
            "summary": (boot_payload.get("self_mirror_context") or {}).get("proof_index_summary"),
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        },
        "provider_status": {
            "schema": "provider-status",
            "ok": boot_payload.get("provider_ok", False),
            "openvino_preferred": True,
            "fallback_stub_allowed": profile.get("fallback_stub_allowed", False),
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        },
        "cloud_budget_status": {
            "schema": "cloud-budget-status",
            "cloud_providers_enabled": profile.get("cloud_providers_enabled", False),
            "external_network_allowed": profile.get("external_network_allowed", False),
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        },
        "browser_tool_status": {
            "schema": "browser-tool-status",
            "live_browser_enabled": profile.get("live_browser_enabled", False),
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        },
        "audio_io_status": boot_payload.get("audio_context"),
        "audio_local_setup_status": {
            "schema": "audio-local-setup-status",
            "detail": (boot_payload.get("audio_context") or {}).get("local_setup") if isinstance(boot_payload.get("audio_context"), dict) else None,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        },
        "tool_governance_status": boot_payload.get("tool_context"),
        "denial_policy_summary": DENIAL_POLICY_SUMMARY,
        "stop_panic_status": {
            "schema": "stop-panic-status",
            "panic_stop_enabled": profile.get("panic_stop_enabled", True),
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        },
        "instructions": {
            "anchor": ANCHOR_BOOT_INSTRUCTION,
            "chrono_lock": CHRONO_LOCK_BOOT_INSTRUCTION,
            "wake_refresh": WAKE_REFRESH_BOOT_INSTRUCTION,
            "witness_journal": EWJ_BOOT_INSTRUCTION,
            "self_mirror": SELF_MIRROR_BOOT_INSTRUCTION,
        },
        **FROZEN_FALSE,
    }
    return ctx


def assess_boot_completeness(temporal: dict[str, Any], *, anchor_optional: bool = False) -> tuple[list[str], list[str]]:
    optional = {"external_start_anchor"} if anchor_optional else set()
    present = [k for k in BOOT_CONTEXT_KEYS if k in temporal and (temporal.get(k) is not None or k in optional)]
    missing = [k for k in BOOT_CONTEXT_KEYS if k not in present]
    return present, missing


FROZEN_FALSE = {
    "advisory_only": True,
    "permission_granted": False,
    "authority_created": False,
}


__all__ = [
    "BOOT_CONTEXT_KEYS",
    "build_temporal_boot_context",
    "assess_boot_completeness",
]
