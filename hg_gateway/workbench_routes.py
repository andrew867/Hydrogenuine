"""Agent Zero Workbench gateway routes — governed, Keycloak-verified, no effects.

Every endpoint verifies an `agent-zero-panel` (or gateway-ui) operator token via
the same fail-closed boundary the KLR operator-decision routes use. The actor is
derived from the verified Keycloak subject, never the request body. Runs, artifacts,
progress, steering, and settings are recorded as chained receipts; the Workbench
performs no external effects.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from hg_gateway.operator_auth_boundary import (
    OperatorAuthError, verify_operator_request,
)
from hg_workbench import WorkbenchRunStore
from hg_workbench.artifact_store import (
    ArtifactStoreError, ArtifactTooLargeError, max_upload_bytes,
)
from hg_workbench.run_store import RunIsolationError, WorkbenchError
from hg_workbench.receipts import verify_run_chain

_UPLOAD_CHUNK = 1024 * 1024

router = APIRouter()

_STORE: Optional[WorkbenchRunStore] = None


def _store() -> WorkbenchRunStore:
    global _STORE
    root = Path(os.environ.get("HG_WORKBENCH_DIR",
                               Path(os.environ.get("HG_GATEWAY_DATA_DIR", "."))
                               / "workbench_runs"))
    # Re-create if the configured dir changed (tests point it at tmp dirs).
    if _STORE is None or _STORE.root != root:
        _STORE = WorkbenchRunStore(root)
    return _STORE


def _operator(request: Request, *, step_up_required: bool = False):
    # Accept a Bearer token (API clients) OR a verified gateway cookie session
    # (the logged-in browser panel). Fail closed.
    try:
        return verify_operator_request(request, required_role="hg.operator",
                                       step_up_required=step_up_required)
    except OperatorAuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.code) from exc


def _wb_error(exc: WorkbenchError) -> HTTPException:
    status = 403 if isinstance(exc, RunIsolationError) else 400
    if exc.code == "run_not_found":
        status = 404
    return HTTPException(status_code=status, detail=exc.code)


@router.post("/workbench/runs")
def create_run(request: Request, body: Optional[dict] = Body(default=None)) -> dict:
    identity = _operator(request)
    body = body or {}
    request_text = str(body.get("request_text", "")).strip()
    if not request_text:
        raise HTTPException(status_code=400, detail="request_text required")
    run = _store().create_run(
        identity=identity, request_text=request_text,
        workflow_id=str(body.get("workflow_id", "adhoc")),
        risk_level=str(body.get("risk_level", "low")))
    return run.to_payload()


@router.get("/workbench/runs")
def list_runs(request: Request) -> dict:
    identity = _operator(request)
    return {"runs": [r.to_payload() for r in _store().list_runs(identity)]}


@router.get("/workbench/runs/{run_id}")
def get_run(run_id: str, request: Request) -> dict:
    identity = _operator(request)
    try:
        run = _store().get_run(run_id, identity)
    except WorkbenchError as exc:
        raise _wb_error(exc) from exc
    return run.to_payload()


@router.get("/workbench/runs/{run_id}/timeline")
def get_timeline(run_id: str, request: Request) -> dict:
    identity = _operator(request)
    try:
        chain = _store().read_chain(run_id, identity)
    except WorkbenchError as exc:
        raise _wb_error(exc) from exc
    return {"run_id": run_id, "receipts": chain,
            "chain": verify_run_chain(chain)}


@router.post("/workbench/runs/{run_id}/artifacts")
def add_artifact(run_id: str, request: Request,
                 body: Optional[dict] = Body(default=None)) -> dict:
    identity = _operator(request)
    body = body or {}
    content_hash = str(body.get("content_hash", ""))
    # Evidence integrity: the artifact receipt records content_hash, so require a
    # well-formed sha256 (the browser computes it via crypto.subtle). Reject junk.
    if not re.fullmatch(r"(sha256:)?[0-9a-f]{64}", content_hash):
        raise HTTPException(status_code=400, detail="content_hash must be sha256")
    try:
        artifact = _store().register_artifact(
            run_id=run_id, identity=identity,
            filename=str(body.get("filename", "artifact")),
            mime_type=str(body.get("mime_type", "application/octet-stream")),
            size_bytes=int(body.get("size_bytes", 0)),
            content_hash=content_hash,
            source=str(body.get("source", "upload")),
            document_ref=body.get("document_ref"))
    except WorkbenchError as exc:
        raise _wb_error(exc) from exc
    return artifact.to_payload()


@router.post("/workbench/runs/{run_id}/artifacts/upload")
async def upload_artifact(run_id: str, request: Request,
                          file: UploadFile = File(...),
                          expected_sha256: Optional[str] = Form(default=None),
                          sensitivity: str = Form(default="unclassified"),
                          label: str = Form(default="")) -> dict:
    """Upload real file *bytes* to the bounded local artifact store.

    The server streams the bytes under a hard size cap, computes the sha256
    itself, and records an artifact receipt holding hash/size/path-ref — never
    the bytes. ``expected_sha256`` (optional, from the browser's crypto.subtle)
    is a client expectation; a mismatch rejects the upload. No external storage,
    no execution.
    """
    identity = _operator(request)
    if expected_sha256 and not re.fullmatch(r"(sha256:)?[0-9a-f]{64}",
                                            expected_sha256.strip()):
        raise HTTPException(status_code=400, detail="expected_sha256 must be sha256")

    # Bounded async read: never trust Content-Length; stop the moment we exceed
    # the cap so a hostile client cannot spool an unbounded body to disk/memory.
    cap = max_upload_bytes()
    collected: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_UPLOAD_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > cap:
            raise HTTPException(status_code=413, detail="upload_too_large")
        collected.append(chunk)
    await file.close()

    try:
        artifact, receipt_hash = _store().register_uploaded_artifact(
            run_id=run_id, identity=identity,
            filename=file.filename or "upload.bin",
            mime_type=file.content_type or "application/octet-stream",
            chunks=collected, expected_sha256=expected_sha256,
            sensitivity=sensitivity, label=label)
    except ArtifactTooLargeError:
        raise HTTPException(status_code=413, detail="upload_too_large")
    except WorkbenchError as exc:
        if exc.code == "content_hash_mismatch":
            raise HTTPException(status_code=400, detail="content_hash_mismatch") from exc
        raise _wb_error(exc) from exc
    except ArtifactStoreError as exc:
        raise HTTPException(status_code=400, detail=exc.code) from exc

    payload = artifact.to_payload()
    payload.update({"receipt_hash": receipt_hash, "stored": True,
                    "external_storage": False})
    return payload


@router.get("/workbench/runs/{run_id}/events/stream")
def stream_events(run_id: str, request: Request) -> StreamingResponse:
    """Finite SSE catch-up of the run's receipt chain.

    Emits one ``event: receipt`` frame per receipt with ``seq`` greater than
    ``since_seq`` (query) or ``Last-Event-ID`` (header), then an ``event: end``
    frame and closes. The stream is *observation, not authority*: it appends
    nothing to the chain and can authorize no action. Finite so buffering test
    clients (and browsers) both terminate cleanly.
    """
    identity = _operator(request)
    try:
        chain = _store().read_chain(run_id, identity)
    except WorkbenchError as exc:
        raise _wb_error(exc) from exc

    since_seq = -1
    for cand in (request.query_params.get("since_seq"),
                 request.headers.get("last-event-id")):
        if cand is not None:
            try:
                since_seq = max(since_seq, int(cand))
            except (TypeError, ValueError):
                pass

    def _events():
        for receipt in chain:
            try:
                seq = int(receipt.get("seq", -1))
            except (TypeError, ValueError):
                continue
            if seq <= since_seq:
                continue
            data = json.dumps(receipt, separators=(",", ":"))
            yield f"id: {seq}\nevent: receipt\ndata: {data}\n\n"
        # Explicit terminal frame reaffirming the stream never carries authority.
        yield 'event: end\ndata: {"authority":false,"stream":"observation"}\n\n'

    return StreamingResponse(
        _events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no",
                 "Connection": "close"})


@router.post("/workbench/runs/{run_id}/progress")
def add_progress(run_id: str, request: Request,
                 body: Optional[dict] = Body(default=None)) -> dict:
    identity = _operator(request)
    body = body or {}
    try:
        event = _store().append_progress(
            run_id=run_id, identity=identity,
            event_type=str(body.get("event_type", "model_progress")),
            subagent_lane_id=body.get("subagent_lane_id"),
            persona=body.get("persona"), detail=str(body.get("detail", "")))
    except WorkbenchError as exc:
        raise _wb_error(exc) from exc
    return event.to_payload()


@router.post("/workbench/runs/{run_id}/steering")
def add_steering(run_id: str, request: Request,
                 body: Optional[dict] = Body(default=None)) -> dict:
    identity = _operator(request)
    body = body or {}
    text = str(body.get("text", "")).strip()
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    try:
        msg = _store().append_steering(run_id=run_id, identity=identity, text=text)
    except WorkbenchError as exc:
        raise _wb_error(exc) from exc
    return msg.to_payload()


@router.post("/workbench/runs/{run_id}/settings")
def change_setting(run_id: str, request: Request,
                   body: Optional[dict] = Body(default=None)) -> dict:
    body = body or {}
    action_class = str(body.get("action_class", "configuration"))
    # High/restricted/breakglass changes need step-up evidence captured from the
    # token at verification time (amr/acr) — request it so the identity carries it.
    from hg_operator_auth.stepup_policy import ACTION_CLASS_POLICY
    risk = ACTION_CLASS_POLICY.get(action_class, ("high", ""))[0]
    identity = _operator(request,
                         step_up_required=risk in ("high", "restricted", "breakglass"))
    try:
        change = _store().request_setting_change(
            run_id=run_id, identity=identity,
            setting=str(body.get("setting", "")),
            action_class=str(body.get("action_class", "configuration")),
            old_value=str(body.get("old_value", "")),
            new_value=str(body.get("new_value", "")))
    except WorkbenchError as exc:
        raise _wb_error(exc) from exc
    payload = change.to_payload()
    if not change.applied:
        # Held pending step-up: 403 with the reason + the receipted change id.
        raise HTTPException(status_code=403, detail={
            "code": "setting_change_held", "reason": change.hold_reason,
            "change_id": change.change_id, "setting": change.setting})
    return payload


__all__ = ["router"]
