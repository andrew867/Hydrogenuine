from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_public_root_docs_and_scripts_exist() -> None:
    required = [
        "README.md",
        "INSTALL.md",
        "CONFIGURATION.md",
        "TROUBLESHOOTING.md",
        "SECURITY.md",
        "CONTRIBUTING.md",
        "LICENSE",
        "NOTICE",
        "THIRD_PARTY_NOTICES.md",
        "TRADEMARKS.md",
        "docker-compose.yml",
        ".env.example",
        "start.ps1",
        "start.sh",
        "stop.ps1",
        "stop.sh",
        "doctor.ps1",
        "doctor.sh",
        "demo.ps1",
        "demo.sh",
        "examples/offline_demo.py",
        "examples/plugins/echo_plugin.py",
        "tools/verify_no_bytecode_only_export.py",
        "docs/community/quickstart.md",
        "docs/community/multi_chat.md",
        "docs/community/architecture.md",
        "docs/community/api.md",
        "docs/community/security_privacy.md",
        "docs/community/plugins.md",
        ".github/ISSUE_TEMPLATE/bug_report.md",
        ".github/ISSUE_TEMPLATE/feature_request.md",
        ".github/pull_request_template.md",
        ".github/workflows/ci.yml",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    assert missing == []


def test_public_docs_describe_community_not_internal_stack() -> None:
    readme = read("README.md")
    assert "Hydrogenuine Community" in readme
    assert "http://127.0.0.1:4173" in readme
    assert "no gateway key, cloud key, LM Studio" in readme
    assert "hg chat resume" in readme
    assert "enterprise SSO" in readme
    assert "Investor" not in readme
    assert "internal operator control plane" not in readme


def test_packaging_files_use_safe_local_defaults() -> None:
    compose = read("docker-compose.yml")
    env = read(".env.example")
    assert "HG_COMMUNITY_DATA_DIR" in compose
    assert "oss-demo-key" in compose
    assert "HG_GATEWAY_AUTH_MODE=local-no-key" in env
    assert "HG_GATEWAY_STORE=sqlite" in env
    assert "HG_GATEWAY_API_KEY=" not in env
    assert ("OPENAI" + "_API_KEY=") not in env
    assert "C:\\Users\\" not in read("README.md")


def test_extension_contract_mentions_leases_and_receipts() -> None:
    plugins = read("docs/community/plugins.md")
    security = read("docs/community/security_privacy.md")
    assert "lease" in plugins.lower()
    assert "receipt" in plugins.lower()
    assert "Telemetry is off" in security


def test_api_docs_and_ci_cover_release_gates() -> None:
    api = read("docs/community/api.md")
    ci = read(".github/workflows/ci.yml")
    assert "/v1/chats/{chat_id}/messages/stream" in api
    assert "/v1/leases" in api
    assert "test_community_backend_acceptance.py" in ci
    assert "verify_no_bytecode_only_export.py" in ci
