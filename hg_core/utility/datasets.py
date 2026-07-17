"""
Pack 22: Utility datasets loader and validation.
Load outcomes_v1, probe suites, templates, targets. Validate unique outcome_id, required fields, tag allowlist.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Default base path: repo root / datasets / utility
def _default_base() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "datasets" / "utility"


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def get_tag_allowlist(outcomes: List[Dict[str, Any]], suites: Dict[str, Any], targets: Dict[str, Any]) -> set:
    """Build allowlist from outcomes tags + suite tag_focus/pair_rules + target weights."""
    allow = set()
    for o in outcomes:
        for t in o.get("tags") or []:
            allow.add(str(t))
    for sid, s in (suites or {}).items():
        if isinstance(s, dict):
            for t in s.get("tag_focus") or []:
                allow.add(str(t))
            pr = s.get("pair_rules") or {}
            for t in pr.get("include_tags") or []:
                allow.add(str(t))
            for t in pr.get("anti_tags") or []:
                allow.add(str(t))
    for tid, t in (targets or {}).items():
        if isinstance(t, dict) and "weights" in t:
            for k in t["weights"]:
                allow.add(str(k))
    return allow


def validate_outcomes(
    outcomes: List[Dict[str, Any]],
    tag_allowlist: Optional[set] = None,
) -> Tuple[bool, List[str]]:
    """Validate: unique outcome_id, required fields (outcome_id, text, tags), tags in allowlist."""
    errors: List[str] = []
    seen: set = set()
    for i, o in enumerate(outcomes):
        oid = o.get("outcome_id")
        if not oid:
            errors.append(f"outcome index {i}: missing outcome_id")
            continue
        if oid in seen:
            errors.append(f"duplicate outcome_id: {oid}")
        seen.add(oid)
        if not o.get("text"):
            errors.append(f"outcome {oid}: missing text")
        tags = o.get("tags")
        if not isinstance(tags, list):
            errors.append(f"outcome {oid}: tags must be a list")
        elif tag_allowlist is not None:
            for t in tags:
                if t not in tag_allowlist:
                    errors.append(f"outcome {oid}: tag {t!r} not in allowlist")
    return len(errors) == 0, errors


def validate_suites(suites: Dict[str, Any], tag_allowlist: set) -> Tuple[bool, List[str]]:
    """Validate suite definitions reference valid tags."""
    errors: List[str] = []
    for sid, s in (suites or {}).items():
        if not isinstance(s, dict):
            continue
        for t in s.get("tag_focus") or []:
            if t not in tag_allowlist:
                errors.append(f"suite {sid}: tag_focus {t!r} not in allowlist")
        pr = s.get("pair_rules") or {}
        for t in pr.get("include_tags") or []:
            if t not in tag_allowlist:
                errors.append(f"suite {sid}: include_tags {t!r} not in allowlist")
        for t in pr.get("anti_tags") or []:
            if t not in tag_allowlist:
                errors.append(f"suite {sid}: anti_tags {t!r} not in allowlist")
    return len(errors) == 0, errors


def validate_targets(targets: Dict[str, Any], tag_allowlist: set) -> Tuple[bool, List[str]]:
    """Validate target profiles reference valid tags."""
    errors: List[str] = []
    for tid, t in (targets or {}).items():
        if not isinstance(t, dict) or "weights" not in t:
            continue
        for k in t["weights"]:
            if k not in tag_allowlist:
                errors.append(f"target {tid}: weight key {k!r} not in allowlist")
    return len(errors) == 0, errors


def load_outcomes_v1(base: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load outcomes_v1 outcomes.jsonl. Returns list of outcome dicts."""
    base = base or _default_base()
    path = base / "outcomes_v1" / "outcomes.jsonl"
    if not path.exists():
        return []
    return _read_jsonl(path)


def load_suites(base: Optional[Path] = None) -> Dict[str, Any]:
    """Load probe_suites/suites.json."""
    base = base or _default_base()
    path = base / "probe_suites" / "suites.json"
    if not path.exists():
        return {}
    return _read_json(path)


def load_templates(base: Optional[Path] = None) -> Dict[str, Any]:
    """Load prompts/templates.json."""
    base = base or _default_base()
    path = base / "prompts" / "templates.json"
    if not path.exists():
        return {}
    return _read_json(path)


def load_targets_v1(base: Optional[Path] = None) -> Dict[str, Any]:
    """Load targets/targets_v1.json."""
    base = base or _default_base()
    path = base / "targets" / "targets_v1.json"
    if not path.exists():
        return {}
    return _read_json(path)


def load_and_validate_outcomes_v1(base: Optional[Path] = None) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Load outcomes_v1, suites, targets; build allowlist; validate outcomes and suites/targets.
    Returns (outcomes, error_message or None).
    """
    base = base or _default_base()
    outcomes = load_outcomes_v1(base)
    if not outcomes:
        return [], "no outcomes loaded"
    suites = load_suites(base)
    targets = load_targets_v1(base)
    allowlist = get_tag_allowlist(outcomes, suites, targets)
    ok, errs = validate_outcomes(outcomes, allowlist)
    if not ok:
        return outcomes, "; ".join(errs[:5])
    ok, errs = validate_suites(suites, allowlist)
    if not ok:
        return outcomes, "; ".join(errs[:5])
    ok, errs = validate_targets(targets, allowlist)
    if not ok:
        return outcomes, "; ".join(errs[:5])
    return outcomes, None
