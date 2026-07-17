"""
Layer 9 Phase 5: Scenario tagger — produce ScenarioTag from evidence; emit SCENARIO_TAG_RECORDED and SCENARIO_ALARM_RAISED when pessimistic.
Pack2-04: Multi-label tagging (risk domains, operation types, stakeholder types) with confidence; POST /v1/alignment/tag.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.alignment_science.schemas import (
    scenario_tag,
    ScenarioTag,
    validate_scenario_tag,
)

# Multi-label tag taxonomy (Pack2-04)
RISK_DOMAINS = ["privacy", "security", "finance", "medical", "legal", "self_harm", "misinformation", "harassment"]
OPERATION_TYPES = ["read", "write", "external_write", "network", "code_exec", "credential_use"]
STAKEHOLDER_TYPES = ["user", "third_party", "system", "regulator"]
MODEL_VERSION = "rules-v1"


def _artifacts_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "alignment_science" / "scenario_tags"


def _derive_scenario(evidence_refs: List[str], pessimistic_threshold: Optional[float] = None) -> tuple[str, str]:
    """
    Stub: derive scenario from evidence refs. Returns (scenario, confidence_or_rationale).
    Rule: if any ref path or string contains 'fail' or 'pessimistic' -> pessimistic;
    else if many refs (>= 5) -> intermediate; else -> optimistic.
    """
    if not evidence_refs:
        return "intermediate", "No evidence provided."
    lower_refs = [str(r).lower() for r in evidence_refs]
    if any("fail" in r or "pessimistic" in r for r in lower_refs):
        return "pessimistic", "Evidence indicates failure or pessimistic signal."
    if len(evidence_refs) >= 5:
        return "intermediate", "Substantial evidence; mixed signals."
    return "optimistic", "Limited evidence; no negative signals."


def run_scenario_tagger(
    workspace_root: Path,
    scope_id: str,
    evidence_refs: List[str],
    tag_id: Optional[str] = None,
    pessimistic_threshold: Optional[float] = None,
    emit_ledger: bool = True,
    emit_alarm_when_pessimistic: bool = True,
) -> ScenarioTag:
    workspace_root = Path(workspace_root)
    tag_id = tag_id or scope_id
    scenario, rationale = _derive_scenario(evidence_refs, pessimistic_threshold)
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    root = _artifacts_root(workspace_root) / date_prefix
    root.mkdir(parents=True, exist_ok=True)
    artifact_path = root / f"{scope_id}.json"
    result = scenario_tag(
        tag_id=tag_id,
        scenario=scenario,
        evidence_refs=evidence_refs,
        confidence_or_rationale=rationale,
    )
    result["scope_id"] = scope_id
    result["artifact_ref"] = str(artifact_path)
    artifact_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if emit_ledger:
        try:
            from hg_core.ledger import emit

            emit(
                "SCENARIO_TAG_RECORDED",
                "scenario_tag",
                scope_id,
                {
                    "scope_id": scope_id,
                    "tag_id": tag_id,
                    "scenario": scenario,
                    "evidence_refs": evidence_refs,
                    "artifact_ref": str(artifact_path),
                },
                workspace_root=workspace_root,
                object_path=str(artifact_path),
            )
            if emit_alarm_when_pessimistic and scenario == "pessimistic":
                emit(
                    "SCENARIO_ALARM_RAISED",
                    "scenario_alarm",
                    scope_id,
                    {
                        "scope_id": scope_id,
                        "scenario": scenario,
                        "evidence_refs": evidence_refs,
                        "artifact_ref": str(artifact_path),
                    },
                    workspace_root=workspace_root,
                    object_path=str(artifact_path),
                )
        except Exception:
            pass
    return result


def tag_text_multi_label(text: str, context: Optional[Dict[str, Any]] = None, use_llm: bool = False) -> Dict[str, Any]:
    """
    Multi-label tag for alignment: risk domains, operation types, stakeholder types.
    Returns { tags: [{ name, confidence }], model_version }.
    Rule-based: keyword heuristics; no sensitive text in rationale (feature indices only).
    """
    context = context or {}
    combined = (text or "") + " " + json.dumps(context)[:500]
    combined_lower = combined.lower()
    tags: List[Dict[str, Any]] = []
    # Risk domains: simple keyword presence -> 0.6–0.9 confidence
    for domain in RISK_DOMAINS:
        pattern = domain.replace("_", r"[\s\-_]?")
        if re.search(pattern, combined_lower):
            tags.append({"name": f"risk:{domain}", "confidence": 0.7})
    # Operation types
    for op in OPERATION_TYPES:
        if op.replace("_", " ") in combined_lower or op in combined_lower:
            tags.append({"name": f"op:{op}", "confidence": 0.75})
    # Stakeholder
    for st in STAKEHOLDER_TYPES:
        if st.replace("_", " ") in combined_lower or st in combined_lower:
            tags.append({"name": f"stakeholder:{st}", "confidence": 0.7})
    if use_llm:
        try:
            from hg_llm import get_default_registry, CompletionRequest
            prompt = f"""Classify this text into alignment tags. Reply with JSON only: {{ "risk": ["privacy" if applicable], "ops": ["read" etc], "stakeholder": ["user" etc] }}. Use only: risk domains privacy, security, finance, medical, legal, self_harm, misinformation, harassment; ops read, write, external_write, network, code_exec, credential_use; stakeholder user, third_party, system, regulator.
Text (first 800 chars): {combined[:800]}"""
            reg = get_default_registry()
            resp = reg.complete(CompletionRequest(messages=[{"role": "user", "content": prompt}], model="openai/gpt-4o-mini", max_tokens=300, temperature=0))
            if resp and resp.content:
                mo = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", resp.content)
                raw = mo.group(0) if mo else "{}"
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = {}
                for d in parsed.get("risk", [])[:3]:
                    if d in RISK_DOMAINS:
                        tags.append({"name": f"risk:{d}", "confidence": 0.85})
                for o in parsed.get("ops", [])[:3]:
                    if o in OPERATION_TYPES:
                        tags.append({"name": f"op:{o}", "confidence": 0.85})
                for s in parsed.get("stakeholder", [])[:2]:
                    if s in STAKEHOLDER_TYPES:
                        tags.append({"name": f"stakeholder:{s}", "confidence": 0.85})
        except Exception:
            pass
    # Dedupe by name, keep max confidence
    seen: Dict[str, float] = {}
    for t in tags:
        n, c = t["name"], float(t.get("confidence", 0.5))
        if n not in seen or seen[n] < c:
            seen[n] = c
    tags = [{"name": n, "confidence": round(c, 2)} for n, c in seen.items()]
    return {"tags": tags, "model_version": MODEL_VERSION}


def get_scenario_tag(workspace_root: Path, scope_id: str) -> Optional[ScenarioTag]:
    workspace_root = Path(workspace_root)
    root = _artifacts_root(workspace_root)
    if not root.exists():
        return None
    for date_dir in sorted(root.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        path = date_dir / f"{scope_id}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("scope_id") == scope_id and validate_scenario_tag(data):
                    return data
            except Exception:
                continue
    return None
