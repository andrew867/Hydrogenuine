# Swarm spawn/reduce, contracts, and controller (Phase 5)
from .contracts import MAX_SWARM_CHILDREN, QuantumSwarmPlan, SwarmPlan, SwarmResult
from .nodes import swarm_spawn, swarm_reduce
from .quantum_nodes import swarm_reduce_quantum, swarm_spawn_quantum, reduce_for_plan
from .controller import SwarmController

__all__ = [
    "MAX_SWARM_CHILDREN",
    "SwarmPlan",
    "QuantumSwarmPlan",
    "SwarmResult",
    "SwarmController",
    "swarm_spawn",
    "swarm_reduce",
    "swarm_spawn_quantum",
    "swarm_reduce_quantum",
    "reduce_for_plan",
]
