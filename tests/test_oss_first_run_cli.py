from __future__ import annotations

import json
from pathlib import Path

from hg_cli.cli import main
from hg_cli.config import build_config, load_config, save_config


def _config(tmp_path: Path, mode: str = "demo") -> Path:
    path = tmp_path / "config.json"
    save_config(build_config(mode=mode, config_path=path, data_dir=tmp_path / "data"), path)
    return path


def test_demo_init_writes_no_secrets_and_needs_no_keys(tmp_path, monkeypatch, capsys):
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "XAI_API_KEY", "HG_GATEWAY_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    path = tmp_path / "config.json"
    rc = main(["init", "--mode", "demo", "--non-interactive", "--config", str(path)])
    assert rc == 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["mode"] == "demo"
    assert payload["gateway"]["auth_mode"] == "local-no-key"
    assert payload["provider"]["key_env"] is None
    text = path.read_text(encoding="utf-8").lower()
    assert "sk-" not in text
    assert "api_key\"" not in text
    assert "no gateway or model-provider api keys are required" in capsys.readouterr().out.lower()


def test_local_init_validates_mocked_openai_compatible_endpoint(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setattr("hg_cli.cli.validate_openai_compatible_endpoint", lambda url: (True, f"mock ready {url}"))
    rc = main([
        "init", "--mode", "local", "--provider", "lm-studio",
        "--base-url", "http://127.0.0.1:1234/v1", "--model", "local-test-model",
        "--non-interactive", "--config", str(path),
    ])
    assert rc == 0
    config = load_config(path)
    assert config["provider"]["runtime_provider"] == "vllm"
    assert config["provider"]["key_env"] is None


def test_cloud_doctor_names_missing_selected_key_without_breaking_demo(tmp_path, monkeypatch, capsys):
    path = tmp_path / "config.json"
    config = build_config(mode="cloud", provider="openai", model="gpt-test", config_path=path, data_dir=tmp_path / "data")
    save_config(config, path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert main(["doctor", "--config", str(path)]) == 1
    output = capsys.readouterr().out
    assert "selected cloud mode requires OPENAI_API_KEY" in output
    assert "hg init --force --mode demo" in output


def test_config_show_is_always_redacted(tmp_path, capsys):
    path = _config(tmp_path)
    payload = load_config(path)
    payload["unexpected_secret"] = "do-not-print"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert main(["config", "show", "--redacted", "--config", str(path)]) == 0
    output = capsys.readouterr().out
    assert "do-not-print" not in output
    assert "[redacted]" in output


def test_chat_new_list_and_resume_use_persisted_active_chat(tmp_path, monkeypatch, capsys):
    path = _config(tmp_path)
    chats: dict[str, dict] = {}
    messages: dict[str, list[dict]] = {}

    def fake_request(_self, method, route, body=None):
        if method == "POST" and route == "/chats":
            chat_id = f"chat-{len(chats) + 1}"
            chat = {"chat_id": chat_id, "title": body["title"]}
            chats[chat_id] = chat
            messages[chat_id] = []
            return {"chat_id": chat_id, "chat": chat}
        if method == "GET" and route == "/chats":
            return {"chats": list(chats.values())}
        if method == "GET" and route.startswith("/chats/") and route.endswith("/messages"):
            return {"messages": messages[route.split("/")[2]]}
        if method == "GET" and route.startswith("/chats/"):
            chat_id = route.split("/")[2]
            return {"chat": chats[chat_id]}
        raise AssertionError((method, route, body))

    monkeypatch.setattr("hg_cli.client.GatewayClient.request", fake_request)
    assert main(["chat", "new", "--title", "One", "--config", str(path)]) == 0
    assert main(["chat", "new", "--title", "Two", "--config", str(path)]) == 0
    assert main(["chat", "list", "--config", str(path)]) == 0
    assert main(["chat", "resume", "chat-1", "--config", str(path)]) == 0
    output = capsys.readouterr().out
    assert "Created chat chat-1: One" in output
    assert "Created chat chat-2: Two" in output
    assert "Resumed chat-1: One" in output
    assert load_config(path)["state"]["active_chat_id"] == "chat-1"
