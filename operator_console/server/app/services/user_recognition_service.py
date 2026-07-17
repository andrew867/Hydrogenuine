"""User cognitive recognition operator service (G16)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.consent.ledger import ConsentLedger
from hg_core.repr_interp.templates import load_templates
from hg_core.repr_interp.user_recognition import is_user_recognition_enabled, recognize_user, recognition_status


def _workspace_root() -> Path:
    try:
        from hg_lib.config import get_workspace_root

        return Path(get_workspace_root())
    except Exception:
        return Path(".")


def _require_feature() -> Optional[Dict[str, Any]]:
    if not is_user_recognition_enabled():
        return {"ok": False, "error": "user_recognition_disabled"}
    return None


def get_user_recognition_status(subject_id: str) -> Dict[str, Any]:
    blocked = _require_feature()
    if blocked:
        return blocked
    return recognition_status(subject_id=subject_id, workspace_root=_workspace_root())


def analyze_user_recognition(
    *,
    subject_id: str,
    interaction: Dict[str, Any],
    purpose: str = "operator_panel",
    proof_bundle_ref: Optional[str] = None,
) -> Dict[str, Any]:
    blocked = _require_feature()
    if blocked:
        return blocked
    try:
        return recognize_user(
            subject_id=subject_id,
            interaction=interaction,
            workspace_root=_workspace_root(),
            purpose=purpose,
            proof_bundle_ref=proof_bundle_ref,
        )
    except Exception as exc:
        from hg_core.consent.errors import ConsentDeniedError

        if isinstance(exc, ConsentDeniedError):
            return {"ok": False, "error": "consent_required", "subject_id": subject_id}
        raise


def list_kinship_templates() -> Dict[str, Any]:
    blocked = _require_feature()
    if blocked:
        return {**blocked, "templates": []}
    templates = load_templates(_workspace_root())
    return {"ok": True, "templates": templates, "count": len(templates)}


def seed_user_recognition_demo() -> Dict[str, Any]:
    blocked = _require_feature()
    if blocked:
        return blocked
    root = _workspace_root()
    fixtures_src = root / "evals" / "g16" / "user_recognition" / "fixtures.json"
    if not fixtures_src.exists():
        bundled = Path(__file__).resolve().parents[4] / "evals" / "g16" / "user_recognition" / "fixtures.json"
        if bundled.exists():
            dest = root / "evals" / "g16" / "user_recognition"
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy(bundled, dest / "fixtures.json")
    fixtures = json.loads((root / "evals" / "g16" / "user_recognition" / "fixtures.json").read_text(encoding="utf-8"))
    ledger = ConsentLedger(path=root / "memory" / "governance" / "consent_ledger.jsonl")
    seeded = []
    for grant in fixtures.get("seed_grants") or []:
        seeded.append(
            ledger.grant(
                subject_id=str(grant["subject_id"]),
                consent_class=str(grant["consent_class"]),
                purpose=str(grant.get("purpose") or "demo"),
                granted_by=str(grant.get("granted_by") or "operator"),
                expires_at=grant.get("expires_at"),
            )
        )
    sample = fixtures.get("sample_interactions") or {}
    telex = analyze_user_recognition(
        subject_id="demo-user",
        interaction=sample.get("telex_lennon_style") or {"messages": []},
        purpose="seed_demo",
    )
    return {
        "ok": True,
        "seeded_grants": len(seeded),
        "template_count": len(load_templates(root)),
        "demo_recognition": telex,
    }
