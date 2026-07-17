"""
Hydrogenuine data directory and config setup.

- Resolve data dir (HG_DATA_DIR or ~/.hg).
- Ensure data dir and redis subdir exist.
- Master config: hg.json in data dir holds all secrets (gateway token, env.vars for API keys).
  Never in .env; .env is paths only (HG_DATA_DIR, HG_WORKSPACE). See docs/guides/CONFIG_AND_SECRETS.md.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def get_data_dir() -> Path:
    """Return data directory path (HG_DATA_DIR or ~/.hg)."""
    raw = os.environ.get("HG_DATA_DIR", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.home() / ".hg").resolve()


def ensure_data_dir(data_dir: Path | None = None) -> Path:
    """Create data dir and redis subdir if missing. Return path."""
    data_dir = data_dir or get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "redis").mkdir(parents=True, exist_ok=True)
    return data_dir


def hg_json_path(data_dir: Path) -> Path:
    """Path to hg.json inside data dir."""
    return data_dir / "hg.json"


def write_hg_json(
    data_dir: Path,
    *,
    env_vars: dict[str, str] | None = None,
    gateway_token: str | None = None,
    gateway_admin_key: str | None = None,
    gateway_tenant_admin_keys: list[str] | None = None,
    gateway_principal_keys: list[dict[str, str]] | None = None,
    merge: bool = True,
) -> Path:
    """
    Write or update hg.json in data_dir.
    env_vars: map of env var name -> value (e.g. OPENAI_API_KEY, HG_API_KEY).
    gateway_token: used as gateway.auth.token for operator API auth.
    gateway_admin_key: used as gateway.auth.admin_key for superadmin / admin console.
    gateway_tenant_admin_keys: list of API keys with tenant-admin role for their tenant.
    gateway_principal_keys: list of {key, tenant_id, principal_id} for principal-scoped login.
    merge: if True and file exists, merge new keys into existing; else overwrite.
    """
    path = hg_json_path(data_dir)
    data: dict[str, Any] = {}
    if merge and path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    if "gateway" not in data:
        data["gateway"] = {}
    if "auth" not in data["gateway"]:
        data["gateway"]["auth"] = {}
    if gateway_token is not None:
        data["gateway"]["auth"]["token"] = gateway_token
    if gateway_admin_key is not None:
        data["gateway"]["auth"]["admin_key"] = gateway_admin_key
    if gateway_tenant_admin_keys is not None:
        data["gateway"]["auth"]["tenant_admin_keys"] = gateway_tenant_admin_keys
    if gateway_principal_keys is not None:
        data["gateway"]["auth"]["principal_keys"] = gateway_principal_keys

    if "env" not in data:
        data["env"] = {}
    if "vars" not in data["env"]:
        data["env"]["vars"] = {}
    vars_dict = data["env"]["vars"]
    if not isinstance(vars_dict, dict):
        vars_dict = {}
        data["env"]["vars"] = vars_dict
    if env_vars:
        for k, v in env_vars.items():
            if v:
                vars_dict[k] = v

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def read_hg_json(data_dir: Path) -> dict[str, Any]:
    """Read hg.json from data dir; return empty dict if missing or invalid."""
    path = hg_json_path(data_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def ensure_operator_db_initialized(data_dir: Path) -> bool:
    """
    Create and initialize the operator console run-index DB (hg_console.db) in data_dir
    so the API has a blank database ready on first start. Idempotent.
    Returns True if DB was created or already existed, False if initialization failed.
    """
    db_path = data_dir / "hg_console.db"
    if db_path.exists():
        return True
    try:
        os.environ["HG_DB_PATH"] = str(db_path)
        # Import after setting env so config picks up HG_DB_PATH
        from operator_console.server.app.services.run_index_db import init_db
        init_db()
        return True
    except Exception:
        return False


# Only these keys are ever written to .env. All secrets stay in the master config (hg.json).
# Investor/security posture: one source of truth for secrets; .env is paths and non-secret overrides only.
SAFE_ENV_KEYS_FOR_DOTENV = frozenset({
    "HG_DATA_DIR",
    "HG_WORKSPACE",
    "HG_TIMEZONE",
})


def _env_escape(value: str) -> str:
    """Escape a value for .env: quote if needed and escape internal quotes."""
    if not value:
        return '""'
    if "\n" in value or "\r" in value or '"' in value or "#" in value or " " in value or "=" in value:
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r") + '"'
    return value


def read_env_file(path: Path) -> dict[str, str]:
    """Parse a .env file into KEY -> value. Skips empty lines and # comments."""
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        idx = line.find("=")
        if idx <= 0:
            continue
        key = line[:idx].strip()
        raw = line[idx + 1 :].strip()
        if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
            raw = raw[1:-1].replace("\\n", "\n").replace("\\r", "\r").replace('\\"', '"').replace("\\\\", "\\")
        out[key] = raw
    return out


