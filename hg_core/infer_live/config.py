"""INFER-LIVE configuration — env-driven dry-run; not hardcoded."""

from __future__ import annotations

import os


def _truthy(val: str | None) -> bool:
    return str(val or "").strip().lower() in ("1", "true", "yes", "on")


def cognitive_soak_active() -> bool:
    return _truthy(os.environ.get("HG_COGNITIVE_SOAK_ACTIVE"))


def infer_dry_run_mode(runtime_mode=None) -> bool:
    """Env-driven dry-run. Not hardcoded true."""
    raw = os.environ.get("HG_INFER_DRY_RUN")
    if raw is not None and str(raw).strip() != "":
        return _truthy(raw)
    return False


def provider_fallback_allowed(runtime_mode=None) -> bool:
    """Fallback stubs never count as real cognition when cognitive soak is active."""
    if cognitive_soak_active():
        return False
    if runtime_mode is not None:
        name = getattr(runtime_mode, "value", str(runtime_mode))
        if name in ("fixture", "test", "dry_run"):
            return True
    try:
        from hg_runtime.runtime_mode import RuntimeMode, resolve_runtime_mode

        receipt = resolve_runtime_mode()
        if receipt.runtime_mode in (RuntimeMode.FIXTURE, RuntimeMode.TEST, RuntimeMode.DRY_RUN):
            return True
    except Exception:
        pass
    return infer_dry_run_mode(runtime_mode)


def infer_refuse_authority_conversion() -> bool:
    return True


def infer_refuse_live_backend_calls() -> bool:
    return True


def infer_refuse_model_download_without_approval() -> bool:
    return True


__all__ = [
    "cognitive_soak_active",
    "infer_dry_run_mode",
    "infer_refuse_authority_conversion",
    "infer_refuse_live_backend_calls",
    "infer_refuse_model_download_without_approval",
    "provider_fallback_allowed",
]
