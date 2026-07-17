from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


def _string_list(value: Any, *, lowercase: bool = True) -> List[str]:
    if not isinstance(value, list):
        return []
    items: List[str] = []
    for item in value:
        text = str(item or "").strip()
        if not text:
            continue
        items.append(text.lower() if lowercase else text)
    return items


def normalize_approval_rule(rule: Any) -> Dict[str, Any]:
    if not isinstance(rule, dict):
        return {}
    normalized = {
        "id": str(rule.get("id") or "").strip(),
        "label": str(rule.get("label") or "").strip(),
        "enabled": bool(rule.get("enabled", True)),
        "decision": str(rule.get("decision") or "auto_approve").strip().lower() or "auto_approve",
        "kinds": _string_list(rule.get("kinds")),
        "risks": _string_list(rule.get("risks")),
        "workflow_ids": _string_list(rule.get("workflow_ids"), lowercase=False),
        "platforms": _string_list(rule.get("platforms")),
        "modes": _string_list(rule.get("modes")),
    }
    return normalized


def normalize_approval_rules(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rules: List[Dict[str, Any]] = []
    for raw in value:
        rule = normalize_approval_rule(raw)
        if rule:
            rules.append(rule)
    return rules


def _rule_matches(
    rule: Dict[str, Any],
    *,
    kind: str,
    risk: str,
    workflow_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> bool:
    payload = payload or {}
    if not rule.get("enabled", True):
        return False
    if rule.get("decision") != "auto_approve":
        return False

    comparisons = {
        "kinds": (str(kind or "").strip().lower(), rule.get("kinds") or []),
        "risks": (str(risk or "").strip().lower(), rule.get("risks") or []),
        "workflow_ids": (str(workflow_id or "").strip(), rule.get("workflow_ids") or []),
        "platforms": (str(payload.get("platform") or "").strip().lower(), rule.get("platforms") or []),
        "modes": (str(payload.get("mode") or "").strip().lower(), rule.get("modes") or []),
    }
    for _, (actual, allowed) in comparisons.items():
        if allowed and actual not in allowed:
            return False
    return True


def iter_legacy_auto_approve_rules(settings: Optional[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    if not isinstance(settings, dict):
        return []
    for kind in _string_list(settings.get("auto_approve_kinds")):
        yield {
            "id": f"legacy:{kind}",
            "label": f"Auto-approve {kind}",
            "enabled": True,
            "decision": "auto_approve",
            "kinds": [kind],
            "risks": [],
            "workflow_ids": [],
            "platforms": [],
            "modes": [],
        }


def get_effective_approval_rules(settings: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(settings, dict):
        return []
    rules = list(iter_legacy_auto_approve_rules(settings))
    rules.extend(normalize_approval_rules(settings.get("approval_rules")))
    return rules


def evaluate_auto_approval(
    settings: Optional[Dict[str, Any]],
    *,
    kind: str,
    risk: str,
    workflow_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    payload = payload or {}
    for rule in get_effective_approval_rules(settings):
        if _rule_matches(rule, kind=kind, risk=risk, workflow_id=workflow_id, payload=payload):
            return rule
    return None


def build_auto_approval_note(rule: Optional[Dict[str, Any]], *, workflow_id: Optional[str] = None) -> str:
    if rule and rule.get("label"):
        return f"Auto-approved by policy: {rule['label']}"
    if workflow_id:
        return f"Auto-approved by policy for {workflow_id}"
    return "Auto-approved by policy"
