import uuid
from .worker_adapter import run_inprocess
from .run_index_db import upsert_run
from .validator_adapter import validate
from .review_adapter import review

def validate_graph(dag: dict) -> dict:
    return validate(dag)

def review_graph(dag: dict) -> dict:
    return review(dag)

def submit_run(dag: dict) -> dict:
    run_id = str(uuid.uuid4())
    res = run_inprocess(run_id, dag)
    upsert_run(res)
    return {"ok": True, "run_id": run_id, "status": res.get("status")}
