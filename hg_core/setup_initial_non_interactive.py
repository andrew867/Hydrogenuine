"""
Non-interactive initial setup for Docker/first-run: create hg.json from env when missing.
Reads: HG_DATA_DIR, HG_WORKSPACE, HG_SETUP_OPERATOR_KEY, HG_SETUP_ADMIN_KEY.
Writes: data_dir/hg.json (operator key, admin key, tenant_by_key, env vars for gateway).
No prompts. Safe to run when hg.json already exists (no-op or merge based on caller).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def run(data_dir: Path, workspace: Path, operator_key: str, admin_key: str) -> bool:
    """
    Write hg.json with operator key, admin key, and tenant mapping.
    Returns True if config was written, False if skipped (e.g. no keys).
    """
    from hg_core.setup_data import ensure_data_dir, write_hg_json

    ensure_data_dir(data_dir)
    env_vars: dict[str, str] = {}
    gateway_token: str | None = None
    gateway_admin_key: str | None = None

    if operator_key and operator_key.strip():
        operator_key = operator_key.strip()
        env_vars["HG_API_KEY"] = operator_key
        env_vars["HG_GATEWAY_API_KEY"] = operator_key
        env_vars["HG_GATEWAY_TENANT_BY_KEY"] = f"{operator_key}:default"
        gateway_token = operator_key
    if admin_key and admin_key.strip():
        gateway_admin_key = admin_key.strip()
        env_vars["HG_GATEWAY_ADMIN_KEY"] = gateway_admin_key

    if not gateway_token and not gateway_admin_key:
        return False

    write_hg_json(
        data_dir,
        env_vars=env_vars,
        gateway_token=gateway_token,
        gateway_admin_key=gateway_admin_key,
        merge=True,
    )
    return True


def main() -> int:
    data_dir_raw = os.environ.get("HG_DATA_DIR", "").strip()
    workspace_raw = os.environ.get("HG_WORKSPACE", "").strip() or os.environ.get("PWD", "")
    operator_key = os.environ.get("HG_SETUP_OPERATOR_KEY", "").strip()
    admin_key = os.environ.get("HG_SETUP_ADMIN_KEY", "").strip()

    if not data_dir_raw:
        data_dir = Path.home() / ".hg"
    else:
        data_dir = Path(data_dir_raw).expanduser().resolve()
    workspace = Path(workspace_raw).expanduser().resolve()

    hg_json = data_dir / "hg.json"
    if hg_json.exists():
        return 0

    if run(data_dir, workspace, operator_key, admin_key):
        print("hg.json created (non-interactive setup)", file=sys.stderr)
    else:
        print("No HG_SETUP_OPERATOR_KEY or HG_SETUP_ADMIN_KEY set; run hg-setup to configure.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
