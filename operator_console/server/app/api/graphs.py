from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..core.auth import require_api_key
from ..services.graph_ops import validate_graph, review_graph, submit_run

router = APIRouter()

class GraphPayload(BaseModel):
    dag: dict

@router.post("/validate")
def validate(payload: GraphPayload, _=Depends(require_api_key)):
    return validate_graph(payload.dag)

@router.post("/review")
def review(payload: GraphPayload, _=Depends(require_api_key)):
    return review_graph(payload.dag)

@router.post("/run")
def run(payload: GraphPayload, _=Depends(require_api_key)):
    return submit_run(payload.dag)
