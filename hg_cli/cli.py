"""Unified public ``hg`` command."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from hg_cli.client import GatewayClient, GatewayError
from hg_cli.config import (
    CLOUD_KEY_ENVS,
    ConfigError,
    build_config,
    default_config_path,
    load_config,
    redacted_config,
    save_config,
    validate_openai_compatible_endpoint,
)


def _path(value: str | None) -> Path | None:
    return Path(value).expanduser().resolve() if value else None


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _interactive_init(args: argparse.Namespace) -> None:
    print("Hydrogenuine Community setup")
    print("1) Demo/mock: offline, deterministic, no keys")
    print("2) Local model: LM Studio or another OpenAI-compatible endpoint")
    print("3) Cloud provider: key remains in an environment variable")
    print("4) Private/commercial stack: records the boundary; components are not in this repository")
    choice = input("Choose a mode [1]: ").strip() or "1"
    args.mode = {"1": "demo", "2": "local", "3": "cloud", "4": "private"}.get(choice, choice)
    if args.mode == "local":
        args.provider = input("Provider [lm-studio]: ").strip() or "lm-studio"
        default_url = "http://127.0.0.1:1234/v1" if args.provider == "lm-studio" else "http://127.0.0.1:11434/v1"
        args.base_url = input(f"OpenAI-compatible base URL [{default_url}]: ").strip() or default_url
        args.model = input("Model name [local-model]: ").strip() or "local-model"
    elif args.mode == "cloud":
        args.provider = input("Provider (openai/anthropic/google/xai) [openai]: ").strip() or "openai"
        args.model = input("Model name (optional): ").strip() or None
        args.key_env = input(f"Key environment variable [{CLOUD_KEY_ENVS.get(args.provider, 'OPENAI_API_KEY')}]: ").strip() or None


def command_init(args: argparse.Namespace) -> int:
    config_path = _path(args.config) or default_config_path()
    if config_path.exists() and not args.force:
        print(f"Configuration already exists at {config_path}")
        print("Use 'hg config show --redacted' to inspect it, or 'hg init --force' to replace it.")
        return 0
    if not args.non_interactive and not args.mode:
        _interactive_init(args)
    mode = (args.mode or "demo").lower()
    try:
        config = build_config(
            mode=mode,
            config_path=config_path,
            data_dir=_path(args.data_dir),
            provider=args.provider,
            base_url=args.base_url,
            model=args.model,
            key_env=args.key_env,
        )
        if mode == "local" and not args.skip_validation:
            ok, detail = validate_openai_compatible_endpoint(str(config["provider"]["base_url"]))
            if not ok:
                print(f"Local endpoint is not ready: {detail}", file=sys.stderr)
                print("Start the model server and retry, or use --skip-validation to save the configuration for later.", file=sys.stderr)
                return 2
            print(f"Local endpoint ready: {detail}")
        path = save_config(config, config_path)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    Path(config["data_dir"]).mkdir(parents=True, exist_ok=True)
    print(f"Wrote safe configuration: {path}")
    if mode == "demo":
        print("Demo/mock mode is ready. No gateway or model-provider API keys are required.")
    elif mode == "local":
        print("Local model mode is configured. No cloud API key is required.")
    elif mode == "cloud":
        print(f"Cloud mode selected. Set {config['provider']['key_env']} in your shell; its value was not written to disk.")
    else:
        print("Private/commercial mode recorded. Those components are not included in Hydrogenuine Community.")
    print("Next: hg doctor")
    return 0


def _doctor_lines(config: dict[str, Any]) -> tuple[list[tuple[str, str]], bool]:
    lines: list[tuple[str, str]] = []
    ok = True
    data_dir = Path(config["data_dir"])
    lines.append(("PASS", f"configuration schema: {config['schema']}"))
    lines.append(("PASS", f"mode: {config['mode']}"))
    lines.append(("PASS", f"data directory: {data_dir}"))
    provider = config.get("provider") or {}
    mode = config["mode"]
    if mode == "demo":
        lines.append(("PASS", "deterministic local provider ready; no keys or network required"))
    elif mode == "local":
        endpoint_ok, detail = validate_openai_compatible_endpoint(str(provider.get("base_url") or ""))
        lines.append(("PASS" if endpoint_ok else "WARN", detail))
        if not endpoint_ok:
            lines.append(("INFO", "The rest of Community still works in demo mode. Start the local model server when you want live inference."))
    elif mode == "cloud":
        key_env = str(provider.get("key_env") or "")
        if os.environ.get(key_env, "").strip():
            lines.append(("PASS", f"selected provider credential is present in {key_env} (value redacted)"))
        else:
            lines.append(("FAIL", f"selected cloud mode requires {key_env}; set it in your shell or run 'hg init --force --mode demo'"))
            ok = False
    else:
        lines.append(("FAIL", "private/commercial components are not included in this Community repository"))
        lines.append(("INFO", "Use demo, local, or cloud mode for the OSS core."))
        ok = False
    return lines, ok


def command_doctor(args: argparse.Namespace) -> int:
    try:
        config = load_config(_path(args.config))
    except ConfigError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        print("Fix: run 'hg init --mode demo --non-interactive' for a no-key local setup.", file=sys.stderr)
        return 1
    lines, ok = _doctor_lines(config)
    for status, detail in lines:
        print(f"{status:4} {detail}")
    if args.self_test:
        if config["mode"] != "demo":
            print("INFO self-test uses the deterministic demo provider regardless of the selected live provider")
        try:
            from hg_cli.demo import run_demo

            result = run_demo(config)
            print(f"PASS offline proof/receipt self-test: {result['receipt_count']} receipts")
        except Exception as exc:
            print(f"FAIL offline proof/receipt self-test: {exc}")
            ok = False
    print("DOCTOR PASS" if ok else "DOCTOR NEEDS ATTENTION")
    return 0 if ok else 1


def command_config_show(args: argparse.Namespace) -> int:
    try:
        config = load_config(_path(args.config))
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    _print_json(redacted_config(config))
    return 0


def command_demo(args: argparse.Namespace) -> int:
    try:
        config = load_config(_path(args.config))
    except ConfigError:
        path = _path(args.config) or default_config_path()
        config = build_config(mode="demo", config_path=path)
    from hg_cli.demo import run_demo

    result = run_demo(config)
    _print_json(result) if args.json else print(
        f"Demo complete: chat={result['chat_id']} assistant={result['assistant_preview']} receipts={result['receipt_count']}"
    )
    return 0


def _client_for(config: dict[str, Any]) -> GatewayClient:
    auth_mode = str((config.get("gateway") or {}).get("auth_mode") or "local-no-key")
    return GatewayClient(str(config.get("api_base") or "http://127.0.0.1:8000/v1"), auth_mode=auth_mode)


def _save_active_chat(config: dict[str, Any], chat_id: str, path: Path) -> None:
    config.setdefault("state", {})["active_chat_id"] = chat_id
    save_config(config, path)


def command_chat(args: argparse.Namespace) -> int:
    path = _path(args.config) or default_config_path()
    try:
        config = load_config(path)
        client = _client_for(config)
        if args.chat_command == "new":
            result = client.request("POST", "/chats", {"title": args.title})
            chat_id = str(result["chat_id"])
            _save_active_chat(config, chat_id, path)
            print(chat_id if args.json else f"Created chat {chat_id}: {result.get('chat', {}).get('title', args.title)}")
            return 0
        if args.chat_command == "list":
            chats = client.request("GET", "/chats").get("chats", [])
            if args.json:
                _print_json(chats)
            elif not chats:
                print("No chats yet. Create one with: hg chat new --title \"My chat\"")
            else:
                active = (config.get("state") or {}).get("active_chat_id")
                for chat in chats:
                    marker = "*" if chat.get("chat_id") == active else " "
                    print(f"{marker} {chat.get('chat_id')}  {chat.get('title', 'Untitled chat')}")
            return 0
        if args.chat_command == "resume":
            chat_id = args.chat_id or str((config.get("state") or {}).get("active_chat_id") or "")
            if not chat_id:
                print("No active chat. Pass a chat ID or run: hg chat new", file=sys.stderr)
                return 2
            chat = client.request("GET", f"/chats/{chat_id}").get("chat", {})
            _save_active_chat(config, chat_id, path)
            if args.message:
                result = client.request("POST", f"/chats/{chat_id}/messages", {"content": args.message})
                assistant = result.get("assistant_message") or {}
                print(str(assistant.get("content") or ""))
            else:
                messages = client.request("GET", f"/chats/{chat_id}/messages").get("messages", [])
                if args.json:
                    _print_json({"chat": chat, "messages": messages})
                else:
                    print(f"Resumed {chat_id}: {chat.get('title', 'Untitled chat')}")
                    for message in messages:
                        print(f"{message.get('role', 'message')}: {message.get('content', '')}")
            return 0
    except (ConfigError, GatewayError, KeyError) as exc:
        print(f"Chat command failed: {exc}", file=sys.stderr)
        return 1
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hg", description="Hydrogenuine Community setup, diagnostics, demo, and chat CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create a safe first-run configuration")
    init.add_argument("--mode", choices=["demo", "local", "cloud", "private"])
    init.add_argument("--provider")
    init.add_argument("--base-url")
    init.add_argument("--model")
    init.add_argument("--key-env")
    init.add_argument("--data-dir")
    init.add_argument("--config")
    init.add_argument("--non-interactive", action="store_true")
    init.add_argument("--skip-validation", action="store_true")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=command_init)

    doctor = sub.add_parser("doctor", help="validate configuration without exposing secrets")
    doctor.add_argument("--config")
    doctor.add_argument("--self-test", action="store_true")
    doctor.set_defaults(func=command_doctor)

    config = sub.add_parser("config", help="inspect public configuration")
    config_sub = config.add_subparsers(dest="config_command", required=True)
    show = config_sub.add_parser("show")
    show.add_argument("--config")
    show.add_argument("--redacted", action="store_true", help="accepted for explicitness; output is always redacted")
    show.set_defaults(func=command_config_show)

    demo = sub.add_parser("demo", help="run a deterministic no-network proof/receipt demo")
    demo.add_argument("--config")
    demo.add_argument("--json", action="store_true")
    demo.set_defaults(func=command_demo)

    chat = sub.add_parser("chat", help="create, list, and resume local chats")
    chat_sub = chat.add_subparsers(dest="chat_command", required=True)
    chat_new = chat_sub.add_parser("new")
    chat_new.add_argument("--title", default="New governed chat")
    chat_new.add_argument("--config")
    chat_new.add_argument("--json", action="store_true")
    chat_new.set_defaults(func=command_chat)
    chat_list = chat_sub.add_parser("list")
    chat_list.add_argument("--config")
    chat_list.add_argument("--json", action="store_true")
    chat_list.set_defaults(func=command_chat)
    chat_resume = chat_sub.add_parser("resume")
    chat_resume.add_argument("chat_id", nargs="?")
    chat_resume.add_argument("--message")
    chat_resume.add_argument("--config")
    chat_resume.add_argument("--json", action="store_true")
    chat_resume.set_defaults(func=command_chat)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
