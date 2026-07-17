"""DSE configuration — sandbox roots and sink enablement."""

from __future__ import annotations

from pathlib import Path


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def dse_sandbox_root() -> Path:
    return workspace_root() / "sandbox" / "dse"


def dse_file_sink_root() -> Path:
    return dse_sandbox_root() / "files"


def dse_store_sink_root() -> Path:
    return dse_sandbox_root() / "store"


def dse_grant_registry_root() -> Path:
    return dse_sandbox_root() / "grants"


def dse_command_sandbox_root() -> Path:
    return dse_sandbox_root() / "commands"


def dse_sensor_sink_root() -> Path:
    return dse_sandbox_root() / "sensors"


def dse_outbox_root() -> Path:
    return dse_sandbox_root() / "outbox"


def dse_checkpoint_root() -> Path:
    return dse_sandbox_root() / "checkpoints"


def dse_process_sandbox_root() -> Path:
    return dse_sandbox_root() / "processes"


def dse_loop_supervisor_root() -> Path:
    return dse_sandbox_root() / "loops"


def dse_inference_sink_root() -> Path:
    return dse_sandbox_root() / "inference"


def dse_proof_root() -> Path:
    return workspace_root() / "docs" / "proofs" / "dse"


def dse_model_cache_root() -> Path:
    return dse_sandbox_root() / "model_cache"


def dse_real_sink_enabled() -> bool:
    """Real durable sinks enabled for DSE pass (sandbox-scoped only)."""
    return True


def dse_refuse_authority_conversion() -> bool:
    return True


def ensure_sandbox_dirs() -> None:
    for path in (
        dse_file_sink_root(),
        dse_store_sink_root(),
        dse_grant_registry_root(),
        dse_command_sandbox_root(),
        dse_sensor_sink_root(),
        dse_outbox_root(),
        dse_checkpoint_root(),
        dse_process_sandbox_root(),
        dse_loop_supervisor_root(),
        dse_inference_sink_root(),
        dse_proof_root(),
        dse_model_cache_root(),
    ):
        path.mkdir(parents=True, exist_ok=True)


__all__ = [
    "dse_checkpoint_root",
    "dse_command_sandbox_root",
    "dse_file_sink_root",
    "dse_grant_registry_root",
    "dse_inference_sink_root",
    "dse_loop_supervisor_root",
    "dse_model_cache_root",
    "dse_outbox_root",
    "dse_process_sandbox_root",
    "dse_proof_root",
    "dse_real_sink_enabled",
    "dse_refuse_authority_conversion",
    "dse_sandbox_root",
    "dse_sensor_sink_root",
    "dse_store_sink_root",
    "ensure_sandbox_dirs",
    "workspace_root",
]
