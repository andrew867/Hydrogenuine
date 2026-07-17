from pydantic import BaseModel
import os
import json
from pathlib import Path
from typing import Dict, Optional


DEFAULT_API_KEY = "changeme"
STRICT_ENV_BYPASS = {"demo", "dev", "development", "test", "testing"}
SAFE_LOCAL_ONLY_ENV = "SAFE_LOCAL_ONLY"


def _load_gateway_token() -> Optional[str]:
    """Load gateway auth token from hg.json when available."""
    cfg_path = os.getenv("HG_CONFIG")
    if cfg_path:
        path = Path(cfg_path)
    else:
        path = Path.home() / ".hg" / "hg.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return (data.get("gateway") or {}).get("auth", {}).get("token")
    except (json.JSONDecodeError, OSError):
        return None


def _resolve_api_key_with_source() -> tuple[str, str]:
    """Resolve API key: HG_API_KEY, else HG_GATEWAY_API_KEY (same as gateway), else hg.json gateway token, else default."""
    env_key = os.getenv("HG_API_KEY")
    if env_key:
        return env_key.strip(), "env"
    gw_env = os.getenv("HG_GATEWAY_API_KEY")
    if gw_env:
        return gw_env.strip(), "gateway_env"
    gw = _load_gateway_token()
    if gw:
        return gw, "gateway"
    return DEFAULT_API_KEY, "default"


def _resolve_api_key() -> str:
    """Resolve API key from env, then gateway token, else default."""
    return _resolve_api_key_with_source()[0]


def _runtime_env_label() -> str:
    return (os.getenv("HG_ENV", "Demo") or "Demo").strip()


def _safe_local_only() -> bool:
    return (os.getenv(SAFE_LOCAL_ONLY_ENV, "") or "").strip().lower() in {"1", "true", "yes", "on"}


def _strict_auth_required() -> bool:
    return _runtime_env_label().lower() not in STRICT_ENV_BYPASS


def validate_operator_runtime_config() -> None:
    key, source = _resolve_api_key_with_source()
    if _strict_auth_required() and (not key or key == DEFAULT_API_KEY):
        raise RuntimeError(
            "Operator API refuses to start in non-demo mode with a default or missing API key. "
            "Set HG_API_KEY or HG_GATEWAY_API_KEY to a non-default value."
        )


def _load_product_api_keys() -> Dict[str, str]:
    """Ch4 product API: map API key -> role (viewer | operator | admin)."""
    keys = os.getenv("HG_PRODUCT_API_KEYS")
    if keys:
        try:
            return json.loads(keys)
        except json.JSONDecodeError:
            pass
    m: Dict[str, str] = {}
    v = os.getenv("HG_PRODUCT_API_KEY_VIEWER")
    if v:
        m[v] = "viewer"
    o = os.getenv("HG_PRODUCT_API_KEY_OPERATOR")
    if o:
        m[o] = "operator"
    a = os.getenv("HG_PRODUCT_API_KEY_ADMIN")
    if a:
        m[a] = "admin"
    gateway_admin = os.getenv("HG_GATEWAY_ADMIN_KEY")
    if gateway_admin:
        m[gateway_admin] = "admin"
    gateway_operator = os.getenv("HG_GATEWAY_API_KEY") or os.getenv("HG_API_KEY")
    if gateway_operator:
        m.setdefault(gateway_operator, "operator")
    if m:
        return m
    api_key = _resolve_api_key()
    if api_key:
        return {api_key: "operator"}
    return {}

class Settings(BaseModel):
    api_key: str = _resolve_api_key()
    runs_root: str = os.getenv("HG_RUNS_ROOT", "./.hg_runs")
    sqlite_path: str = os.getenv("HG_DB_PATH", "./hg_console.db")
    cors_origins: str = os.getenv(
        "HG_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:8080,http://127.0.0.1:8080",
    )

    @property
    def product_api_keys(self) -> Dict[str, str]:
        return _load_product_api_keys()

    @property
    def api_key_source(self) -> str:
        """Where api_key was resolved from (env|gateway|default)."""
        return _resolve_api_key_with_source()[1]

    @property
    def runtime_env(self) -> str:
        return _runtime_env_label()

    @property
    def safe_local_only(self) -> bool:
        return _safe_local_only()

    @property
    def runtime_mode(self) -> str:
        return "safe-local" if self.safe_local_only else "normal"

    @property
    def strict_auth_required(self) -> bool:
        return _strict_auth_required()

settings = Settings()
