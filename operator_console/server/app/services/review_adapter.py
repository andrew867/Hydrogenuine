"""Wire console review to hg_core graph_review."""

import sys
from pathlib import Path

_workspace_root = Path(__file__).resolve().parents[4]
if str(_workspace_root) not in sys.path:
    sys.path.insert(0, str(_workspace_root))

from hg_core.task_graph.graph_review import ReviewPolicy, annotate_in_loop_body, review_dag


def review(dag: dict) -> dict:
    """Review DAG via hg_core; return {ok, reviewed_dag, report}."""
    dag = dict(dag)  # don't mutate caller's dict
    annotate_in_loop_body(dag)
    reviewed_dag, report = review_dag(dag, ReviewPolicy())
    return {
        "ok": not report.get("blocked", True),
        "reviewed_dag": reviewed_dag,
        "report": report,
    }
