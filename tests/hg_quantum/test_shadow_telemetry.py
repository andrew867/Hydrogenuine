from __future__ import annotations

from hg_quantum.shadow_telemetry import record_shadow_event, shadow_summary


def test_record_and_summarize_shadow_events(tmp_path):
    record_shadow_event(
        "shell_model",
        "offset_compare",
        {"diverged": True, "child_count": 3},
        correlation_id="corr-1",
        workspace_root=tmp_path,
    )
    record_shadow_event(
        "shell_model",
        "offset_compare",
        {"diverged": False, "child_count": 3},
        workspace_root=tmp_path,
    )
    summary = shadow_summary(component="shell_model", workspace_root=tmp_path)
    assert summary["total_events"] == 2
    assert summary["divergent_events"] == 1
    assert summary["by_component"]["shell_model"] == 2
