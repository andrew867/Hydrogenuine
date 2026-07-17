"""Upload + SSE gateway route tests (WBT cases 7-19).

Real file bytes through the governed upload endpoint into the bounded local
store; server-side sha256; receipts hold hash/size/path-ref, never bytes; finite
SSE catch-up that authorizes nothing; full auth/isolation negatives.
"""
from __future__ import annotations

import hashlib
import io
import json

import pytest

from tests.workbench_transport.conftest import mint

RAW_SENTINEL = b"RAWBYTES-MARKER-8f2c1a payload contents that must never be receipted"


def _b(tok):
    return {"Authorization": f"Bearer {tok}"}


def _run(c, tok):
    r = c.post("/v1/workbench/runs", headers=_b(tok), json={"request_text": "x"})
    assert r.status_code == 200, r.text
    return r.json()["run_id"]


def _upload(c, tok, run_id, data, *, filename="doc.txt", expected=None, extra=None):
    fields = {}
    if expected is not None:
        fields["expected_sha256"] = expected
    if extra:
        fields.update(extra)
    return c.post(f"/v1/workbench/runs/{run_id}/artifacts/upload", headers=_b(tok),
                  files={"file": (filename, io.BytesIO(data), "text/plain")},
                  data=fields)


# ---- upload (cases 7-14) ----

def test_case7_upload_stores_bytes_and_server_hash(client, rsa_keys):
    c, sink = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-7")
    run_id = _run(c, tok)
    r = _upload(c, tok, run_id, RAW_SENTINEL, filename="contract.txt", extra={"label": "c"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["source"] == "upload_bytes"
    assert j["content_hash"] == "sha256:" + hashlib.sha256(RAW_SENTINEL).hexdigest()
    assert j["size_bytes"] == len(RAW_SENTINEL)
    assert j["stored"] is True and j["external_storage"] is False
    assert j["stored_path_ref"].startswith("artifacts/")
    # the bytes really landed on disk
    assert (sink / run_id / j["stored_path_ref"]).read_bytes() == RAW_SENTINEL


def test_case8_filename_sanitized(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-8")
    run_id = _run(c, tok)
    j = _upload(c, tok, run_id, b"x", filename="../../evil name.txt").json()
    assert ".." not in j["filename"] and "/" not in j["filename"]
    assert j["filename"] == "evil_name.txt"


def test_case9_raw_bytes_absent_from_receipt_chain(client, rsa_keys):
    c, sink = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-9")
    run_id = _run(c, tok)
    _upload(c, tok, run_id, RAW_SENTINEL)
    chain = (sink / run_id / "receipt_chain.jsonl").read_text(encoding="utf-8")
    assert b"RAWBYTES-MARKER".decode() not in chain      # bytes never receipted
    assert hashlib.sha256(RAW_SENTINEL).hexdigest() in chain  # only the hash


def test_case10_expected_hash_match_and_mismatch(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-10")
    run_id = _run(c, tok)
    good = hashlib.sha256(b"abc").hexdigest()
    assert _upload(c, tok, run_id, b"abc", expected=good).status_code == 200
    r = _upload(c, tok, run_id, b"abc", expected="0" * 64)
    assert r.status_code == 400
    assert r.json()["detail"] == "content_hash_mismatch"


def test_case11_oversize_rejected_413(client, rsa_keys, monkeypatch):
    c, sink = client
    monkeypatch.setenv("HG_WORKBENCH_MAX_UPLOAD_BYTES", "16")
    tok = mint(rsa_keys, roles=("operator",), sub="op-11")
    run_id = _run(c, tok)
    r = _upload(c, tok, run_id, b"x" * 64)
    assert r.status_code == 413
    # nothing persisted for the rejected upload
    art_dir = sink / run_id / "artifacts"
    assert not art_dir.exists() or not any(art_dir.iterdir())


def test_case12_malformed_expected_hash_400(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-12")
    run_id = _run(c, tok)
    r = _upload(c, tok, run_id, b"x", expected="not-a-hash")
    assert r.status_code == 400


def test_case13_unauth_and_cross_operator_denied(client, rsa_keys):
    c, sink = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-13a")
    run_id = _run(c, tok)
    # unauthenticated
    r0 = c.post(f"/v1/workbench/runs/{run_id}/artifacts/upload",
                files={"file": ("a", io.BytesIO(b"z"), "text/plain")})
    assert r0.status_code == 401
    # different operator cannot upload to this run
    other = mint(rsa_keys, roles=("operator",), sub="op-13b")
    assert _upload(c, other, run_id, b"z").status_code == 403


def test_case14_upload_to_missing_run_404(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-14")
    r = _upload(c, tok, "wbr-deadbeef-0000-0000-0000-000000000000", b"z")
    assert r.status_code == 404


# ---- SSE (cases 15-19) ----

def test_case15_sse_catchup_is_finite_and_typed(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-15")
    run_id = _run(c, tok)
    _upload(c, tok, run_id, b"hello")
    r = c.get(f"/v1/workbench/runs/{run_id}/events/stream", headers=_b(tok))
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    body = r.text                       # finite: TestClient returns the full body
    assert body.count("event: receipt") == 2   # run_created + artifact_registered
    assert "event: end" in body
    assert "id: 0" in body and "id: 1" in body


def test_case16_sse_is_observation_not_authority(client, rsa_keys):
    c, sink = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-16")
    run_id = _run(c, tok)
    before = (sink / run_id / "receipt_chain.jsonl").read_text(encoding="utf-8")
    body = c.get(f"/v1/workbench/runs/{run_id}/events/stream", headers=_b(tok)).text
    after = (sink / run_id / "receipt_chain.jsonl").read_text(encoding="utf-8")
    # streaming appended nothing to the authoritative chain
    assert before == after
    # the terminal frame declares non-authority explicitly
    assert '"authority":false' in body


def test_case17_sse_since_seq_filters(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-17")
    run_id = _run(c, tok)
    _upload(c, tok, run_id, b"hello")
    r = c.get(f"/v1/workbench/runs/{run_id}/events/stream?since_seq=0", headers=_b(tok))
    body = r.text
    # seq 0 (run_created) filtered out; only seq>0 (artifact_registered) streams
    assert body.count("event: receipt") == 1
    assert "id: 0\n" not in body


def test_case18_sse_last_event_id_header(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-18")
    run_id = _run(c, tok)
    _upload(c, tok, run_id, b"hello")
    r = c.get(f"/v1/workbench/runs/{run_id}/events/stream",
              headers={**_b(tok), "Last-Event-ID": "1"})
    assert r.text.count("event: receipt") == 0   # everything already seen


def test_case19_sse_auth_isolation(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator",), sub="op-19a")
    run_id = _run(c, tok)
    # unauthenticated
    assert c.get(f"/v1/workbench/runs/{run_id}/events/stream").status_code == 401
    # cross-operator
    other = mint(rsa_keys, roles=("operator",), sub="op-19b")
    assert c.get(f"/v1/workbench/runs/{run_id}/events/stream",
                 headers=_b(other)).status_code == 403
    # missing run
    assert c.get("/v1/workbench/runs/wbr-deadbeef-0000-0000-0000-000000000000/events/stream",
                 headers=_b(tok)).status_code == 404
