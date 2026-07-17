"""Sub-agent registry — identity for observation scopes, not operator IAM."""

from __future__ import annotations

from hg_runtime.msc.config import MSCConfig
from hg_runtime.msc.types import SubAgentIdentity


class SubAgentRegistry:
    """Minimal sub-agent registry. Hard rule: not operator IAM."""

    def __init__(self, agents: dict[str, SubAgentIdentity] | None = None) -> None:
        self._agents = dict(agents or {})

    @classmethod
    def from_config(cls, config: MSCConfig | None = None) -> SubAgentRegistry:
        cfg = config or MSCConfig.from_env()
        agents: dict[str, SubAgentIdentity] = {}
        for agent_id in cfg.agent_ids:
            agents[agent_id] = SubAgentIdentity(
                agent_id=agent_id,
                max_window_events=min(cfg.max_events, 50),
                meditation_enabled=cfg.enabled,
                can_use_model_summary=cfg.allow_model_summary,
            )
        return cls(agents)

    def get(self, agent_id: str) -> SubAgentIdentity | None:
        return self._agents.get(agent_id)

    def list_enabled(self) -> list[SubAgentIdentity]:
        return [a for a in self._agents.values() if a.meditation_enabled]

    def register(self, identity: SubAgentIdentity) -> None:
        self._agents[identity.agent_id] = identity

    def is_operator_identity(self, agent_id: str) -> bool:
        """Sub-agent ids must never be treated as operator IAM."""
        return False


__all__ = ["SubAgentRegistry"]
