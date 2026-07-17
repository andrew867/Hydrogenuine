"""
Layer 9 Phase 4: Eval pipeline — generate EvalCases, score run/decision, EvalRunResult.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from hg_core.alignment_science.schemas import eval_case, eval_run_result, EvalCase, EvalRunResult, validate_eval_case, validate_eval_run_result


def _cases_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "alignment_science" / "eval_cases"


def _runs_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "alignment_science" / "eval_runs"


def generate_eval_cases(workspace_root: Path, domain: str, count: int = 5) -> List[EvalCase]:
    workspace_root = Path(workspace_root)
    cases: List[EvalCase] = []
    for i in range(count):
        case_id = f"{domain}_{i}"
        cases.append(eval_case(case_id=case_id, input_data=f"input_{domain}_{i}", expected_or_criteria=f"expected_{domain}_{i}", domain=domain))
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    root = _cases_root(workspace_root) / date_prefix
    root.mkdir(parents=True, exist_ok=True)
    safe_domain = "".join(c if c.isalnum() or c in "-_" else "_" for c in domain)[:32]
    path = root / f"{safe_domain}.json"
    path.write_text(json.dumps({"domain": domain, "cases": cases}, indent=2, ensure_ascii=False), encoding="utf-8")
    return cases


def get_eval_cases(workspace_root: Path, domain: str) -> List[EvalCase]:
    workspace_root = Path(workspace_root)
    root = _cases_root(workspace_root)
    if not root.exists():
        return []
    safe_domain = "".join(c if c.isalnum() or c in "-_" else "_" for c in domain)[:32]
    for date_dir in sorted(root.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        path = date_dir / f"{safe_domain}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                raw = data.get("cases") or []
                return [c for c in raw if validate_eval_case(c)]
            except Exception:
                continue
    return []


def run_eval_scorer(
    workspace_root: Path,
    case_ids: List[str],
    decision_id: Optional[str] = None,
    run_id: Optional[str] = None,
    emit_ledger: bool = True,
) -> EvalRunResult:
    workspace_root = Path(workspace_root)
    eval_run_id = str(uuid.uuid4())
    scores: Dict[str, float] = {cid: 0.5 for cid in case_ids}
    aggregate = sum(scores.values()) / len(scores) if scores else 0.0
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    root = _runs_root(workspace_root) / date_prefix
    root.mkdir(parents=True, exist_ok=True)
    artifact_path = root / f"{eval_run_id}.json"
    result = eval_run_result(eval_run_id=eval_run_id, case_ids=case_ids, scores=scores, artifact_ref=str(artifact_path), aggregate=round(aggregate, 4))
    out = dict(result)
    if decision_id is not None:
        out["decision_id"] = decision_id
    if run_id is not None:
        out["run_id"] = run_id
    artifact_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    if emit_ledger:
        try:
            from hg_core.ledger import emit
            emit("EVAL_RUN_COMPLETED", "eval_run", eval_run_id, {"eval_run_id": eval_run_id, "aggregate": aggregate, "artifact_ref": str(artifact_path)}, workspace_root=workspace_root, object_path=str(artifact_path))
        except Exception:
            pass
    return result


def get_eval_run_result(workspace_root: Path, eval_run_id: str) -> Optional[EvalRunResult]:
    workspace_root = Path(workspace_root)
    root = _runs_root(workspace_root)
    if not root.exists():
        return None
    for date_dir in root.iterdir():
        if not date_dir.is_dir():
            continue
        path = date_dir / f"{eval_run_id}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("eval_run_id") == eval_run_id and validate_eval_run_result(data):
                    return data
            except Exception:
                continue
    return None
