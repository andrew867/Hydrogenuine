"""Safe local tool implementations."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from hg_runtime.model_provider_fabric.provider_receipts import (
    ProviderKind,
    ProviderMode,
    ProviderRealityVerdict,
    ProviderStatus,
    build_provider_receipt,
    receipt_counts_as_cognition,
)
from hg_runtime.model_provider_fabric.routing import COGNITIVE_ROLES
from hg_runtime.runtime_mode import resolve_runtime_mode
from hg_runtime.tool_capability_fabric.types import advisory_envelope, stable_hash

WORKSPACE = Path(__file__).resolve().parents[3]

SHELL_ALLOWLIST = frozenset(
    {
        "git status --short",
        "docker compose ps",
        "docker compose ps --format json",
    }
)


def capability_manifest_tool(registry_manifest: dict[str, Any]) -> dict[str, Any]:
    return advisory_envelope(
        schema="tool-result-capability-manifest",
        result=registry_manifest,
        is_proof=False,
        is_publication=False,
    )


def memory_read_tool(*, query: str = "") -> dict[str, Any]:
    fixture = {
        "entries": [
            {"key": "agent0.boot.doctrine", "summary": "Model proposes; authority disposes.", "advisory_only": True},
            {"key": "agent0.tools", "summary": "Request capabilities via broker; never self-authorize.", "advisory_only": True},
        ],
        "query": query,
        "source": "local_fixture",
    }
    return advisory_envelope(
        schema="tool-result-memory-read",
        result=fixture,
        result_hash=stable_hash(fixture),
        is_truth=False,
        is_proof=False,
    )


def memory_write_request_tool(*, content: str, key: str = "pending") -> dict[str, Any]:
    return advisory_envelope(
        schema="tool-result-memory-write-request",
        result={"status": "request_recorded", "key": key, "mutated": False},
        content_hash=stable_hash({"key": key, "content": content}),
        write_performed=False,
    )


def proof_read_tool(*, limit: int = 20) -> dict[str, Any]:
    proofs_root = WORKSPACE / "docs" / "proofs"
    bundles: list[dict[str, str]] = []
    if proofs_root.is_dir():
        for child in sorted(proofs_root.iterdir())[:limit]:
            if child.is_dir():
                bundles.append({"name": child.name, "path": str(child.relative_to(WORKSPACE))})
    return advisory_envelope(schema="tool-result-proof-read", result={"bundles": bundles}, is_proof=False)


def proof_verify_tool(*, path: str) -> dict[str, Any]:
    target = WORKSPACE / path
    ok = target.is_dir() or target.is_file()
    return advisory_envelope(
        schema="tool-result-proof-verify",
        result={"path": path, "exists": ok, "verified": ok},
        is_proof=False,
    )


def artifact_read_tool(*, artifact_class: str = "report") -> dict[str, Any]:
    reports = WORKSPACE / "docs" / "reports" / "phases"
    names = [p.name for p in sorted(reports.glob("*.md"))[:15]] if reports.is_dir() else []
    return advisory_envelope(
        schema="tool-result-artifact-read",
        result={"artifact_class": artifact_class, "reports": names},
        metadata_only=True,
    )


def knowledge_lookup_tool(*, query: str) -> dict[str, Any]:
    hits: list[dict[str, str]] = []
    for sub in ("docs/planning", "docs/runbooks"):
        root = WORKSPACE / sub
        if not root.is_dir():
            continue
        for path in root.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if query.lower() in text.lower() or query.lower() in path.name.lower():
                hits.append({"path": str(path.relative_to(WORKSPACE)), "title": path.stem})
            if len(hits) >= 10:
                break
    return advisory_envelope(
        schema="tool-result-knowledge-lookup",
        result={"query": query, "hits": hits, "source": "local_docs"},
        is_proof=False,
        is_truth=False,
    )


def social_draft_tool(*, text: str, platform: str = "local") -> dict[str, Any]:
    draft = {"platform": platform, "text": text, "published": False, "draft_only": True}
    return advisory_envelope(
        schema="tool-result-social-draft",
        result=draft,
        draft_hash=stable_hash(draft),
        is_publication=False,
        live_side_effect=False,
    )


def web_search_request_tool(*, query: str) -> dict[str, Any]:
    return advisory_envelope(
        schema="tool-result-web-search-request",
        result={"query": query, "provider_configured": False, "executed": False, "live_research": False},
        contract_only=True,
        executed=False,
        live_research=False,
    )


def email_draft_tool(*, to: str, subject: str, body: str) -> dict[str, Any]:
    draft = {"to": to, "subject": subject, "body": body, "sent": False, "draft_only": True}
    return advisory_envelope(
        schema="tool-result-email-draft",
        result=draft,
        draft_hash=stable_hash(draft),
        is_publication=False,
        live_side_effect=False,
    )


def account_creation_request_tool(*, site: str) -> dict[str, Any]:
    return advisory_envelope(
        schema="tool-result-account-creation-request",
        result={"site": site, "executed": False},
        operator_review_required=True,
        live_side_effect=False,
    )


def operator_message_tool(*, message: str, subject: str = "agent0-tool-request") -> dict[str, Any]:
    return advisory_envelope(
        schema="tool-result-operator-message",
        result={"subject": subject, "message": message, "delivered": False, "queued_for_operator": True},
    )


def shell_safe_tool(*, command: str) -> dict[str, Any]:
    cmd = command.strip()
    if cmd not in SHELL_ALLOWLIST:
        return advisory_envelope(
            schema="tool-result-shell-safe",
            success=False,
            denied=True,
            result={"command": cmd, "reason": "not_allowlisted"},
        )
    try:
        proc = subprocess.run(
            cmd,
            cwd=WORKSPACE,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        return advisory_envelope(
            schema="tool-result-shell-safe",
            success=proc.returncode == 0,
            denied=False,
            result={"command": cmd, "stdout": proc.stdout[:2000], "stderr": proc.stderr[:500], "exit_code": proc.returncode},
            live_side_effect=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return advisory_envelope(schema="tool-result-shell-safe", success=False, denied=False, result={"error": str(exc)})


def model_inference_tool_stub(*, prompt: str, role: str = "model_inference") -> dict[str, Any]:
    mode_receipt = resolve_runtime_mode()
    receipt = build_provider_receipt(
        provider_id="model_inference_tool_stub",
        provider_kind=ProviderKind.STUB,
        provider_mode=ProviderMode.FALLBACK_STUB,
        role=role,
        request_hash=stable_hash({"prompt": prompt}),
        config_hash=stable_hash({"stub": True}),
        runtime_mode=mode_receipt.runtime_mode.value,
        cognitive_soak_active=mode_receipt.cognitive_soak_active,
        dry_run=False,
        fixture_mode=mode_receipt.fixture_allowed,
        status=ProviderStatus.REFUSED if role.upper() in COGNITIVE_ROLES else ProviderStatus.UNAVAILABLE,
        verdict=(
            ProviderRealityVerdict.RED_PROVIDER_FALLBACK_AS_COGNITION
            if role.upper() in COGNITIVE_ROLES
            else ProviderRealityVerdict.YELLOW_PROVIDER_UNAVAILABLE
        ),
        response_hash=stable_hash({"response": "stub"}),
    )
    response_text = "[advisory inference routed via model provider fabric]"
    return advisory_envelope(
        schema="tool-result-model-inference",
        result={
            "prompt": prompt,
            "response": response_text,
            "provider_mode": ProviderMode.FALLBACK_STUB.value,
            "provider_receipt": receipt.to_payload(),
            "counts_as_cognition": receipt_counts_as_cognition(receipt),
        },
        inference_is_advisory_only=True,
        provider_mode=ProviderMode.FALLBACK_STUB.value,
        counts_as_cognition=False,
    )


def execute_local_tool(capability_id: str, parameters: dict[str, Any], *, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    if capability_id == "capability_manifest":
        return capability_manifest_tool(manifest or {})
    if capability_id == "local_memory_read":
        return memory_read_tool(query=str(parameters.get("query", "")))
    if capability_id == "memory_write_request":
        return memory_write_request_tool(content=str(parameters.get("content", "")), key=str(parameters.get("key", "pending")))
    if capability_id == "proof_read":
        return proof_read_tool(limit=int(parameters.get("limit", 20)))
    if capability_id == "proof_verify":
        return proof_verify_tool(path=str(parameters.get("path", "")))
    if capability_id == "artifact_read":
        return artifact_read_tool(artifact_class=str(parameters.get("artifact_class", "report")))
    if capability_id == "knowledge_lookup":
        return knowledge_lookup_tool(query=str(parameters.get("query", "")))
    if capability_id == "social_draft":
        return social_draft_tool(text=str(parameters.get("text", "")), platform=str(parameters.get("platform", "local")))
    if capability_id == "web_search_request":
        return web_search_request_tool(query=str(parameters.get("query", "")))
    if capability_id == "operator_message":
        return operator_message_tool(message=str(parameters.get("message", "")), subject=str(parameters.get("subject", "agent0-tool-request")))
    if capability_id == "shell_safe":
        return shell_safe_tool(command=str(parameters.get("command", "")))
    if capability_id == "model_inference":
        role = str(parameters.get("role", "AGENT_DRAFT_WRITE"))
        return model_inference_tool_stub(prompt=str(parameters.get("prompt", "")), role=role)
    if capability_id == "email_draft":
        return email_draft_tool(
            to=str(parameters.get("to", "")),
            subject=str(parameters.get("subject", "")),
            body=str(parameters.get("body", parameters.get("message", ""))),
        )
    if capability_id == "account_creation_request":
        return account_creation_request_tool(site=str(parameters.get("site", "")))
    if capability_id == "storage_read":
        return artifact_read_tool(artifact_class="storage")
    if capability_id.startswith("browser_"):
        from hg_runtime.cloud_browser_governance.browser import execute_browser_tool

        return execute_browser_tool(capability_id, parameters)
    return advisory_envelope(schema="tool-result-unknown", success=False, result={"capability_id": capability_id})


__all__ = ["SHELL_ALLOWLIST", "execute_local_tool"]
