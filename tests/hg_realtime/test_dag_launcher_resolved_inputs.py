"""DagLauncher passes scheduler resolved_inputs to run_dag_job."""

from hg_realtime.integrations.dag_launcher import _resolved_inputs_to_cli_args


def test_resolved_inputs_to_cli_args_flattens_scalars():
    args = _resolved_inputs_to_cli_args(
        {
            "task_name": "fourclaw-auto-post",
            "trigger": "realtime",
            "goal": "scheduled check",
            "platforms": ["fourclaw"],
        }
    )
    assert args == [
        "--input",
        "task_name=fourclaw-auto-post",
        "--input",
        "trigger=realtime",
        "--input",
        "goal=scheduled check",
    ]
