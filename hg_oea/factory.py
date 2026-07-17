"""OEA executor factory — explicit stub vs real mode."""

from __future__ import annotations

from hg_oea.bounded_executor import OEABoundedExecutor
from hg_oea.config import OEAConfig
from hg_oea.executor import OEAStubExecutor


def create_oea_executor(config: OEAConfig | None = None, *, clock=None):
    cfg = config or OEAConfig.from_env()
    if cfg.is_real:
        return OEABoundedExecutor(cfg, clock=clock)
    return OEAStubExecutor()


__all__ = ["create_oea_executor"]
