"""Event-driven lease invalidation — races fail closed.

Subscribes to situation-fact changes. When a fact relevant to an active lease
changes, the lease is suspended *first* (deny window), then re-evaluated:
- conditions still satisfiable -> resumed;
- conditions violated -> stays suspended with reason;
- close obligations whose trigger matches -> emitted as ObligationDue.

Revocation events always win over concurrent execution: the suspension happens
synchronously inside the fact-change callback, before any new authorization
can observe the changed world through an ACTIVE lease.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from hg_lease.gpp_bridge import LeaseAuthority
from hg_lease.policy import EvalContext
from hg_lease.stores import LeaseStore, SituationFact, SituationStore


@dataclass(frozen=True)
class ObligationDue:
    lease_id: str
    obligation: dict[str, Any]
    triggered_by_fact: str
    at_wall: str


class SituationInvalidator:
    """Wires SituationStore change events to lease suspension/resumption."""

    def __init__(
        self,
        *,
        authority: LeaseAuthority,
        lease_store: LeaseStore,
        situation_store: SituationStore,
        clock: Callable[[], tuple[str, float]],
        obligation_sink: Optional[Callable[[ObligationDue], None]] = None,
    ) -> None:
        self._authority = authority
        self._leases = lease_store
        self._situation = situation_store
        self._clock = clock
        self._obligation_sink = obligation_sink
        situation_store.subscribe(self.on_fact_changed)

    def _fact_names(self, condition: Any) -> set[str]:
        names: set[str] = set()
        if condition is None:
            return names
        payload = condition.to_payload()

        def walk(node: dict[str, Any]) -> None:
            if node.get("type") == "fact":
                names.add(node["fact_name"])
            for child in node.get("children", []) or []:
                walk(child)
            if node.get("child"):
                walk(node["child"])

        walk(payload)
        return names

    def on_fact_changed(
        self, fact: SituationFact, previous: Optional[SituationFact]
    ) -> None:
        now_wall, _ = self._clock()
        for lease in list(self._leases.all()):
            if lease.state not in ("ACTIVE", "SUSPENDED"):
                continue
            policy = self._authority.policy_for(lease)
            if policy is None:
                continue
            relevant = self._fact_names(policy.condition)
            watched = relevant | set(policy.required_facts)
            if fact.name not in watched:
                self._check_obligations(lease, policy, fact, now_wall)
                continue

            # Fail closed: suspend before re-evaluating so no authorization
            # can race through an ACTIVE lease against a stale world.
            if lease.state == "ACTIVE":
                self._authority.suspend_lease(
                    lease.lease_id,
                    reason_code=f"invalidation.fact_changed:{fact.name}",
                )

            snapshot = self._situation.snapshot(now_wall=now_wall)
            missing = [n for n in policy.required_facts if n not in snapshot]
            ok = not missing
            if ok and policy.condition is not None:
                res = policy.condition.evaluate(
                    EvalContext(facts=dict(snapshot), now_wall=now_wall)
                )
                # Only fact-condition health matters here; time windows govern
                # per-request evaluation, not standing validity.
                fact_failures = [
                    r
                    for r in res.reasons
                    if not r.startswith("policy.outside_time_window")
                ]
                ok = res.ok or not fact_failures
            if ok:
                self._authority.resume_lease(
                    lease.lease_id,
                    reason_code=f"invalidation.fact_recovered:{fact.name}",
                )
            self._check_obligations(lease, policy, fact, now_wall)

    def _check_obligations(
        self, lease: Any, policy: Any, fact: SituationFact, now_wall: str
    ) -> None:
        if self._obligation_sink is None:
            return
        for obligation in policy.close_obligations:
            trigger = obligation.get("trigger_fact")
            if trigger != fact.name:
                continue
            expected = obligation.get("trigger_value")
            if expected is not None and fact.typed_value != expected:
                continue
            self._obligation_sink(
                ObligationDue(
                    lease_id=lease.lease_id,
                    obligation=dict(obligation),
                    triggered_by_fact=fact.name,
                    at_wall=now_wall,
                )
            )
