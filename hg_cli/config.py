"""Safe, public configuration for the Hydrogenuine Community CLI.

The file written by this module contains configuration and environment-variable
references only. Secret values are never persisted here.
"""

from __future__ import annotations

import json
import os
import stat
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


SCHEMA = "hydrogenuine-community-config-v1"
MODES = {"demo", "local", "cloud", "private"}
LOCAL_PROVIDERS = {"lm-studio", "openai-compatible", "ollama", "vllm"}
CLOUD_KEY_ENVS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "xai": "XAI_API_KEY",
}
SECRET_MARKERS = ("api_key", "apikey", "secret", "password", "token")


class ConfigError(ValueError):
    """Raised when a public configuration is incomplete or unsafe."""


def default_config_path() -> Path:
    explicit = os.environ.get("HG_CONFIG_PATH", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    community_dir = os.environ.get("HG_COMMUNITY_DATA_DIR", "").strip()
    if community_dir:
        return (Path(community_dir).expanduser().resolve() / "config.json")
    source_local = Path.cwd() / ".hg_community" / "config.json"
    if source_local.exists():
        return source_local.resolve()
    return (Path.home() / ".hydrogenuine" / "config.json").resolve()


def default_data_dir(config_path: Path) -> Path:
    if config_path.parent.name == ".hg_community":
        return config_path.parent
    return config_path.parent / "data"


def load_config(path: Path | None = None) -> dict[str, Any]:
    resolved = (path or default_config_path()).expanduser().resolve()
    if not resolved.exists():
        raise ConfigError(f"Configuration not found at {resolved}. Run: hg init")
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Configuration at {resolved} is not readable JSON: {exc}") from exc
    validate_config(data)
    return data


def validate_config(data: dict[str, Any]) -> None:
    if data.get("schema") != SCHEMA:
        raise ConfigError(f"Unsupported configuration schema: {data.get('schema')!r}")
    mode = data.get("mode")
    if mode not in MODES:
        raise ConfigError(f"Unsupported mode: {mode!r}")
    provider = data.get("provider") or {}
    if mode == "local":
        if provider.get("id") not in LOCAL_PROVIDERS:
            raise ConfigError("Local mode requires lm-studio, openai-compatible, ollama, or vllm.")
        if not str(provider.get("base_url") or "").strip():
            raise ConfigError("Local mode requires an OpenAI-compatible base URL.")
        if not str(provider.get("model") or "").strip():
            raise ConfigError("Local mode requires a model name.")
    if mode == "cloud":
        if provider.get("id") not in CLOUD_KEY_ENVS:
            raise ConfigError("Cloud mode requires openai, anthropic, google, or xai.")
        if not str(provider.get("key_env") or "").strip():
            raise ConfigError("Cloud mode requires a key environment-variable name.")


def build_config(
    *,
    mode: str,
    config_path: Path,
    data_dir: Path | None = None,
    provider: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    key_env: str | None = None,
) -> dict[str, Any]:
    mode = mode.strip().lower()
    if mode not in MODES:
        raise ConfigError(f"Mode must be one of: {', '.join(sorted(MODES))}")
    resolved_data = (data_dir or default_data_dir(config_path)).expanduser().resolve()
    provider_id = (provider or ("stub" if mode == "demo" else "lm-studio" if mode == "local" else "openai" if mode == "cloud" else "private-stack")).strip().lower()
    if mode == "local":
        resolved_base = (base_url or ("http://127.0.0.1:1234/v1" if provider_id == "lm-studio" else "http://127.0.0.1:11434/v1")).rstrip("/")
        resolved_model = (model or "local-model").strip()
        runtime_provider = "vllm"
        resolved_key_env = None
    elif mode == "cloud":
        resolved_base = (base_url or "").rstrip("/") or None
        resolved_model = (model or "").strip() or None
        runtime_provider = provider_id
        resolved_key_env = (key_env or CLOUD_KEY_ENVS.get(provider_id) or "").strip() or None
    elif mode == "demo":
        resolved_base = None
        resolved_model = "local-deterministic"
        runtime_provider = "stub"
        resolved_key_env = None
    else:
        resolved_base = None
        resolved_model = None
        runtime_provider = None
        resolved_key_env = None
    config = {
        "schema": SCHEMA,
        "edition": "community",
        "mode": mode,
        "data_dir": str(resolved_data),
        "api_base": "http://127.0.0.1:8000/v1",
        "gateway": {"auth_mode": "api-key" if mode == "private" else "local-no-key"},
        "provider": {
            "id": provider_id,
            "runtime_provider": runtime_provider,
            "base_url": resolved_base,
            "model": resolved_model,
            "key_env": resolved_key_env,
        },
        "state": {"active_chat_id": None},
    }
    validate_config(config)
    return config


def save_config(config: dict[str, Any], path: Path | None = None) -> Path:
    validate_config(config)
    resolved = (path or default_config_path()).expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    tmp = resolved.with_suffix(resolved.suffix + ".tmp")
    tmp.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(resolved)
    try:
        resolved.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return resolved


def validate_openai_compatible_endpoint(base_url: str, timeout: float = 2.0) -> tuple[bool, str]:
    url = base_url.rstrip("/") + "/models"
    request = urllib.request.Request(url, headers={"accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = int(getattr(response, "status", 200))
            if 200 <= status < 400:
                return True, f"endpoint responded at {url}"
            return False, f"endpoint returned HTTP {status} at {url}"
    except urllib.error.HTTPError as exc:
        return False, f"endpoint returned HTTP {exc.code} at {url}"
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return False, f"endpoint unavailable at {url}: {getattr(exc, 'reason', exc)}"


def apply_config_to_environment(path: Path | None = None) -> dict[str, Any] | None:
    try:
        config = load_config(path)
    except ConfigError:
        return None
    provider = config.get("provider") or {}
    os.environ["HG_COMMUNITY_DATA_DIR"] = str(config["data_dir"])
    os.environ["HG_GATEWAY_DB_PATH"] = str(Path(config["data_dir"]) / "gateway.sqlite3")
    os.environ["HG_GATEWAY_STORE"] = "sqlite"
    os.environ["HG_GATEWAY_AUTH_MODE"] = str((config.get("gateway") or {}).get("auth_mode") or "local-no-key")
    mode = config.get("mode")
    if mode == "demo":
        os.environ["SAFE_LOCAL_ONLY"] = "1"
        os.environ["HG_DEFAULT_PROVIDER"] = "stub"
    elif mode == "local":
        os.environ["SAFE_LOCAL_ONLY"] = "0"
        os.environ["HG_DEFAULT_PROVIDER"] = "vllm"
        os.environ["HG_VLLM_BASE_URL"] = str(provider.get("base_url") or "")
        os.environ["HG_VLLM_MODEL"] = str(provider.get("model") or "local-model")
        if provider.get("id") == "lm-studio":
            os.environ["LM_STUDIO_BASE_URL"] = str(provider.get("base_url") or "")
    elif mode == "cloud":
        runtime_provider = str(provider.get("runtime_provider") or provider.get("id") or "")
        if runtime_provider:
            os.environ["HG_DEFAULT_PROVIDER"] = runtime_provider
        model = str(provider.get("model") or "")
        if model:
            os.environ[f"HG_{runtime_provider.upper()}_MODEL"] = model
        base_url = str(provider.get("base_url") or "")
        if base_url:
            os.environ[f"{runtime_provider.upper()}_BASE_URL"] = base_url
    return config


def redacted_config(config: dict[str, Any]) -> dict[str, Any]:
    def redact(value: Any, key: str = "") -> Any:
        lower = key.lower()
        if any(marker in lower for marker in SECRET_MARKERS) and not lower.endswith("_env"):
            return "[redacted]" if value else value
        if isinstance(value, dict):
            return {k: redact(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [redact(v, key) for v in value]
        return value

    return redact(config)
