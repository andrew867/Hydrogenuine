"""YSR handler — yawn soft-reset for sub-agents."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from hg_runtime.yawn.config import YSRConfig
from hg_runtime.yawn.cycle import _bus_head_seq, run_yawn_for_agents
from hg_runtime.yawn.policy import evaluate_trigger
class StubYSRHandler:
    """No-op YSR handler — safe default when YSR disabled."""

    handler_id = "rtc.stub.ysr"

    def should_yawn(
        self,
        view: Mapping[str, Any],
        aep_state: Mapping[str, Any],
        *,
        panic_active: bool = False,
        operator_requested: bool = False,
    ) -> bool:
        del view, aep_state, panic_active, operator_requested
        return False

    def execute_yawn(
        self,
        view: Mapping[str, Any],
        aep_state: Mapping[str, Any],
        *,
        panic_active: bool = False,
        operator_requested: bool = False,
    ) -> List[Dict[str, Any]]:
        del view, aep_state, panic_active, operator_requested
        return []

    def bind_runtime(self, bus: Any, state: Mapping[str, Any]) -> None:
        del bus, state


class Phase1YSRHandler:
    """Bounded yawn soft-reset for registered sub-agents."""

    handler_id = "rtc.ysr.phase1"

    def __init__(
        self,
        *,
        config: YSRConfig | None = None,
        runtime_dir: Any = None,
        clock: Any = None,
        requested: bool = False,
        agent_ids: tuple[str, ...] | None = None,
    ) -> None:
        self._config = config or YSRConfig.from_env()
        self._runtime_dir = runtime_dir
        self._clock = clock
        self._requested = requested
        self._agent_ids = agent_ids or self._config.agent_ids
        self._bus: Any = None
        self._state: Mapping[str, Any] | None = None

    def bind_runtime(self, bus: Any, state: Mapping[str, Any]) -> None:
        self._bus = bus
        self._state = state
        if self._runtime_dir is None and hasattr(bus, "runtime_dir"):
            self._runtime_dir = bus.runtime_dir

    def _now(self) -> str:
        if callable(self._clock):
            return str(self._clock())
        if self._bus is not None and hasattr(self._bus, "clock"):
            return str(self._bus.clock())
        return "1970-01-01T00:00:00.000000Z"

    def should_yawn(
        self,
        view: Mapping[str, Any],
        aep_state: Mapping[str, Any],
        *,
        panic_active: bool = False,
        operator_requested: bool = False,
    ) -> bool:
        if not self._config.enabled or self._bus is None or self._runtime_dir is None:
            return False
        if panic_active:
            return False
        if operator_requested or self._requested:
            return True
        bus_head = _bus_head_seq(self._bus)
        for agent_id in self._agent_ids:
            from hg_runtime import world_state as ws
            from hg_runtime.yawn.cycle import _refresh_world_state_from_bus

            _, refreshed_hash = _refresh_world_state_from_bus(self._bus)
            prior_hash = ws.state_hash(self._state) if isinstance(self._state, dict) else ""
            decision = evaluate_trigger(
                config=self._config,
                agent_id=agent_id,
                view=view,
                aep_state=aep_state,
                runtime_dir=self._runtime_dir,
                bus_head_seq=bus_head,
                prior_world_state_hash=prior_hash,
                refreshed_world_state_hash=refreshed_hash,
                panic_active=panic_active,
                operator_requested=False,
            )
            if decision.result == "yawn_allowed":
                return True
        return False

    def execute_yawn(
        self,
        view: Mapping[str, Any],
        aep_state: Mapping[str, Any],
        *,
        panic_active: bool = False,
        operator_requested: bool = False,
    ) -> List[Dict[str, Any]]:
        if not self._config.enabled or self._bus is None or self._runtime_dir is None:
            return []
        return run_yawn_for_agents(
            config=self._config,
            agent_ids=self._agent_ids,
            view=view,
            aep_state=aep_state,
            bus=self._bus,
            runtime_dir=self._runtime_dir,
            clock_now=self._now(),
            panic_active=panic_active,
            operator_requested=operator_requested or self._requested,
            prior_state=self._state if isinstance(self._state, dict) else None,
        )


__all__ = ["Phase1YSRHandler", "StubYSRHandler"]
