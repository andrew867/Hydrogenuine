"""
DAG validator diagnostics: Diagnostic type and validate_dag_with_diagnostics.

Returns structured errors and warnings with standard codes for planner and tooling.
See hg_core/task_graph/docs/dag_validator_diagnostics_contract.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from .schema import DAG
from .validator import validate_dag


@dataclass
class Diagnostic:
    """Single validation error or warning with a standard code."""
    level: str  # "error" | "warn"
    code: str
    message: str
    node_id: Optional[str] = None
    field_path: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "level": self.level,
            "code": self.code,
            "message": self.message,
        }
        if self.node_id is not None:
            out["node_id"] = self.node_id
        if self.field_path is not None:
            out["field_path"] = self.field_path
        if self.suggestion is not None:
            out["suggestion"] = self.suggestion
        return out


def validate_dag_with_diagnostics(
    dag: Union[DAG, Dict[str, Any]],
    strict: bool = False,
) -> Dict[str, Any]:
    """
    Validate a DAG and return ok, errors, and warnings with standard diagnostic codes.

    Args:
        dag: DAG instance or dict (converted via DAG.from_dict).
        strict: Passed to validation; when True may enable stricter checks (e.g. expression vars).

    Returns:
        {"ok": bool, "errors": list[Diagnostic], "warnings": list[Diagnostic]}
        ok is True when there are no errors.
    """
    if isinstance(dag, dict):
        if not dag.get("graph_id"):
            return {
                "ok": False,
                "errors": [
                    Diagnostic(
                        level="error",
                        code="MISSING_GRAPH_ID",
                        message="graph_id is required",
                        field_path="graph_id",
                    )
                ],
                "warnings": [],
            }
        dag = DAG.from_dict(dag)
    result = validate_dag(dag)
    errors: List[Diagnostic] = []
    for e in result.errors:
        code = e.get("code") or "VALIDATION_ERROR"
        errors.append(
            Diagnostic(
                level="error",
                code=code,
                message=e["message"],
                node_id=e.get("node_id"),
                field_path=e.get("path"),
                suggestion=e.get("suggestion"),
            )
        )
    return {
        "ok": result.valid,
        "errors": errors,
        "warnings": [],
    }
