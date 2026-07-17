"""G14 fingerprint-prior cognitive state compression API."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..core.auth import require_api_key
from ..services.fingerprint_compression_service import (
    decode_chunk,
    encode_stream,
    eval_fixtures,
    trajectory_stats,
)

router = APIRouter()


class EncodeBody(BaseModel):
    profile: Dict[str, Any]
    frames: List[Dict[str, Any]] = Field(default_factory=list)


class DecodeBody(BaseModel):
    profile: Dict[str, Any]
    chunk: Dict[str, Any]


@router.post("/compression/encode")
def post_encode(body: EncodeBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    return encode_stream(profile=body.profile, frames=body.frames)


@router.post("/compression/decode")
def post_decode(body: DecodeBody, _=Depends(require_api_key)) -> Dict[str, Any]:
    return decode_chunk(profile=body.profile, chunk=body.chunk)


@router.get("/compression/trajectory-stats")
def get_trajectory_stats(entity_id: str | None = None, _=Depends(require_api_key)) -> Dict[str, Any]:
    return trajectory_stats(entity_id=entity_id)


@router.get("/compression/eval-fixtures")
def get_eval_fixtures(_=Depends(require_api_key)) -> Dict[str, Any]:
    return eval_fixtures()
