"""Phase 18 platform proof and live dispatch."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.external_write_authority.incident_plan import find_incident_plan_for_scope
from hg_runtime.external_write_authority.live_permit import load_live_permit
from hg_runtime.external_write_authority.live_smoke import (
    PHASE18_ROOT,
    Phase18Verdict,
    file_sha256,
    get_live_dispatch_count,
    increment_live_dispatch_count,
    load_live_smoke_scope,
    load_phase18_policy,
    phase18_env_configured,
    stop_panic_active,
)
from hg_runtime.external_write_authority.schema import new_id, now_iso
from hg_runtime.social_capability.credentials import load_operator_social_env


@dataclass
class Phase18LiveDispatchResult:
    live_dispatch_result_id: str
    live_permit_ref: str
    platform: str
    action_type: str
    content_sha256: str
    external_side_effect: bool
    dispatched_at: str
    verdict: str
    platform_object_id: str | None = None
    platform_url: str | None = None
    visibility_status: str | None = None
    proof_ref: str | None = None
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "live_dispatch_result_id": self.live_dispatch_result_id,
            "live_permit_ref": self.live_permit_ref,
            "platform": self.platform,
            "action_type": self.action_type,
            "content_sha256": self.content_sha256,
            "external_side_effect": self.external_side_effect,
            "platform_object_id": self.platform_object_id,
            "platform_url": self.platform_url,
            "visibility_status": self.visibility_status,
            "dispatched_at": self.dispatched_at,
            "proof_ref": self.proof_ref,
            "verdict": self.verdict,
            "hash": self.hash,
        }

    def with_hash(self) -> Phase18LiveDispatchResult:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return Phase18LiveDispatchResult(**{**self.__dict__, "hash": compute_record_hash(body)})


@dataclass
class PlatformVisibilityProof:
    platform_proof_id: str
    live_dispatch_result_ref: str
    platform: str
    platform_object_id: str
    platform_url: str
    observed_at: str
    visibility_status: str
    proof_method: str
    verdict: str
    content_sha256_observed: str | None = None
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "platform_proof_id": self.platform_proof_id,
            "live_dispatch_result_ref": self.live_dispatch_result_ref,
            "platform": self.platform,
            "platform_object_id": self.platform_object_id,
            "platform_url": self.platform_url,
            "observed_at": self.observed_at,
            "visibility_status": self.visibility_status,
            "content_sha256_observed": self.content_sha256_observed,
            "proof_method": self.proof_method,
            "verdict": self.verdict,
            "hash": self.hash,
        }

    def with_hash(self) -> PlatformVisibilityProof:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return PlatformVisibilityProof(**{**self.__dict__, "hash": compute_record_hash(body)})


def _results_dir() -> Path:
    return PHASE18_ROOT / "dispatch_results"


def _proofs_dir() -> Path:
    return PHASE18_ROOT / "platform_proofs"


def _parse_content_file(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.strip().splitlines()
    if not lines:
        return "Phase 18 test", text
    first = lines[0].strip()
    if first.startswith("#"):
        title = first.lstrip("#").strip() or "Phase 18 test"
        body = "\n".join(lines[1:]).strip() or text
    else:
        title = first[:120]
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else text
    return title, body


def _moltbook_token_configured() -> bool:
    from hg_platforms.moltbook.moltbook_api_client import moltbook_token_configured

    load_operator_social_env()
    return moltbook_token_configured()


def _moltbook_create_post(*, submolt: str, title: str, content: str) -> dict[str, Any]:
    from hg_platforms.moltbook.moltbook_api_client import moltbook_api_base

    token = (
        os.environ.get("HG_MOLTBOOK_TOKEN")
        or os.environ.get("HG_SOCIAL_MOLTBOOK_TOKEN")
        or os.environ.get("MOLTBOOK_API_KEY")
        or ""
    ).strip()
    if not token:
        return {"ok": False, "error": "credentials_missing"}
    base = moltbook_api_base()
    url = f"{base}/posts"
    payloads = [
        {"submolt_name": submolt, "title": title, "content": content},
        {"submolt": submolt, "title": title, "content": content},
    ]
    last_error: dict[str, Any] = {"ok": False, "error": "platform_rejected"}
    for payload in payloads:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "openclaw-agent-zero/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                data = json.loads(raw)
                post = data.get("post") or data
                post_id = post.get("id") if isinstance(post, dict) else None
                post_url = f"https://www.moltbook.com/post/{post_id}" if post_id else None
                return {"ok": True, "post_id": post_id, "post_url": post_url, "raw": data}
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(err_body)
            except json.JSONDecodeError:
                parsed = {"message": err_body[:500]}
            last_error = {
                "ok": False,
                "error": f"http_{exc.code}",
                "body": err_body[:500],
                "parsed": parsed,
            }
            if exc.code == 400 and payload is payloads[0]:
                continue
            return last_error
        except Exception as exc:  # noqa: BLE001 — surface platform errors without crashing
            return {"ok": False, "error": str(exc)}
    return last_error


def _fake_adapter_dispatch(*, platform: str, action_type: str) -> dict[str, Any]:
    return {
        "ok": True,
        "post_id": "fake-post-id",
        "post_url": f"https://example.test/{platform}/{action_type}/fake",
        "fake": True,
    }


def dispatch_live(*, live_permit_id: str) -> tuple[Phase18LiveDispatchResult | None, list[str]]:
    """Execute one scoped live action. Returns (result, deny_reasons)."""
    policy = load_phase18_policy()
    env = phase18_env_configured()
    deny: list[str] = []

    if not env["allow_live_smoke"]:
        deny.append("RED_LIVE_ACTION_WITHOUT_EXPLICIT_PHASE18_ENV")
    if not env["operator_confirmed"]:
        deny.append("RED_LIVE_ACTION_WITHOUT_OPERATOR_CONFIRMATION")
    if stop_panic_active():
        deny.append("stop_panic_active")
    if get_live_dispatch_count() >= int(policy.get("max_live_actions", 1)):
        deny.append("RED_MULTIPLE_LIVE_ACTIONS")

    permit = load_live_permit(live_permit_id)
    if not permit:
        deny.append("RED_LIVE_ACTION_WITHOUT_LIVE_PERMIT")
        return None, deny
    if permit.is_revoked():
        deny.append("RED_LIVE_ACTION_WITH_REVOKED_PERMIT")
        return None, deny
    if permit.is_expired():
        deny.append("RED_LIVE_ACTION_WITH_EXPIRED_PERMIT")
        return None, deny
    if permit.max_live_actions != 1:
        deny.append("RED_MULTIPLE_LIVE_ACTIONS")

    scope = load_live_smoke_scope(permit.live_smoke_scope_ref)
    if not scope:
        deny.append("RED_LIVE_ACTION_WITHOUT_OPERATOR_SCOPE")
        return None, deny
    if scope.is_expired():
        deny.append("RED_LIVE_ACTION_WITH_STALE_APPROVAL")

    content_path = Path(scope.content_file_ref)
    if not content_path.is_file():
        deny.append("content_file_missing")
        return None, deny
    sha = file_sha256(content_path)
    if sha != permit.content_sha256:
        deny.append("RED_LIVE_ACTION_WITH_CONTENT_HASH_MISMATCH")
        return None, deny
    if env["expected_content_sha256"] and sha != env["expected_content_sha256"]:
        deny.append("RED_LIVE_ACTION_WITH_CONTENT_HASH_MISMATCH")
        return None, deny
    if env["platform"] and env["platform"] != permit.platform:
        deny.append("RED_LIVE_ACTION_WITH_PLATFORM_MISMATCH")
        return None, deny
    if env["action_type"] and env["action_type"] != permit.action_type:
        deny.append("RED_LIVE_ACTION_WITH_ACTION_TYPE_MISMATCH")
        return None, deny

    incident = find_incident_plan_for_scope(scope.scope_id)
    if not incident and policy.get("incident_rollback_plan_required"):
        deny.append("RED_INCIDENT_ROLLBACK_PLAN_MISSING")
        return None, deny

    if deny:
        return None, deny

    if permit.action_type not in ("publish_post",) and permit.platform == "moltbook":
        if permit.action_type in ("reply", "comment"):
            deny.append("RED_LIVE_REPLY_OR_COMMENT_UNSCOPED")
            return None, deny

    use_fake = os.environ.get("HG_PHASE18_USE_FAKE_ADAPTER", "").lower() in ("1", "true", "yes")
    external_side_effect = False
    post_id = None
    post_url = None
    visibility = None
    verdict = Phase18Verdict.YELLOW_READY

    if use_fake:
        api_result = _fake_adapter_dispatch(platform=permit.platform, action_type=permit.action_type)
        verdict = "YELLOW_FAKE_ADAPTER_NOT_LIVE_GREEN"
        post_id = api_result.get("post_id")
        post_url = api_result.get("post_url")
        visibility = "simulated"
    elif permit.platform == "moltbook" and permit.action_type == "publish_post":
        if not env["live_writes_enabled"]:
            deny.append("RED_LIVE_ACTION_WITHOUT_EXPLICIT_PHASE18_ENV")
            return None, deny
        if not _moltbook_token_configured():
            deny.append("YELLOW_PLATFORM_WRITE_CREDENTIALS_MISSING")
            return None, deny
        title, body = _parse_content_file(content_path)
        submolt = os.environ.get("HG_PHASE18_SUBMOLT", "general")
        api_result = _moltbook_create_post(submolt=submolt, title=title, content=body)
        if not api_result.get("ok"):
            deny.append(api_result.get("error", "platform_rejected"))
            return None, deny
        external_side_effect = True
        post_id = api_result.get("post_id")
        post_url = api_result.get("post_url")
        visibility = "published" if post_id else "visibility_delayed"
        verdict = Phase18Verdict.GREEN if post_id and post_url else Phase18Verdict.YELLOW_VISIBILITY
    else:
        deny.append("YELLOW_PHASE_18_READY_FOR_OPERATOR_LIVE_SCOPE")
        return None, deny

    if external_side_effect or use_fake:
        increment_live_dispatch_count()

    result = Phase18LiveDispatchResult(
        live_dispatch_result_id=new_id("p18-live-dispatch"),
        live_permit_ref=live_permit_id,
        platform=permit.platform,
        action_type=permit.action_type,
        content_sha256=sha,
        external_side_effect=external_side_effect,
        platform_object_id=post_id,
        platform_url=post_url,
        visibility_status=visibility,
        dispatched_at=now_iso(),
        verdict=verdict,
    ).with_hash()

    path = _results_dir()
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{result.live_dispatch_result_id}.json").write_text(
        json.dumps(result.to_payload(), indent=2) + "\n", encoding="utf-8"
    )
    return result, deny


def load_dispatch_result(result_id: str) -> Phase18LiveDispatchResult | None:
    path = _results_dir() / f"{result_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return Phase18LiveDispatchResult(
        live_dispatch_result_id=data["live_dispatch_result_id"],
        live_permit_ref=data["live_permit_ref"],
        platform=data["platform"],
        action_type=data["action_type"],
        content_sha256=data["content_sha256"],
        external_side_effect=data["external_side_effect"],
        platform_object_id=data.get("platform_object_id"),
        platform_url=data.get("platform_url"),
        visibility_status=data.get("visibility_status"),
        dispatched_at=data["dispatched_at"],
        proof_ref=data.get("proof_ref"),
        verdict=data["verdict"],
        hash=data.get("hash"),
    )


def verify_platform_proof(*, dispatch_result_id: str) -> PlatformVisibilityProof | None:
    result = load_dispatch_result(dispatch_result_id)
    if not result or not result.external_side_effect:
        return None
    if not result.platform_object_id and not result.platform_url:
        return None

    proof_method = "api_readback"
    visibility = result.visibility_status or "unknown"
    verdict = Phase18Verdict.GREEN

    if result.platform == "moltbook" and result.platform_object_id:
        from hg_platforms.moltbook.moltbook_api_client import fetch_moltbook_feed, moltbook_token_configured

        load_operator_social_env()
        if moltbook_token_configured():
            try:
                from hg_platforms.moltbook.moltbook_api_client import moltbook_api_base, _http_get

                token = (
                    os.environ.get("HG_MOLTBOOK_TOKEN")
                    or os.environ.get("HG_SOCIAL_MOLTBOOK_TOKEN")
                    or ""
                ).strip()
                base = moltbook_api_base()
                status, data = _http_get(
                    f"{base}/posts/{result.platform_object_id}",
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                )
                if status == 200 and isinstance(data, dict):
                    visibility = "visible"
                elif status == 404:
                    visibility = "not_found"
                    verdict = Phase18Verdict.YELLOW_VISIBILITY
                else:
                    visibility = "visibility_delayed"
                    verdict = Phase18Verdict.YELLOW_VISIBILITY
            except Exception:
                visibility = "visibility_delayed"
                verdict = Phase18Verdict.YELLOW_VISIBILITY
        else:
            visibility = "visibility_delayed"
            verdict = Phase18Verdict.YELLOW_VISIBILITY

    proof = PlatformVisibilityProof(
        platform_proof_id=new_id("p18-proof"),
        live_dispatch_result_ref=dispatch_result_id,
        platform=result.platform,
        platform_object_id=result.platform_object_id or "",
        platform_url=result.platform_url or "",
        observed_at=now_iso(),
        visibility_status=visibility,
        content_sha256_observed=result.content_sha256,
        proof_method=proof_method,
        verdict=verdict,
    ).with_hash()

    path = _proofs_dir()
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{proof.platform_proof_id}.json").write_text(
        json.dumps(proof.to_payload(), indent=2) + "\n", encoding="utf-8"
    )

    updated = Phase18LiveDispatchResult(
        **{**result.__dict__, "proof_ref": proof.platform_proof_id, "visibility_status": visibility}
    ).with_hash()
    (_results_dir() / f"{dispatch_result_id}.json").write_text(
        json.dumps(updated.to_payload(), indent=2) + "\n", encoding="utf-8"
    )
    return proof
