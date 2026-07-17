"""Extended dry autonomy package."""

from hg_runtime.extended_dry_autonomy.schema import ExtendedDryAutonomyConfig, ExtendedDryAutonomyVerdict

__all__ = ["ExtendedDryAutonomyConfig", "ExtendedDryAutonomyVerdict", "run_extended_dry_autonomy"]


def run_extended_dry_autonomy(*args, **kwargs):
    from hg_runtime.extended_dry_autonomy.extended_runner import run_extended_dry_autonomy as _run

    return _run(*args, **kwargs)
