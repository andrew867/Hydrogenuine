"""
Unified Telegram config and send for lifecycle, overseer, and CLI.

Single source of truth for bot_token and chat_id resolution order:
env -> hg.json env.vars -> config (overseer/platform) -> jobs backup.
Default chat_id 241533146 when unset.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


def _get_workspace_root() -> Optional[Path]:
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root()
    except Exception:
        return None


def _load_hg_config(workspace_root: Optional[Path]) -> dict:
    try:
        from hg_lib.config_loader import get_config
        root = workspace_root or _get_workspace_root()
        return get_config(workspace_root=root, reload=False) if root else {}
    except Exception:
        return {"overseer": {}, "platform": {}, "memory": {}}


def _load_hg_json(workspace_root: Optional[Path]) -> dict:
    candidates: list[Path] = []
    if workspace_root:
        candidates.append(workspace_root / "hg.json")
        candidates.append(workspace_root.parent / "hg.json")
    try:
        candidates.append(Path.home() / ".hg" / "hg.json")
    except Exception:
        pass
    for path in candidates:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
    return {}


def _load_hg_env_vars(workspace_root: Optional[Path]) -> Dict[str, str]:
    data = _load_hg_json(workspace_root)
    env_block = data.get("env") if isinstance(data, dict) else {}
    vars_block = env_block.get("vars") if isinstance(env_block, dict) else None
    if isinstance(vars_block, dict):
        return {str(k): str(v) for k, v in vars_block.items() if v}
    return {}


def _get_hg_json_telegram(workspace_root: Optional[Path], keys: list[str]) -> Optional[str]:
    data = _load_hg_json(workspace_root)
    channels = data.get("channels") if isinstance(data, dict) else None
    telegram = channels.get("telegram") if isinstance(channels, dict) else None
    if isinstance(telegram, dict):
        for key in keys:
            if key in telegram and telegram[key]:
                return str(telegram[key])
    return None


def _get_config_telegram_value(config: dict, keys: list[str]) -> Optional[str]:
    for section in ("overseer", "platform"):
        section_data = (config or {}).get(section) or {}
        if isinstance(section_data, dict):
            for key in keys:
                if key in section_data and section_data[key]:
                    return str(section_data[key])
            telegram_block = section_data.get("telegram")
            if isinstance(telegram_block, dict):
                for key in keys:
                    if key in telegram_block and telegram_block[key]:
                        return str(telegram_block[key])
    return None


def _load_chat_id_from_jobs_backup() -> Optional[str]:
    cron_dir = Path.home() / ".hg" / "cron"
    if not cron_dir.exists():
        return None
    candidates = list(cron_dir.glob("jobs.json.backup*")) + list(cron_dir.glob("jobs - Copy*.json"))
    candidates.extend(cron_dir.glob("jobs.json.bak"))
    candidates.extend(cron_dir.glob("jobs.json.pre-fix-backup"))
    candidates.append(cron_dir / "jobs.json")
    for path in candidates:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        jobs = data.get("jobs", []) if isinstance(data, dict) else []
        for job in jobs:
            delivery = (job or {}).get("delivery")
            if isinstance(delivery, dict) and delivery.get("channel") == "telegram":
                target = delivery.get("to")
                if target:
                    return str(target)
    return None


def get_telegram_config(workspace_root: Optional[Path] = None) -> Dict[str, Optional[str]]:
    """
    Resolve Telegram chat_id and bot_token.
    Order: env -> hg.json env.vars -> config -> jobs backup.
    chat_id defaults to 241533146 if never set.
    """
    root = workspace_root or _get_workspace_root()
    config = _load_hg_config(root)
    hg_env = _load_hg_env_vars(root)

    chat_id = (
        os.getenv("TELEGRAM_CHAT_ID")
        or os.getenv("ANDREW_TELEGRAM_USER_ID")
        or (hg_env.get("TELEGRAM_CHAT_ID") if hg_env else None)
        or (hg_env.get("ANDREW_TELEGRAM_USER_ID") if hg_env else None)
        or _get_config_telegram_value(config, ["telegram_chat_id", "telegram_user_id", "telegram_to", "chat_id", "user_id", "to"])
        or _load_chat_id_from_jobs_backup()
        or "241533146"
    )

    bot_token = (
        os.getenv("TELEGRAM_BOT_TOKEN")
        or (hg_env.get("TELEGRAM_BOT_TOKEN") if hg_env else None)
        or _get_config_telegram_value(config, ["telegram_bot_token", "telegram_token", "bot_token", "token"])
        or _get_hg_json_telegram(root, ["botToken", "bot_token", "token"])
    )

    return {"chat_id": chat_id, "bot_token": bot_token}


def is_telegram_configured(workspace_root: Optional[Path] = None) -> bool:
    """True if bot_token is set (chat_id can default)."""
    cfg = get_telegram_config(workspace_root)
    return bool(cfg.get("bot_token"))


def send_telegram(
    text: str,
    chat_id: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Send one Telegram message. Uses get_telegram_config for token and default chat_id.

    Args:
        text: Message body (Markdown allowed).
        chat_id: Override destination; if None, use config default.
        workspace_root: Optional workspace for config resolution.

    Returns:
        {"ok": True} or {"ok": False, "error": "..."}. May include message_id, chat_id.
    """
    if not text or not str(text).strip():
        return {"ok": False, "error": "Message cannot be empty"}
    cfg = get_telegram_config(workspace_root)
    token = cfg.get("bot_token")
    if not token:
        return {"ok": False, "error": "Telegram bot token not found. Set TELEGRAM_BOT_TOKEN or add it to hg.json"}
    dest = chat_id or cfg.get("chat_id") or "241533146"

    import requests
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": dest, "text": text.strip(), "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        if result.get("ok"):
            return {
                "ok": True,
                "chat_id": dest,
                "message_id": result.get("result", {}).get("message_id"),
            }
        return {
            "ok": False,
            "error": result.get("description", "Unknown Telegram API error"),
            "chat_id": dest,
        }
    except requests.exceptions.HTTPError as e:
        try:
            err = e.response.json()
            desc = err.get("description", str(e))
        except Exception:
            desc = str(e)
        return {"ok": False, "error": f"HTTP {e.response.status_code}: {desc}", "chat_id": dest}
    except requests.exceptions.RequestException as e:
        return {"ok": False, "error": f"Request failed: {str(e)}", "chat_id": dest}
    except Exception as e:
        return {"ok": False, "error": str(e), "chat_id": dest}
