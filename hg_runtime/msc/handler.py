"""MSC handler — quiet observation cycles for sub-agents."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from hg_runtime import world_state as ws
from hg_runtime.contract import Event, draft, jsonable, stable_id
from hg_runtime.msc.config import MSCConfig
from hg_runtime.msc.registry import SubAgentRegistry
from hg_runtime.msc.store import load_previous_summary_ref, store_summary_ref
from hg_runtime.msc.summary import build_deterministic_summary
from hg_runtime.msc.types import MeditationCycleRecord
from hg_runtime.msc.window import select_bounded_window

RECOVERY_ACTIVE_STATES = frozenset(
    {
        "RECOVERY",
        "DRAINING",
        "CHECKPOINTING",
        "HYGIENE",
        "REHYDRATING",
        "SAFE_MODE",
    }
)

AUTHORITY_EVENT_PREFIXES = (
    "DECISION_EVENT",
    "GPP_PERMIT_BOUND",
    "UEAK_EXECUTION_COMMITTED",
    "OEA_EXECUTION_COMPLETED",
    "TER_COMMAND_COMPLETED",
    "ACTION_COMMITTED",
    "SRP_PATCH_APPLIED",
)


class StubMSCHandler:
    """No-op MSC handler — safe default when MSC disabled."""

    handler_id = "rtc.stub.msc"

    def should_enter_cycle(
        self,
        view: Mapping[str, Any],
        aep_state: Mapping[str, Any],
        *,
        panic_active: bool = False,
        operator_requested: bool = False,
    ) -> bool:
        del view, aep_state, panic_active, operator_requested
        return False

    def execute_cycle(
        self,
        view: Mapping[str, Any],
        aep_state: Mapping[str, Any],
        *,
        panic_active: bool = False,
    ) -> List[Dict[str, Any]]:
        del view, aep_state, panic_active
        return []

    def bind_runtime(self, bus: Any, state: Mapping[str, Any]) -> None:
        del bus, state


class Phase1MSCHandler:
    """Bounded quiet observation for registered sub-agents."""

    handler_id = "rtc.msc.phase1"

    def __init__(
        self,
        *,
        config: MSCConfig | None = None,
        registry: SubAgentRegistry | None = None,
        runtime_dir: Any = None,
        clock: Any = None,
        requested: bool = False,
    ) -> None:
        self._config = config or MSCConfig.from_env()
        self._registry = registry or SubAgentRegistry.from_config(self._config)
        self._runtime_dir = runtime_dir
        self._clock = clock
        self._requested = requested
        self._bus: Any = None
        self._state: Mapping[str, Any] | None = None
        self._tick_checks = 0
        self._last_cycle_tick = 0

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

    def _recovery_active(self, view: Mapping[str, Any]) -> bool:
        env = view.get("environment", {})
        if not isinstance(env, Mapping):
            return False
        state = str(env.get("recovery_state", "NORMAL"))
        if state in RECOVERY_ACTIVE_STATES:
            return True
        return bool(env.get("panic"))

    def _aep_suggests_quiet(self, aep_state: Mapping[str, Any]) -> bool:
        """AEP may suggest; it may not command."""
        try:
            severity = int(aep_state.get("max_severity", 0))
        except (TypeError, ValueError):
            severity = 0
        return severity >= 7

    def should_enter_cycle(
        self,
        view: Mapping[str, Any],
        aep_state: Mapping[str, Any],
        *,
        panic_active: bool = False,
        operator_requested: bool = False,
    ) -> bool:
        if not self._config.enabled:
            return False
        if not self._registry.list_enabled():
            return False
        self._tick_checks += 1
        if panic_active:
            return False
        if self._recovery_active(view):
            return False
        if operator_requested or self._requested:
            return True
        if self._config.cycle_every_ticks > 0:
            ticks = int(view.get("self", {}).get("ticks", 0)) if isinstance(view.get("self"), Mapping) else 0
            if ticks > 0 and ticks % self._config.cycle_every_ticks == 0:
                return True
        if self._aep_suggests_quiet(aep_state):
            return True
        return False

    def _refusal_draft(
        self,
        agent_id: str,
        cycle_id: str,
        reason_code: str,
        *,
        parents: Sequence[str] = (),
    ) -> Dict[str, Any]:
        record = MeditationCycleRecord(
            agent_id=agent_id,
            cycle_id=cycle_id,
            started_at=self._now(),
            completed_at=self._now(),
            result_status=reason_code,
            reason_code=reason_code,
        )
        return draft(
            "MSC_REFUSED",
            {
                "cycle": record.to_payload(),
                "reason_code": reason_code,
                "observation_only": True,
            },
            causal_parents=list(parents),
        )

    def execute_cycle(
        self,
        view: Mapping[str, Any],
        aep_state: Mapping[str, Any],
        *,
        panic_active: bool = False,
    ) -> List[Dict[str, Any]]:
        if not self._config.enabled or self._bus is None:
            return []

        drafts: List[Dict[str, Any]] = []
        all_events = list(self._bus.read_all())
        if self._state is not None and isinstance(self._state, dict):
            world_hash = ws.state_hash(self._state)
        elif isinstance(view, Mapping):
            world_hash = ws.state_hash(jsonable(view))
        else:
            world_hash = ""

        for agent in self._registry.list_enabled():
            cycle_id = stable_id("msc", agent.agent_id, self._tick_checks, world_hash)
            parents: List[str] = []

            if panic_active:
                drafts.append(
                    self._refusal_draft(agent.agent_id, cycle_id, "REFUSED_PANIC")
                )
                continue

            if self._recovery_active(view):
                drafts.append(
                    self._refusal_draft(
                        agent.agent_id, cycle_id, "REFUSED_RECOVERY_ACTIVE"
                    )
                )
                continue

            if not agent.meditation_enabled:
                drafts.append(
                    self._refusal_draft(agent.agent_id, cycle_id, "REFUSED_POLICY")
                )
                continue

            started_at = self._now()
            record = MeditationCycleRecord(
                agent_id=agent.agent_id,
                cycle_id=cycle_id,
                started_at=started_at,
                pressure_snapshot={
                    "max_severity": aep_state.get("max_severity", 0),
                    "dimensions": dict(aep_state.get("dimensions", {}))
                    if isinstance(aep_state.get("dimensions"), Mapping)
                    else {},
                    "suggested_quiet": self._aep_suggests_quiet(aep_state),
                },
                recovery_snapshot={
                    "recovery_state": view.get("environment", {}).get("recovery_state", "NORMAL")
                    if isinstance(view.get("environment"), Mapping)
                    else "NORMAL",
                },
                result_status="MEDITATION_REQUESTED",
            )

            req = draft(
                "MSC_MEDITATION_REQUESTED",
                {
                    "cycle": record.to_payload(),
                    "mode": self._config.mode,
                    "observation_only": True,
                },
            )
            drafts.append(req)
            parents = [req["type"]]  # placeholder; loop replaces with event ids

            started = draft(
                "MSC_MEDITATION_STARTED",
                {
                    "agent_id": agent.agent_id,
                    "cycle_id": cycle_id,
                    "started_at": started_at,
                },
            )
            drafts.append(started)

            window_id = stable_id("win", cycle_id)
            max_events = min(self._config.max_events, agent.max_window_events)
            selection = select_bounded_window(
                all_events,
                agent_id=agent.agent_id,
                window_id=window_id,
                max_events=max_events,
                max_age_seconds=self._config.max_age_seconds,
                clock_now=self._now(),
                subsystem_filters=agent.allowed_observation_scopes,
            )

            if not selection.event_ids:
                record.result_status = "REFUSED_NO_CONTEXT"
                record.reason_code = "REFUSED_NO_CONTEXT"
                record.completed_at = self._now()
                drafts.append(
                    draft(
                        "MSC_REFUSED",
                        {
                            "cycle": record.to_payload(),
                            "reason_code": "REFUSED_NO_CONTEXT",
                            "observation_only": True,
                        },
                    )
                )
                continue

            window_draft = draft(
                "MSC_EVENT_WINDOW_SELECTED",
                {
                    **selection.to_payload(),
                    "cycle_id": cycle_id,
                },
            )
            drafts.append(window_draft)

            record.event_window_start = selection.seq_start
            record.event_window_end = selection.seq_end
            record.observed_event_count = len(selection.event_ids)
            record.observed_subsystems = list(selection.observed_subsystems)
            record.result_status = "LISTENING"

            selected_events = [
                e for e in all_events if str(e.get("event_id")) in selection.event_ids
            ]

            drafts.append(
                draft(
                    "MSC_LISTENING_COMPLETED",
                    {
                        "agent_id": agent.agent_id,
                        "cycle_id": cycle_id,
                        "observed_event_count": len(selection.event_ids),
                        "observed_subsystems": list(selection.observed_subsystems),
                    },
                )
            )
            record.result_status = "SUMMARIZING"

            if self._config.mode == "model_assisted":
                record.result_status = "SKIPPED"
                record.reason_code = "model_assisted_disabled"
                record.completed_at = self._now()
                drafts.append(
                    draft(
                        "MSC_SKIPPED",
                        {
                            "cycle": record.to_payload(),
                            "reason": "model_assisted_disabled",
                            "observation_only": True,
                        },
                    )
                )
                continue

            summary_id = stable_id("sum", cycle_id)
            prev_ref = None
            if self._runtime_dir is not None:
                prev_ref = load_previous_summary_ref(self._runtime_dir, agent.agent_id)

            summary = build_deterministic_summary(
                summary_id=summary_id,
                agent_id=agent.agent_id,
                cycle_id=cycle_id,
                events=selected_events,
                event_hashes=selection.event_hashes,
                view=view,
                world_state_hash=world_hash,
                redaction_report_ref=f"redact:{window_id}" if selection.redacted_count else None,
            )

            memory_ref = None
            if self._runtime_dir is not None:
                memory_ref = store_summary_ref(
                    self._runtime_dir,
                    agent_id=agent.agent_id,
                    cycle_id=cycle_id,
                    summary_id=summary_id,
                    summary_hash=summary.summary_hash,
                )

            summary_payload = summary.to_payload()
            if prev_ref:
                summary_payload["previous_summary_ref"] = prev_ref
            if memory_ref:
                summary_payload["memory_ref"] = memory_ref

            drafts.append(
                draft(
                    "MSC_SUMMARY_RECORDED",
                    {
                        **summary_payload,
                        "observation_only": True,
                    },
                )
            )

            record.summary_hash = summary.summary_hash
            record.result_status = "SETTLED"
            record.completed_at = self._now()

            drafts.append(
                draft(
                    "MSC_SETTLED",
                    {
                        "cycle": record.to_payload(),
                        "summary_hash": summary.summary_hash,
                        "memory_ref": memory_ref,
                        "observation_only": True,
                    },
                )
            )

        return drafts

    @staticmethod
    def is_authority_event(etype: str) -> bool:
        return any(etype.startswith(prefix) or etype == prefix for prefix in AUTHORITY_EVENT_PREFIXES)


__all__ = ["Phase1MSCHandler", "StubMSCHandler", "AUTHORITY_EVENT_PREFIXES"]
