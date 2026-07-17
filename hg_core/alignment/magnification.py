"""
Pack2-03: Alignment magnification — rule-based risk amplification.

Takes planned_action (tool_name, inputs) + optional context and produces
MagnificationReport: risk_score, reasons, required_controls, suggested_tests.
Used by gateway to set approval risk and step-up requirements for tool invocations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

# Default when no rule matches or YAML unavailable
_DEFAULT_RISK_SCORE = 50
_DEFAULT_CONTROLS = {
    "step_up_auth": "basic",
    "approval": True,
    "sandbox": False,
    "redact": False,
}
_DEFAULT_REASONS = ["No specific rule matched; applying default write-tool controls."]


def _rules_path() -> Path:
    return Path(__file__).resolve().parent / "rules" / "magnification_rules.yaml"


def _load_rules() -> List[Dict[str, Any]]:
    path = _rules_path()
    if not path.exists() or yaml is None:
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    return [r for r in raw if isinstance(r, dict)]


def _match_rule(rule: Dict[str, Any], tool_name: str) -> bool:
    match = rule.get("match") or {}
    if not isinstance(match, dict):
        return False
    exact = match.get("tool_name")
    if exact is not None and exact == tool_name:
        return True
    prefix = match.get("tool_name_prefix")
    if prefix is not None and (isinstance(prefix, str) and tool_name.startswith(prefix)):
        return True
    return False


def run_magnify(
    planned_action: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run rule-based magnification. Returns MagnificationReport with:
    risk_score (0-100), reasons[], required_controls{}, suggested_tests[].

    planned_action must have "tool_name" (str). Optional "inputs" for future use.
    """
    tool_name = (planned_action or {}).get("tool_name") or ""
    if not isinstance(tool_name, str):
        tool_name = str(tool_name)
    context = context or {}

    rules = _load_rules()
    # Prefer exact match, then prefix match (first match wins; order in YAML matters)
    matched: Optional[Dict[str, Any]] = None
    for r in rules:
        if _match_rule(r, tool_name):
            matched = r
            break

    if matched is None:
        risk_score = _DEFAULT_RISK_SCORE
        reasons = _DEFAULT_REASONS
        required_controls = dict(_DEFAULT_CONTROLS)
        suggested_tests: List[str] = []
    else:
        risk_score = int(matched.get("risk_score", _DEFAULT_RISK_SCORE))
        risk_score = max(0, min(100, risk_score))
        raw_reasons = matched.get("reasons") or _DEFAULT_REASONS
        reasons = [str(r) for r in raw_reasons] if raw_reasons else _DEFAULT_REASONS
        raw_controls = matched.get("required_controls") or _DEFAULT_CONTROLS
        required_controls = {
            "step_up_auth": raw_controls.get("step_up_auth", _DEFAULT_CONTROLS["step_up_auth"]),
            "approval": bool(raw_controls.get("approval", _DEFAULT_CONTROLS["approval"])),
            "sandbox": bool(raw_controls.get("sandbox", _DEFAULT_CONTROLS["sandbox"])),
            "redact": bool(raw_controls.get("redact", _DEFAULT_CONTROLS["redact"])),
        }
        suggested_tests = list(matched.get("suggested_tests") or [])
        if suggested_tests and not isinstance(suggested_tests[0], str):
            suggested_tests = []

    return {
        "risk_score": risk_score,
        "reasons": reasons,
        "required_controls": required_controls,
        "suggested_tests": suggested_tests,
    }


# Type alias for API/docs
MagnificationReport = Dict[str, Any]
