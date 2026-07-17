from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from operator_console.server.app.main import app as operator_app

FIXTURES = Path(__file__).resolve().parents[2] / "evals/g14/cognitive_state_streams/fixtures.json"


@pytest.fixture
def operator_client():
    return TestClient(operator_app)


def test_compression_encode_decode_and_eval(operator_client):
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    stream = data["streams"][0]
    profile = data["profiles"][stream["profile_key"]]
    frames = [
        {**f, "entity_id": stream["entity_id"]}
        for f in stream["frames"][:6]
    ]
    headers = {"Authorization": "Bearer test-api-key"}
    enc = operator_client.post(
        "/api/v1/fingerprint/compression/encode",
        headers=headers,
        json={"profile": profile, "frames": frames},
    )
    assert enc.status_code == 200
    body = enc.json()
    assert body["ok"] is True
    assert body["report"]["compression_ratio"] >= 1.5
    dec = operator_client.post(
        "/api/v1/fingerprint/compression/decode",
        headers=headers,
        json={"profile": profile, "chunk": body["chunk"]},
    )
    assert dec.status_code == 200
    assert len(dec.json()["frames"]) == 6
    ev = operator_client.get("/api/v1/fingerprint/compression/eval-fixtures", headers=headers)
    assert ev.status_code == 200
    assert ev.json()["ok"] is True
