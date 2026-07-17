"""
Pack 6: Reality contracts — schema/replay/policy/tool contracts, breaking-change detection.
REALITY_CONTRACT_PUBLISHED.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def publish_reality_contract(
    *,
    contract_id: str,
    version: str,
    rules: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    required_suites: Optional[List[str]] = None,
) -> str:
    """
    Write contract artifact to artifacts/contracts/reality_contract.json (or contract_id.json),
    emit REALITY_CONTRACT_PUBLISHED. Returns event_id.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    root = workspace_root / "artifacts" / "contracts"
    root.mkdir(parents=True, exist_ok=True)
    doc = {
        "contract_id": contract_id,
        "version": version,
        "rules": rules,
        "required_suites": required_suites or [],
        "published_ts": ts,
    }
    path = root / "reality_contract.json"
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return emit(
        "REALITY_CONTRACT_PUBLISHED",
        "reality_contract",
        contract_id,
        {"contract_id": contract_id, "version": version, "artifact_id": str(path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def load_reality_contract(workspace_root: Path) -> Optional[Dict[str, Any]]:
    """Load the active reality contract from artifacts/contracts (reality_contract.yaml or .json)."""
    root = workspace_root / "artifacts" / "contracts"
    for name in ("reality_contract.yaml", "reality_contract.json"):
        path = root / name
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
            if name.endswith(".yaml"):
                try:
                    import yaml
                    return yaml.safe_load(text)
                except ImportError:
                    continue
            return json.loads(text)
        except (json.JSONDecodeError, OSError):
            continue
    for p in root.glob("*.json"):
        if p.name.startswith("reality") or "contract" in p.name:
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
    return None


def check_breaking_change(
    workspace_root: Path,
    contract: Dict[str, Any],
    *,
    schema_version_before: Optional[str] = None,
    schema_version_after: Optional[str] = None,
    policy_diff_risk_attached: bool = False,
) -> tuple[bool, List[Dict[str, Any]]]:
    """
    Check if proposed change violates contract rules. Returns (is_breaking, list of violations).
    rules may include: require_schema_compat, require_policy_diff_risk, require_deprecation_window.
    """
    violations: List[Dict[str, Any]] = []
    rules = contract.get("rules") or {}
    if schema_version_before is not None and schema_version_after is not None:
        if rules.get("require_schema_compat") and schema_version_before != schema_version_after:
            violations.append({
                "rule": "require_schema_compat",
                "detail": f"schema version change {schema_version_before} -> {schema_version_after}",
            })
    if rules.get("require_policy_diff_risk") and not policy_diff_risk_attached:
        violations.append({"rule": "require_policy_diff_risk", "detail": "policy change must attach diff risk report"})
    return len(violations) == 0, violations
