"""EXCITON Phase 3 local control API — 127.0.0.1 only, routes through boundary."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from hg_runtime.auto_approval_rules.store import AutoApprovalRuleStore
from hg_runtime.exciton.action_handlers import handle_control
from hg_runtime.exciton.control_matrix import get_matrix
from hg_runtime.exciton.agent_zero_review_data_sources import build_agent_zero_review_snapshot_fields
from hg_runtime.exciton.data_sources import CollectorContext
from hg_runtime.exciton.gate_helpers import scan_forbidden
from hg_runtime.exciton.status_aggregator import AggregatorConfig, build_snapshot
from hg_runtime.operator_action_queue.queue import open_default_queue
from hg_runtime.web_action_queue.queue import open_web_queue

WORKSPACE = Path(__file__).resolve().parents[2]


@dataclass
class ExcitonControlAPI:
    workspace: Path = field(default_factory=lambda: WORKSPACE)
    run_dir: Path | None = None
    offline_fixture: bool = False

    def _base_payload(self, extra: dict | None = None) -> dict[str, Any]:
        body = {
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }
        if extra:
            body.update(extra)
        return body

    def get_status(self) -> dict[str, Any]:
        snap = build_snapshot(AggregatorConfig(offline_fixture=self.offline_fixture, allow_network=False))
        payload = snap.to_payload()
        ctx_fields = build_agent_zero_review_snapshot_fields(
            CollectorContext(offline_fixture=self.offline_fixture, allow_network=False)
        )
        return self._base_payload(
            {
                "ok": True,
                "decision": "ALLOW_READ_ONLY",
                "control_id": "REFRESH_STATUS",
                "receipt_ref": "",
                "human_message": "Status snapshot loaded",
                "snapshot": payload,
                "updated_snapshot_hash": payload.get("snapshot_hash"),
                **ctx_fields,
            }
        )

    def get_control_matrix(self) -> dict[str, Any]:
        return self._base_payload(
            {
                "ok": True,
                "decision": "ALLOW_READ_ONLY",
                "control_id": "REFRESH_STATUS",
                "receipt_ref": "",
                "human_message": "Control matrix",
                "matrix": get_matrix(),
            }
        )

    def post_control(self, body: dict[str, Any]) -> dict[str, Any]:
        control_id = str(body.get("control_id", "")).upper()
        payload = dict(body.get("payload") or {})
        payload["workspace"] = str(self.workspace)
        if self.run_dir:
            payload.setdefault("run_dir", str(self.run_dir))
        resp = handle_control(control_id, payload)
        return self._scrub(resp)

    def get_operator_queue(self) -> dict[str, Any]:
        q = open_default_queue(self.workspace)
        items = [i.to_payload() for i in q.list_items()]
        return self._base_payload(
            {
                "ok": True,
                "decision": "ALLOW_READ_ONLY",
                "control_id": "REFRESH_STATUS",
                "receipt_ref": "",
                "human_message": f"{len(items)} queue items",
                "items": items,
            }
        )

    def _control_payload(self, body: dict | None = None) -> dict[str, Any]:
        payload = dict(body or {})
        payload["workspace"] = str(self.workspace)
        if self.run_dir:
            payload.setdefault("run_dir", str(self.run_dir))
        return payload

    def approve_queue_item(self, item_id: str, body: dict | None = None) -> dict[str, Any]:
        body = self._control_payload(body)
        body["queue_item_id"] = unquote(item_id)
        return self._scrub(handle_control("APPROVE_ACTION_ITEM", body))

    def deny_queue_item(self, item_id: str, body: dict | None = None) -> dict[str, Any]:
        body = self._control_payload(body)
        body["queue_item_id"] = unquote(item_id)
        body.setdefault("reason", "operator_denied")
        return self._scrub(handle_control("DENY_ACTION_ITEM", body))

    def expire_queue_item(self, item_id: str, body: dict | None = None) -> dict[str, Any]:
        body = self._control_payload(body)
        body["queue_item_id"] = unquote(item_id)
        body.setdefault("reason", "expired")
        return self._scrub(handle_control("EXPIRE_ACTION_ITEM", body))

    def get_web_actions(self) -> dict[str, Any]:
        wq = open_web_queue(self.workspace, live_browser_enabled=False)
        items = [i.to_payload() for i in wq.list_items()]
        return self._base_payload(
            {
                "ok": True,
                "decision": "ALLOW_READ_ONLY",
                "control_id": "REFRESH_STATUS",
                "receipt_ref": "",
                "human_message": f"{len(items)} web actions",
                "items": items,
            }
        )

    def enqueue_web_action(self, body: dict[str, Any]) -> dict[str, Any]:
        kind = str(body.get("kind", "read")).lower()
        mapping = {
            "read": "ENQUEUE_WEB_READ",
            "click": "ENQUEUE_WEB_CLICK",
            "download": "ENQUEUE_WEB_DOWNLOAD",
        }
        control_id = mapping.get(kind, "ENQUEUE_WEB_READ")
        payload = self._control_payload(body)
        return self._scrub(handle_control(control_id, payload))

    def get_auto_approval_rules(self) -> dict[str, Any]:
        store = AutoApprovalRuleStore.default(self.workspace)
        rules = [r.to_payload() for r in store.load_rules()]
        return self._base_payload(
            {
                "ok": True,
                "decision": "ALLOW_READ_ONLY",
                "control_id": "REFRESH_STATUS",
                "receipt_ref": "",
                "human_message": f"{len(rules)} rules",
                "rules": rules,
            }
        )

    def create_auto_rule(self, body: dict[str, Any]) -> dict[str, Any]:
        if not body.get("operator_ref"):
            return self._base_payload(
                {
                    "ok": False,
                    "decision": "DENY",
                    "control_id": "CREATE_AUTO_APPROVAL_RULE",
                    "receipt_ref": "",
                    "human_message": "operator_ref required",
                    "disabled_reason": "operator_ref required",
                }
            )
        return self._scrub(handle_control("CREATE_AUTO_APPROVAL_RULE", self._control_payload(body)))

    def revoke_auto_rule(self, rule_id: str, body: dict | None = None) -> dict[str, Any]:
        payload = self._control_payload(body)
        payload["rule_id"] = unquote(rule_id)
        return self._scrub(handle_control("REVOKE_AUTO_APPROVAL_RULE", payload))

    def soak_pause_publish(self, body: dict | None = None) -> dict[str, Any]:
        return self._scrub(handle_control("PAUSE_PUBLISH", self._control_payload(body)))

    def soak_resume_approved_only(self, body: dict | None = None) -> dict[str, Any]:
        return self._scrub(handle_control("RESUME_APPROVED_ONLY", self._control_payload(body)))

    def soak_change_approval_mode(self, body: dict | None = None) -> dict[str, Any]:
        return self._scrub(handle_control("CHANGE_APPROVAL_MODE", self._control_payload(body)))

    def soak_stop(self) -> dict[str, Any]:
        return self._scrub(handle_control("STOP_SOAK", self._control_payload()))

    def soak_panic(self) -> dict[str, Any]:
        return self._scrub(handle_control("PANIC_STOP", self._control_payload()))

    def get_situational_awareness(self) -> dict[str, Any]:
        from hg_runtime.exciton.away_digest import build_away_digest, mark_operator_seen
        from hg_runtime.exciton.alerts import build_alert_strip
        from hg_runtime.exciton.data_freshness import assess_freshness
        from hg_runtime.exciton.decision_timeline import build_decision_timeline
        from hg_runtime.exciton.chrono_expiry import clock_confidence_payload
        from hg_runtime.bounded_soak.stop_panic_runtime import operator_semantics, stop_panic_state

        snap = build_snapshot(AggregatorConfig(offline_fixture=self.offline_fixture, allow_network=False))
        gen = snap.generated_at
        return self._base_payload(
            {
                "ok": True,
                "decision": "ALLOW_READ_ONLY",
                "control_id": "REFRESH_STATUS",
                "receipt_ref": "",
                "human_message": "Situational awareness bundle",
                "freshness": assess_freshness(generated_at=gen),
                "away_digest": build_away_digest(workspace=self.workspace),
                "alerts": build_alert_strip(snapshot_generated_at=gen),
                "timeline": build_decision_timeline(workspace=self.workspace),
                "chrono": clock_confidence_payload(),
                "stop_panic": {
                    "state": stop_panic_state(self.workspace).__dict__,
                    "semantics": operator_semantics(),
                },
            }
        )

    def mark_operator_seen(self) -> dict[str, Any]:
        from hg_runtime.exciton.away_digest import mark_operator_seen

        return self._base_payload(
            {
                "ok": True,
                "decision": "ALLOW_READ_ONLY",
                "control_id": "MARK_OPERATOR_SEEN",
                "receipt_ref": "",
                "human_message": "Operator seen timestamp updated",
                "seen": mark_operator_seen(),
            }
        )

    def route(self, method: str, path: str, body: bytes | None = None) -> tuple[int, dict[str, Any]]:
        parsed: dict[str, Any] = {}
        if body:
            try:
                parsed = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                return 400, self._base_payload(
                    {
                        "ok": False,
                        "decision": "DENY",
                        "control_id": "UNKNOWN",
                        "receipt_ref": "",
                        "human_message": "invalid JSON",
                        "errors": ["invalid_json"],
                    }
                )

        path = path.rstrip("/") or "/"
        if method == "GET" and path == "/api/exciton/status":
            return 200, self.get_status()
        if method == "GET" and path == "/api/exciton/control-matrix":
            return 200, self.get_control_matrix()
        if method == "POST" and path == "/api/exciton/control":
            return 200, self.post_control(parsed)
        if method == "GET" and path == "/api/exciton/operator-queue":
            return 200, self.get_operator_queue()
        if method == "GET" and path == "/api/exciton/web-actions":
            return 200, self.get_web_actions()
        if method == "POST" and path == "/api/exciton/web-actions/enqueue":
            return 200, self.enqueue_web_action(parsed)
        if method == "GET" and path == "/api/exciton/auto-approval-rules":
            return 200, self.get_auto_approval_rules()

        if method == "POST" and path == "/api/exciton/auto-approval-rules/create":
            return 200, self.create_auto_rule(parsed)
        if method == "POST" and path.startswith("/api/exciton/auto-approval-rules/") and path.endswith("/revoke"):
            rule_id = path.split("/")[4]
            return 200, self.revoke_auto_rule(rule_id, parsed)
        if method == "POST" and path.startswith("/api/exciton/operator-queue/") and path.endswith("/approve"):
            item_id = path.split("/")[4]
            return 200, self.approve_queue_item(item_id, parsed)
        if method == "POST" and path.startswith("/api/exciton/operator-queue/") and path.endswith("/deny"):
            item_id = path.split("/")[4]
            return 200, self.deny_queue_item(item_id, parsed)
        if method == "POST" and path.startswith("/api/exciton/operator-queue/") and path.endswith("/expire"):
            item_id = path.split("/")[4]
            return 200, self.expire_queue_item(item_id, parsed)
        if method == "POST" and path == "/api/exciton/soak/pause-publish":
            return 200, self.soak_pause_publish(parsed)
        if method == "POST" and path == "/api/exciton/soak/resume-approved-only":
            return 200, self.soak_resume_approved_only(parsed)
        if method == "POST" and path == "/api/exciton/soak/change-approval-mode":
            return 200, self.soak_change_approval_mode(parsed)
        if method == "POST" and path == "/api/exciton/soak/stop":
            return 200, self.soak_stop()
        if method == "POST" and path == "/api/exciton/soak/panic":
            return 200, self.soak_panic()
        if method == "GET" and path == "/api/exciton/situational-awareness":
            return 200, self.get_situational_awareness()
        if method == "POST" and path == "/api/exciton/operator-seen":
            return 200, self.mark_operator_seen()

        return 404, self._base_payload(
            {
                "ok": False,
                "decision": "DENY",
                "control_id": "UNKNOWN",
                "receipt_ref": "",
                "human_message": "not found",
                "errors": [f"unknown path: {path}"],
            }
        )

    def _scrub(self, resp: dict[str, Any]) -> dict[str, Any]:
        bad = scan_forbidden(resp)
        if bad:
            resp = dict(resp)
            resp["errors"] = list(resp.get("errors") or []) + [f"RED_SECRET_LEAK:{bad[0]}"]
            resp["ok"] = False
        return self._base_payload(resp) if "advisory_only" not in resp else resp


__all__ = ["ExcitonControlAPI"]