def write_env_file(
    workspace_root: Path,
    env_vars: dict[str, str],
    *,
    merge: bool = True,
) -> Path:
    """
    Write or merge a .env file in the workspace root with path and non-secret vars only.
    Only keys in SAFE_ENV_KEYS_FOR_DOTENV are ever written. Secrets belong in the
    master config (data dir hg.json); see CONFIG_AND_SECRETS.md.
    merge: if True, read existing .env and merge (only safe keys are kept or emitted).
    """
    path = workspace_root / ".env"
    # Restrict to safe keys only — never write secrets to .env
    safe_vars = {k: str(v).strip() for k, v in env_vars.items() if k in SAFE_ENV_KEYS_FOR_DOTENV and v and str(v).strip()}
    existing: dict[str, str] = read_env_file(path) if merge and path.exists() else {}
    # Keep only safe keys from existing (strip any secrets that were ever in .env)
    existing = {k: v for k, v in existing.items() if k in SAFE_ENV_KEYS_FOR_DOTENV}
    for k, v in safe_vars.items():
        existing[k] = v
    order = ("HG_DATA_DIR", "HG_WORKSPACE", "HG_TIMEZONE")
    ordered = [(k, existing[k]) for k in order if k in existing]
    lines = [
        "# Hydrogenuine paths and non-secret overrides (generated by hg-setup).",
        "# All API keys and secrets live in the master config: <data_dir>/hg.json — never here.",
        "",
    ]
    for k, v in ordered:
        lines.append(f"{k}={_env_escape(v)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_docker_env_hint(data_dir: Path) -> Path:
    """
    Write a small hint file in the data dir: path for HG_DATA_DIR and reminder that
    secrets live only in hg.json.
    """
    path = data_dir / "DOCKER_ENV_HINT.txt"
    data_dir_resolved = data_dir.resolve()
    path.write_text(
        f"""Hydrogenuine data directory: {data_dir_resolved}

Secrets and API keys: only in this directory's hg.json (master config). Never in .env.
For Docker, set the path (e.g. in workspace .env or export):
  Linux/macOS:  export HG_DATA_DIR="{data_dir_resolved}"
  Windows:      $env:HG_DATA_DIR = "{data_dir_resolved}"
Then run: ./start.sh or .\\start.ps1
""",
        encoding="utf-8",
    )
    return path


def apply_hg_env_to_process() -> None:
    """
    Load hg.json from HG_CONFIG (or ~/.hg/hg.json) and set os.environ for any env.vars
    that are not already set. Also sets HG_GATEWAY_ADMIN_KEY from gateway.auth.admin_key
    if not in env.vars. Used at startup by API and realtime-worker so OpenVINO,
    LLM keys, etc. from hg.json are available.
    """
    cfg_path = os.environ.get("HG_CONFIG", "").strip()
    if cfg_path:
        path = Path(cfg_path)
    else:
        path = Path.home() / ".hg" / "hg.json"
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    vars_dict = (data.get("env") or {}).get("vars")
    if isinstance(vars_dict, dict):
        for k, v in vars_dict.items():
            if k and v is not None and k not in os.environ:
                os.environ[k] = str(v)
    auth = (data.get("gateway") or {}).get("auth")
    if isinstance(auth, dict):
        if "admin_key" in auth and auth["admin_key"] and "HG_GATEWAY_ADMIN_KEY" not in os.environ:
            os.environ["HG_GATEWAY_ADMIN_KEY"] = str(auth["admin_key"])
        if "tenant_admin_keys" in auth and isinstance(auth["tenant_admin_keys"], list) and "HG_GATEWAY_TENANT_ADMIN_KEYS" not in os.environ:
            os.environ["HG_GATEWAY_TENANT_ADMIN_KEYS"] = ",".join(str(k) for k in auth["tenant_admin_keys"] if k)
        if "principal_keys" in auth and isinstance(auth["principal_keys"], list) and "HG_GATEWAY_PRINCIPAL_KEYS" not in os.environ:
            parts = []
            for e in auth["principal_keys"]:
                if isinstance(e, dict) and e.get("key") and e.get("tenant_id") is not None and e.get("principal_id") is not None:
                    parts.append(f"{e['key']}:{e['tenant_id']}:{e['principal_id']}")
            if parts:
                os.environ["HG_GATEWAY_PRINCIPAL_KEYS"] = ",".join(parts)
