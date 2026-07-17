"""OpenVINO Windows provider example config contract tests."""

from __future__ import annotations

import json
import re
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
EXAMPLE_CONFIG = WORKSPACE / "configs" / "local_inference" / "openvino_windows.example.json"
CONTRACT_DOC = WORKSPACE / "hg_runtime" / "local_inference" / "providers" / "openvino_windows_provider_contract.md"
GITIGNORE = WORKSPACE / ".gitignore"

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s]{8,}"),
)


def test_example_config_schema() -> None:
    assert EXAMPLE_CONFIG.is_file(), "example config must exist"
    cfg = json.loads(EXAMPLE_CONFIG.read_text(encoding="utf-8"))
    assert cfg["backend_id"] == "windows-openvino-igpu"
    assert cfg["backend_type"] == "openvino_windows"
    assert cfg["base_url"] == "http://host.docker.internal:18080/v1"
    assert cfg["v3_base_url"] == "http://host.docker.internal:18080/v3"
    assert cfg["device"] == "AUTO"
    assert cfg["advisory_only"] is True
    assert cfg["permission_granted"] is False
    assert cfg["authority_created"] is False
    assert cfg["timeout_seconds"] == 60


def test_example_config_no_secrets() -> None:
    raw = EXAMPLE_CONFIG.read_text(encoding="utf-8")
    for pattern in SECRET_PATTERNS:
        assert not pattern.search(raw), "secrets must not appear in example config"


def test_endpoint_url_construction() -> None:
    cfg = json.loads(EXAMPLE_CONFIG.read_text(encoding="utf-8"))
    base = cfg["base_url"].rstrip("/")
    assert base.endswith("/v1")
    host_root = base[: -len("/v1")]
    assert cfg["v3_base_url"] == f"{host_root}/v3"


def test_contract_doc_exists() -> None:
    assert CONTRACT_DOC.is_file()
    text = CONTRACT_DOC.read_text(encoding="utf-8")
    assert "advisory_only" in text
    assert "permission_granted" in text
    assert "Model proposes" in text


def test_gitignore_covers_local_provider_state() -> None:
    text = GITIGNORE.read_text(encoding="utf-8")
    for entry in (".hg-local/", "*.pid", "openvino_provider_test_report.json", ".env.openvino"):
        assert entry in text, f"missing gitignore entry: {entry}"
