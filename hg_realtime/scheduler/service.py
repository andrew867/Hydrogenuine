from __future__ import annotations
import json
import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Optional

from ..bus.interface import EventBus
from ..schemas.event import Event
from .models import RunRequested
from .coalesce import Coalescer, CoalesceConfig

from ..integrations.dag_launcher import DagLauncher
from ..integrations.launch_guard import should_skip_launch
from ..integrations.policy_gate import PolicyGate
from ..integrations.workflow_mapping import route_event_to_workflow

if TYPE_CHECKING:
    from ..integrations.run_index import RunIndexWriter

@dataclass
class SchedulerConfig:
    group: str = "hg-scheduler"
    consumer: str = "sched-1"
    poll_timeout_s: float = 1.0
    max_events: int = 50
    coalesce_window_s: float = 2.0

class RealTimeScheduler:
    """Consumes Events and emits RunRequested into your DAG runtime."""

    def __init__(
        self,
        *,
        bus: EventBus,
        launcher: DagLauncher,
        policy: PolicyGate,
        run_index: Optional["RunIndexWriter"] = None,
        cfg: Optional[SchedulerConfig] = None,
    ) -> None:
        self.bus = bus
        self.launcher = launcher
        self.policy = policy
        self.run_index = run_index
        self.cfg = cfg or SchedulerConfig()
        self.coalescer = Coalescer(CoalesceConfig(window_s=self.cfg.coalesce_window_s))

    def _route_event_to_workflow(self, e: Event) -> Optional[tuple[str, Dict[str, Any]]]:
        """Single source: DAG_JOB_REGISTRY + workflow_registry via workflow_mapping."""
        return route_event_to_workflow(e)

    def _process_approved_runs(self) -> int:
        """Poll gateway for runs with status=approved_pending_launch; launch each with existing run_id."""
        try:
            from hg_gateway.db import get_connection
        except Exception:
            return 0
        launched = 0
        try:
            with get_connection() as c:
                rows = c.execute(
                    "SELECT run_id, pending_request_json FROM runs WHERE status = 'approved_pending_launch' LIMIT 5"
                ).fetchall()
                if not rows:
                    return 0
                for row in rows:
                    run_id = row[0] if isinstance(row, (tuple, list)) else row["run_id"]
                    payload_json = row[1] if isinstance(row, (tuple, list)) else row["pending_request_json"]
                    c.execute("UPDATE runs SET status = 'launching' WHERE run_id = ?", (run_id,))
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug("gateway approved_runs poll skipped: %s", e)
            return 0
        for row in rows:
            run_id = row[0] if isinstance(row, (tuple, list)) else row["run_id"]
            payload_json = row[1] if isinstance(row, (tuple, list)) else row["pending_request_json"]
            if not payload_json:
                continue
            try:
                payload = json.loads(payload_json)
                req = RunRequested(
                    request_id=str(uuid.uuid4()),
                    workflow_id=str(payload.get("workflow_id") or ""),
                    tenant_id=str(payload.get("tenant_id") or "default"),
                    actor_id=str(payload.get("actor_id") or ""),
                    correlation_id=str(payload.get("correlation_id") or ""),
                    resolved_inputs=payload.get("resolved_inputs") or {},
                    dedup_key=payload.get("dedup_key"),
                )
                skip, skip_reason = should_skip_launch(req.workflow_id, req.resolved_inputs)
                if skip:
                    continue
                self.launcher.launch(req, run_id=run_id)
                launched += 1
            except Exception:
                continue
        return launched

    def tick_once(self) -> int:
        self._process_approved_runs()
        events = self.bus.poll(
            group=self.cfg.group,
            consumer=self.cfg.consumer,
            max_events=self.cfg.max_events,
            timeout_s=self.cfg.poll_timeout_s,
        )
        handled = 0
        for e in events:
            try:
                if self.coalescer.should_drop(dedup_key=e.dedup_key, event_id=e.event_id):
                    self.bus.ack(group=self.cfg.group, consumer=self.cfg.consumer, event_id=e.event_id)
                    continue

                route = self._route_event_to_workflow(e)
                if route is None:
                    self.bus.ack(group=self.cfg.group, consumer=self.cfg.consumer, event_id=e.event_id)
                    continue

                workflow_id, resolved_inputs = route

                decision = self.policy.allow_run(
                    tenant_id=e.tenant_id,
                    actor_id=e.actor_id,
                    workflow_id=workflow_id,
                    resolved_inputs=resolved_inputs,
                    correlation_id=e.correlation_id,
                )
                if not decision.allowed:
                    if self.run_index:
                        try:
                            pending_run_id = str(uuid.uuid4())
                            pending_request = {
                                "workflow_id": workflow_id,
                                "tenant_id": e.tenant_id,
                                "actor_id": e.actor_id,
                                "correlation_id": e.correlation_id or "",
                                "resolved_inputs": resolved_inputs,
                                "dedup_key": e.dedup_key,
                            }
                            self.run_index.record_start(
                                run_id=pending_run_id,
                                workflow_id=workflow_id,
                                status="blocked",
                                correlation_id=e.correlation_id,
                                run_dir=None,
                                blocked_reason=getattr(decision, "reason", None) or "blocked by governance",
                                pending_request_json=json.dumps(pending_request),
                            )
                        except Exception:
                            pass
                    self.bus.ack(group=self.cfg.group, consumer=self.cfg.consumer, event_id=e.event_id)
                    continue

                if workflow_id == "swarm":
                    # Phase 5: swarm controller
                    from ..swarm import SwarmController
                    from ..swarm.contracts import SwarmPlan
                    tasks = resolved_inputs.get("swarm_tasks") or []
                    plan = SwarmPlan(
                        summary=resolved_inputs.get("summary", "swarm run"),
                        tasks=tasks,
                        max_children=min(resolved_inputs.get("max_children", 100), 100),
                        max_tool_calls_per_child=int(resolved_inputs.get("max_tool_calls_per_child", 50)),
                        max_wall_clock_s_per_child=int(resolved_inputs.get("max_wall_clock_s_per_child", 300)),
                        max_wall_clock_s=resolved_inputs.get("max_wall_clock_s"),
                        correlation_id=e.correlation_id or str(uuid.uuid4()),
                        tenant_id=e.tenant_id,
                        actor_id=e.actor_id,
                    )
                    controller = SwarmController(launcher=self.launcher)
                    controller.run(plan)
                else:
                    skip, skip_reason = should_skip_launch(workflow_id, resolved_inputs)
                    if skip:
                        import logging
                        logging.getLogger(__name__).debug(
                            "deferred launch workflow_id=%s reason=%s dedup_key=%s",
                            workflow_id,
                            skip_reason,
                            e.dedup_key,
                        )
                        self.bus.ack(group=self.cfg.group, consumer=self.cfg.consumer, event_id=e.event_id)
                        continue
                    rr = RunRequested(
                        request_id=str(uuid.uuid4()),
                        workflow_id=workflow_id,
                        tenant_id=e.tenant_id,
                        actor_id=e.actor_id,
                        correlation_id=e.correlation_id,
                        resolved_inputs=resolved_inputs,
                        dedup_key=e.dedup_key,
                    )
                    self.launcher.launch(rr)
                self.bus.ack(group=self.cfg.group, consumer=self.cfg.consumer, event_id=e.event_id)
                handled += 1
            except Exception:
                # at-least-once: do not ack on error, allow retry
                continue
        return handled

    def run_forever(self) -> None:
        while True:
            self.tick_once()
            time.sleep(0.01)
