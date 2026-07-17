from __future__ import annotations

from hg_quantum.coordination.kpz_predictor import KpzTransportPredictor
from hg_quantum.entanglement.shell_model import ShellModel
from hg_realtime.swarm.contracts import SwarmPlan


def test_kpz_sizing_is_shell_aware():
    tasks = [
        {"entity_id": "p1", "role": "planner"},
        {"entity_id": "w1", "role": "worker"},
        {"entity_id": "w2", "role": "worker"},
        {"entity_id": "v1", "role": "verifier"},
    ]
    assignment = ShellModel().assign_shells(SwarmPlan(summary="kpz", tasks=tasks))
    shell_sizes = {shell: len(members) for shell, members in assignment.shells.items() if members}
    predictor = KpzTransportPredictor(shell_aware=True)
    per_shell = predictor.predict_per_shell("coding", shell_sizes)
    assert set(per_shell) == set(shell_sizes)
    assert all(p.recommended_size >= 1 for p in per_shell.values())
    assert len(per_shell) == len(shell_sizes)
