"""
Scope context for co-access (molecules) layer.

Uses contextvars so reads can be grouped into "rooms" by scope_type/scope_id.
Call set_scope (or use scope_context) at entry points (run_task, DAG executor, overseer cycle).
"""

from contextvars import ContextVar
from typing import Any, Dict, Optional

# Context vars for current scope (session, run, cycle). Never raise; missing scope is empty dict.
_scope_var: ContextVar[Dict[str, Any]] = ContextVar(
    "hg_scope",
    default={},
)


def set_scope(
    scope_type: str,
    scope_id: str,
    run_id: Optional[str] = None,
    session_id: Optional[str] = None,
    cycle_id: Optional[str] = None,
) -> None:
    """
    Set the current scope for access logging. Overwrites any previous scope in this context.
    scope_type: "session" | "run" | "cycle"
    scope_id: identifier for this scope (e.g. session_id, run_id, cycle timestamp)
    """
    _scope_var.set({
        "scope_type": scope_type,
        "scope_id": scope_id,
        "run_id": run_id,
        "session_id": session_id,
        "cycle_id": cycle_id,
    })


def get_scope() -> Dict[str, Any]:
    """Return current scope dict (scope_type, scope_id, optional run_id/session_id/cycle_id). Empty if not set."""
    return _scope_var.get().copy()


def clear_scope() -> None:
    """Clear current scope (reset to empty)."""
    _scope_var.set({})


class scope_context:
    """
    Context manager: set scope for the duration of the block, then restore previous.
    """

    def __init__(
        self,
        scope_type: str,
        scope_id: str,
        run_id: Optional[str] = None,
        session_id: Optional[str] = None,
        cycle_id: Optional[str] = None,
    ):
        self.scope_type = scope_type
        self.scope_id = scope_id
        self.run_id = run_id
        self.session_id = session_id
        self.cycle_id = cycle_id
        self._token = None

    def __enter__(self) -> "scope_context":
        self._token = _scope_var.set({
            "scope_type": self.scope_type,
            "scope_id": self.scope_id,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "cycle_id": self.cycle_id,
        })
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._token is not None:
            _scope_var.reset(self._token)
            self._token = None
