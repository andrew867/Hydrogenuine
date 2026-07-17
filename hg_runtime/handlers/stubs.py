"""RTC Phase 0 stub handlers.

These stubs are real in shape but deliberately narrow:

* cognition only emits proposals and holds no tool handles
* decision only turns candidate proposals into decision events
* kernel is the UEAK/OEA boundary stub and only records committed effects
* memory and regulation are evented, deterministic placeholders
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from hg_runtime.contract import Event, draft, stable_id


class StubCognitionHandler:
    """Proposal-only cognition double for Phase 0 tests and demos."""

    handler_id = "rtc.stub.cognition"

    def __init__(self) -> None:
        self.calls = 0
        self.halted = False

    def propose(self, context: Mapping[str, Any]) -> List[Dict[str, Any]]:
        self.calls += 1
        events = list(context.get("events", []))
        if not events:
            return []
        trigger = events[0]
        proposal_id = stable_id("prop", trigger["event_id"], self.calls)
        request_digest = stable_id("req", trigger["event_id"])
        response_digest = stable_id("resp", proposal_id, trigger["type"])
        return [
            draft(
                "PROPOSAL_EMITTED",
                {
                    "proposal_id": proposal_id,
                    "kind": "candidate_action",
                    "content": {
                        "action_type": "oea_stub_log",
                        "capability_id": "cap.oea_stub_log",
                        "effect_class": "audit_log",
                        "summary": f"acknowledge {trigger['type']}",
                        "trigger_event_id": trigger["event_id"],
                        "governance_trace_refs": [],
                    },
                    "model": "rtc-phase0-stub",
                    "request_digest": request_digest,
                    "response_digest": response_digest,
                    "params": {"temperature": 0.0, "seed": 0},
                },
                causal_parents=[trigger["event_id"]],
            )
        ]

    def halt(self) -> None:
        self.halted = True


class StubDecisionHandler:
    """Minimal SOAR/HAL/GPP-shaped decision double."""

    handler_id = "rtc.stub.decision"

    def evaluate(
        self,
        events: Sequence[Event],
        proposals: Sequence[Event],
        view: Mapping[str, Any],
        aep_state: Mapping[str, Any],
    ) -> List[Dict[str, Any]]:
        del events, view, aep_state
        decisions: List[Dict[str, Any]] = []
        for proposal in proposals:
            payload = proposal.get("payload", {})
            if payload.get("kind") != "candidate_action":
                decisions.append(
                    draft(
                        "DECISION_BLOCKED",
                        {
                            "proposal_id": payload.get("proposal_id"),
                            "reason": "not_candidate_action",
                        },
                        causal_parents=[proposal["event_id"]],
                    )
                )
                continue
            decision_id = stable_id("dec", proposal["event_id"])
            decisions.append(
                draft(
                    "DECISION_EVENT",
                    {
                        "decision_id": decision_id,
                        "proposal_id": payload["proposal_id"],
                        "verdict": "allow_stub",
                        "authority_ref": "phase0-stub",
                        "action": payload["content"],
                    },
                    causal_parents=[proposal["event_id"]],
                )
            )
        return decisions


class StubKernelHandler:
    """UEAK/OEA boundary stub: commit via UEAK, externalize via OEA only."""

    handler_id = "rtc.stub.kernel"

    def __init__(self, *, ueak=None, oea=None) -> None:
        from hg_oea.stub import OEAStub
        from hg_ueak.stub import UEAKStub

        self._ueak = ueak or UEAKStub()
        self._oea = oea or OEAStub()

    @property
    def committed_actions(self) -> List[Dict[str, Any]]:
        return self._ueak.committed_requests

    @property
    def blocked(self) -> bool:
        return self._ueak.blocked

    def execute(
        self, decisions: Sequence[Event], view: Mapping[str, Any]
    ) -> List[Dict[str, Any]]:
        ueak_drafts = self._ueak.execute(decisions, view)
        committed = [
            draft for draft in ueak_drafts if draft["type"] == "UEAK_EXECUTION_COMMITTED"
        ]
        if not committed:
            return ueak_drafts
        # OEA only sees UEAK_EXECUTION_COMMITTED refs — never raw decisions.
        oea_drafts = self._oea.dispatch_committed(
            [
                {
                    "type": "UEAK_EXECUTION_COMMITTED",
                    "event_id": stable_id("evt", draft["payload"]["commit_ref"]),
                    "payload": draft["payload"],
                }
                for draft in committed
            ]
        )
        return [*ueak_drafts, *oea_drafts]

    def block_all(self) -> None:
        self._ueak.block_all()

    def unblock(self) -> None:
        self._ueak.unblock()


class StubMemoryHandler:
    """Derived-memory placeholder: retrieval and write-back are evented."""

    handler_id = "rtc.stub.memory"

    def retrieve(
        self, view: Mapping[str, Any], events: Sequence[Event]
    ) -> Mapping[str, Any]:
        del view
        refs = [event["event_id"] for event in events]
        return {
            "context": {"recent_event_refs": refs},
            "provenance": {"query": "phase0_recent_events", "result_refs": refs},
        }

    def store(
        self,
        events: Sequence[Event],
        proposals: Sequence[Event],
        results: Sequence[Event],
    ) -> List[Dict[str, Any]]:
        refs = [event["event_id"] for event in events]
        refs.extend(proposal["event_id"] for proposal in proposals)
        refs.extend(result["event_id"] for result in results)
        return [
            draft(
                "MEMORY_WRITTEN",
                {
                    "memory_ref": stable_id("mem", *refs) if refs else "mem_empty",
                    "event_refs": refs,
                    "store": "phase0-stub",
                },
                causal_parents=refs[:64],
            )
        ]


class StubArousalReader:
    """AEP-shaped reader. It reports modulation state; it grants no authority."""

    handler_id = "rtc.stub.arousal"

    def read(
        self, events: Sequence[Event], view: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        del view
        max_severity = max((event.get("severity") or 0 for event in events), default=0)
        dimensions: Dict[str, int] = {}
        for event in events:
            if event["type"] != "AEP_SIGNAL_EMITTED":
                continue
            payload = event.get("payload", {})
            signal_class = str(payload.get("class", "UNKNOWN"))
            severity = int(payload.get("severity", 0))
            dimensions[signal_class] = max(dimensions.get(signal_class, 0), severity)
            max_severity = max(max_severity, severity)
        return {"max_severity": int(max_severity), "dimensions": dimensions}


class StubRecoveryHandler:
    """CRR-shaped recovery stub, disabled unless a test opts in."""

    handler_id = "rtc.stub.recovery"

    def __init__(self, cycle_every: int = 0) -> None:
        self.cycle_every = cycle_every
        self.checks = 0
        self.safe_state = False

    def should_enter_cycle(
        self, view: Mapping[str, Any], aep_state: Mapping[str, Any]
    ) -> bool:
        del view, aep_state
        self.checks += 1
        return bool(self.cycle_every and self.checks % self.cycle_every == 0)

    def execute_cycle(self) -> List[Dict[str, Any]]:
        cycle_id = stable_id("crr", self.checks)
        return [
            draft(
                "RECOVERY_STATE_CHANGED",
                {"state": "NORMAL", "cycle_id": cycle_id, "level": "phase0_stub"},
            )
        ]

    def enter_safe_state(self) -> None:
        self.safe_state = True
