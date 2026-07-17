"""
Mermaid flowchart export for DAGs.

Produces flowchart TD string suitable for docs or visualization.
"""

from __future__ import annotations

from typing import Any, Dict, List, Union

from .schema import DAG


def dag_to_mermaid(dag: Union[DAG, Dict[str, Any]]) -> str:
    """
    Convert a DAG to a Mermaid flowchart TD string.

    Args:
        dag: DAG as dict or DAG instance (converted via to_dict).

    Returns:
        String starting with flowchart TD, then node definitions and edges.
        Wrapped in ```mermaid code fence for use in docs.
    """
    if isinstance(dag, DAG):
        dag = dag.to_dict()
    lines: List[str] = ["flowchart TD"]
    for n in dag.get("nodes", []):
        nid = n.get("id")
        if not nid:
            continue
        deps = n.get("depends_on") or []
        if not deps:
            lines.append(f"  {nid}[{nid}]")
        for d in deps:
            lines.append(f"  {d} --> {nid}")
    return "```mermaid\n" + "\n".join(lines) + "\n```\n"
