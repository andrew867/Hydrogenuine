"""Foreground hands-off continuous session for Agent Zero Phase 22."""

from __future__ import annotations

__all__ = [
    "HandsOffSessionConfig",
    "HandsOffSessionState",
    "HandsOffSessionVerdict",
    "SessionPostflight",
    "build_hands_off_session_monitor_snapshot",
    "create_panic_control",
    "create_stop_control",
    "load_postflight",
    "run_hands_off_session",
    "validate_session_config",
]


def __getattr__(name: str):
    if name in {"HandsOffSessionVerdict", "HandsOffSessionStatus"}:
        from hg_runtime.hands_off_session import schema as _s

        return getattr(_s, name)
    if name in {"HandsOffSessionConfig", "validate_session_config", "build_default_config"}:
        from hg_runtime.hands_off_session import session_config as _c

        return getattr(_c, name)
    if name == "HandsOffSessionState":
        from hg_runtime.hands_off_session import session_state as _st

        return getattr(_st, name)
    if name == "run_hands_off_session":
        from hg_runtime.hands_off_session import session_runner as _r

        return getattr(_r, name)
    if name in {"create_stop_control", "create_panic_control", "check_stop", "check_panic"}:
        from hg_runtime.hands_off_session import manual_controls as _m

        return getattr(_m, name)
    if name in {"SessionPostflight", "load_postflight", "write_postflight"}:
        from hg_runtime.hands_off_session import postflight as _p

        return getattr(_p, name)
    if name == "build_hands_off_session_monitor_snapshot":
        from hg_runtime.hands_off_session import exciton_snapshot as _e

        return getattr(_e, name)
    raise AttributeError(name)
