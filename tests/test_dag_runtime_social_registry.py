"""DAG registry must include social-media for realtime scheduler launches."""

from scripts.dag_runtime_jobs import DAG_JOB_REGISTRY, get_runtime_job


def test_social_media_in_dag_registry():
    job = get_runtime_job("social-media")
    assert job is not None
    assert job.job_id == "social-media"
    assert job.dag_path == "memory/automation/dags/social_media.json"


def test_auto_post_jobs_still_registered():
    for job_id in ("moltbook-auto-post", "fourclaw-auto-post-cadence"):
        assert job_id in DAG_JOB_REGISTRY
