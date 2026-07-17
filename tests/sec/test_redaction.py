"""CT-02 redaction unit tests."""

from __future__ import annotations

import os

import pytest

from hg_core.secrets.canary import CANARY_MARKERS, plant_canary_env, clear_canary_env
from hg_core.secrets.crash import format_crash_report
from hg_core.secrets.redact import (
    RedactionFailure,
    contains_leak,
    redact_or_refuse,
    redact_payload,
    redact_text,
    refuse_if_leak,
)
from hg_mel.ledger import MaintenanceLedger
from hg_plt.redaction import redact_payload as plt_redact
from hg_ter.redaction import redact_text as ter_redact


def setup_function() -> None:
    clear_canary_env()


def teardown_function() -> None:
    clear_canary_env()


def test_sec_u3_receipt_redaction() -> None:
    plant_canary_env()
    payload = {"api_key": os.environ["HG_CANARY_SECRET_RECEIPT"], "note": "ok"}
    redacted = redact_payload(payload)
    assert redacted["api_key"] == "[REDACTED]"
    assert not contains_leak(redacted)


def test_sec_u4_ter_output_redacted() -> None:
    text, applied = ter_redact(f"api_key={CANARY_MARKERS['ter']} Bearer abcdefghijklmnop")
    assert applied
    assert CANARY_MARKERS["ter"] not in text
    assert "abcdefghijklmnop" not in text


def test_sec_u5_crash_log_clean() -> None:
    plant_canary_env()
    report = format_crash_report(
        RuntimeError(f"boom {CANARY_MARKERS['crash']}"),
        env=dict(os.environ),
    )
    assert CANARY_MARKERS["crash"] not in report
    assert not contains_leak(report)


def test_sec_i1_live_config_dump_redacted() -> None:
    config = {
        "provider": "openai",
        "api_key": "sk-abcdefghijklmnopqrstuvwxyz123456",
        "base_url": "http://localhost:8000/v1",
    }
    redacted = redact_payload(config)
    assert "sk-abc" not in str(redacted)
    assert redacted["api_key"] == "[REDACTED]"


def test_sec_i2_plt_response_fixture() -> None:
    payload = plt_redact({"api_key": "secret123", "note": "Bearer abcdefghijklmnop"})
    assert payload["api_key"] == "[REDACTED]"
    assert not contains_leak(payload)


def test_redact_or_refuse_blocks_leak() -> None:
    with pytest.raises(RedactionFailure):
        refuse_if_leak({"token": CANARY_MARKERS["event"]})


def test_mel_ledger_redacts_canary(tmp_path) -> None:
    ledger = MaintenanceLedger(tmp_path / "mel.jsonl")
    record = ledger.append(
        "test",
        source_subsystem="sec",
        subject_id="subj",
        subject_hash="sha256:subj",
        payload={"api_key": CANARY_MARKERS["receipt"]},
    )
    assert CANARY_MARKERS["receipt"] not in str(record.payload_redacted)


def test_redact_or_refuse_positive() -> None:
    clean = redact_or_refuse({"status": "ok"})
    assert clean["status"] == "ok"
