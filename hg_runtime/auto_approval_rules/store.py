"""Durable store for auto-approval rules."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.auto_approval_rules.errors import RuleNotFoundError, RuleValidationError
from hg_runtime.auto_approval_rules.policy import is_forbidden_rule_action_type, validate_rule_scope
from hg_runtime.auto_approval_rules.schema import (
    AGENT0_ID,
    AutoApprovalRule,
    AutoApprovalRuleReceipt,
    AutoApprovalRuleStatus,
    new_rule_id,
)

WORKSPACE = Path(__file__).resolve().parents[2]


class AutoApprovalRuleStore:
    def __init__(self, rules_path: Path, receipts_path: Path) -> None:
        self.rules_path = rules_path
        self.receipts_path = receipts_path
        self._usage: dict[str, dict[str, int]] = {}

    @classmethod
    def default(cls, workspace: Path | None = None) -> "AutoApprovalRuleStore":
        root = (workspace or WORKSPACE) / ".hg-local" / "auto_approval_rules"
        return cls(root / "auto_approval_rules.json", root / "auto_approval_receipts.jsonl")

    def load_rules(self) -> list[AutoApprovalRule]:
        if not self.rules_path.is_file():
            return []
        data = json.loads(self.rules_path.read_text(encoding="utf-8"))
        return [AutoApprovalRule.from_payload(r) for r in data.get("rules", [])]

    def save_rules(self, rules: list[AutoApprovalRule]) -> None:
        self.rules_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "auto-approval-rules-store",
            "rules": [r.to_payload() for r in rules],
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }
        tmp = self.rules_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, self.rules_path)

    def append_receipt(self, receipt: AutoApprovalRuleReceipt) -> None:
        self.receipts_path.parent.mkdir(parents=True, exist_ok=True)
        with self.receipts_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(receipt.to_payload(), sort_keys=True) + "\n")

    def get_rule(self, rule_id: str) -> AutoApprovalRule:
        for r in self.load_rules():
            if r.rule_id == rule_id:
                return r
        raise RuleNotFoundError(rule_id)

    def create_rule(
        self,
        *,
        title: str,
        description: str,
        action_type: str,
        allowed_surfaces: list[str],
        max_risk_class: str,
        created_by_operator_ref: str,
        expires_at: str,
        **kwargs: Any,
    ) -> AutoApprovalRule:
        if created_by_operator_ref == AGENT0_ID:
            raise RuleValidationError("agent0 cannot create rules")
        if not expires_at:
            raise RuleValidationError("expires_at required")
        errs = validate_rule_scope(action_type, allowed_surfaces)
        if errs:
            raise RuleValidationError("; ".join(errs))
        if is_forbidden_rule_action_type(action_type):
            raise RuleValidationError(f"forbidden action_type: {action_type}")

        rule = AutoApprovalRule(
            rule_id=new_rule_id(),
            title=title,
            description=description,
            action_type=action_type,
            allowed_surfaces=allowed_surfaces,
            max_risk_class=max_risk_class,
            created_at=datetime.now(timezone.utc).isoformat(),
            created_by_operator_ref=created_by_operator_ref,
            expires_at=expires_at,
            **kwargs,
        )
        rules = self.load_rules()
        rules.append(rule)
        self.save_rules(rules)
        return rule

    def update_rule(self, rule: AutoApprovalRule) -> None:
        rules = self.load_rules()
        for i, r in enumerate(rules):
            if r.rule_id == rule.rule_id:
                rules[i] = rule
                self.save_rules(rules)
                return
        raise RuleNotFoundError(rule.rule_id)

    def increment_usage(self, rule_id: str) -> None:
        u = self._usage.setdefault(rule_id, {"run": 0, "hour": 0, "day": 0})
        u["run"] += 1
        u["hour"] += 1
        u["day"] += 1


__all__ = ["AutoApprovalRuleStore"]
