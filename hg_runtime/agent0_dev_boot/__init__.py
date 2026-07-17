"""Agent #0 dev boot preparation runtime — advisory only, no authority."""

from hg_runtime.agent0_dev_boot.manifest import load_organ_manifest
from hg_runtime.agent0_dev_boot.profiles import load_runtime_profile

__all__ = ["BootResult", "load_organ_manifest", "load_runtime_profile", "run_agent0_dev_boot"]


# Lazy BootResult export for backward compatibility
def __getattr__(name: str):
    if name == "BootResult":
        from hg_runtime.agent0_dev_boot.boot import BootResult

        return BootResult
    if name == "run_agent0_dev_boot":
        from hg_runtime.agent0_dev_boot.boot import run_agent0_dev_boot

        return run_agent0_dev_boot
    raise AttributeError(name)
