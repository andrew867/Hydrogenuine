"""Wire console validate to hg_core validate_dag."""

import sys
from pathlib import Path

_workspace_root = Path(__file__).resolve().parents[4]
if str(_workspace_root) not in sys.path:
    sys.path.insert(0, str(_workspace_root))

from hg_core.task_graph import DAG, validate_dag


def validate(dag: dict) -> dict:
    """Validate DAG via hg_core; return {ok, errors, warnings}."""
    try:
        dag_obj = DAG.from_dict(dag)
    except Exception as e:
        return {"ok": False, "errors": [{"message": str(e), "code": "PARSE_ERROR"}], "warnings": []}
    result = validate_dag(dag_obj)
    return {
        "ok": result.valid,
        "errors": list(result.errors),
        "warnings": [],
    }
