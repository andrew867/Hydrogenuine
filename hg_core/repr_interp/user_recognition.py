"""User cognitive recognition engine (G16 / telex)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from hg_core.consent import assert_recognition_consent, resolve_consent_class

from .geometry import blend_geometry, cosine_similarity, geometry_from_interaction
from .recognition_trace import RecognitionTraceStore
from .templates import load_templates


def is_user_recognition_enabled() -> bool:
    return os.environ.get("HG_USER_RECOGNITION_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _workspace_root(workspace_root: Optional[Path] = None) -> Path:
    if workspace_root is not None:
        return Path(workspace_root)
    try:
        from hg_lib.config import get_workspace_root

        return Path(get_workspace_root())
    except Exception:
        return Path(".")


def _thresholds(workspace_root: Path) -> Dict[str, Any]:
    fixtures = workspace_root / "evals" / "g16" / "user_recognition" / "fixtures.json"
    if fixtures.exists():
        return json.loads(fixtures.read_text(encoding="utf-8")).get("thresholds") or {}
    return {"kinship_min_similarity": 0.82, "near_match_min_similarity": 0.7}


def match_kinship(
    geometry: Mapping[str, float],
    templates: List[Dict[str, Any]],
    *,
    kinship_min: float = 0.82,
    near_min: float = 0.7,
) -> List[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    for template in templates:
        tmpl_geo = template.get("geometry") or {}
        similarity = cosine_similarity(geometry, tmpl_geo)
        kinship = similarity >= kinship_min
        near = similarity >= near_min
        matches.append(
            {
                "template_id": template.get("template_id"),
                "label": template.get("label"),
                "similarity": round(similarity, 4),
                "kinship": kinship,
                "near_match": near and not kinship,
            }
        )
    matches.sort(key=lambda m: m["similarity"], reverse=True)
    return matches


def recognize_user(
    *,
    subject_id: str,
    interaction: Mapping[str, Any],
    workspace_root: Optional[Path] = None,
    purpose: str = "cognitive_kinship",
    persist_trace: bool = True,
    proof_bundle_ref: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Consent-gated user cognitive recognition against fingerprint kinship templates.
    Raises ConsentDeniedError when consent is insufficient.
    """
    root = _workspace_root(workspace_root)
    if not is_user_recognition_enabled():
        return {"ok": False, "error": "user_recognition_disabled", "subject_id": subject_id}

    consent_class = assert_recognition_consent(subject_id, workspace_root=root, source="user_recognition")
    observed = geometry_from_interaction(interaction)
    prior = interaction.get("prior_geometry")
    if isinstance(prior, dict):
        geometry = blend_geometry(observed, prior)
    else:
        geometry = dict(observed)

    thresholds = _thresholds(root)
    kinship_min = float(thresholds.get("kinship_min_similarity") or 0.82)
    near_min = float(thresholds.get("near_match_min_similarity") or 0.7)
    templates = load_templates(root)
    matches = match_kinship(geometry, templates, kinship_min=kinship_min, near_min=near_min)
    top = matches[0] if matches else None

    result: Dict[str, Any] = {
        "ok": True,
        "subject_id": subject_id,
        "purpose": purpose,
        "consent_class": consent_class,
        "geometry": geometry,
        "matches": matches,
        "top_match": top,
        "kinship_detected": bool(top and top.get("kinship")),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "ephemeral": proof_bundle_ref is None,
    }

    if persist_trace:
        store = RecognitionTraceStore(root=root / "memory" / "governance" / "recognition_traces")
        trace = store.append(
            subject_id=subject_id,
            record={
                "event": "USER_RECOGNITION",
                "purpose": purpose,
                "consent_class": consent_class,
                "geometry": geometry,
                "top_match": top,
                "kinship_detected": result["kinship_detected"],
                "proof_bundle_ref": proof_bundle_ref,
            },
        )
        result["recognition_id"] = trace.get("recognition_id")
        result["trace_path"] = str(store._path_for(subject_id))

    return result


def recognition_status(*, subject_id: str, workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    root = _workspace_root(workspace_root)
    effective = resolve_consent_class(subject_id, workspace_root=root)
    store = RecognitionTraceStore(root=root / "memory" / "governance" / "recognition_traces")
    traces = store.read_all(subject_id, limit=20)
    return {
        "ok": True,
        "subject_id": subject_id,
        "feature_enabled": is_user_recognition_enabled(),
        "consent_class": effective,
        "recognition_active": is_user_recognition_enabled() and effective != "none",
        "template_count": len(load_templates(root)),
        "recent_traces": traces,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
