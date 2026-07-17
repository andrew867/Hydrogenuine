"""
Hydrogenuine setup TUI: interactive configuration and setup.

Uses only the standard library (no curses). Run from workspace root or set HG_WORKSPACE.

  python -m hg_core.setup_tui
  hg-setup
"""

from __future__ import annotations

import getpass
import os
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Box drawing and style (stdlib-only, works in Windows console)
# ---------------------------------------------------------------------------

def _tty() -> bool:
    """True if stdout looks like a TTY (for optional ANSI)."""
    try:
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    except Exception:
        return False


def _bold(s: str) -> str:
    if _tty():
        return f"\033[1m{s}\033[0m"
    return s


def _dim(s: str) -> str:
    if _tty():
        return f"\033[2m{s}\033[0m"
    return s


def _green(s: str) -> str:
    if _tty():
        return f"\033[32m{s}\033[0m"
    return s


def _yellow(s: str) -> str:
    if _tty():
        return f"\033[33m{s}\033[0m"
    return s


def _box_top(width: int = 58) -> str:
    return "  ┌" + "─" * (width - 2) + "┐"


def _box_bottom(width: int = 58) -> str:
    return "  └" + "─" * (width - 2) + "┘"


def _box_line(text: str, width: int = 58) -> str:
    pad = max(0, width - 4 - len(text))
    return "  │ " + text + " " * pad + " │"


def _section_title(title: str) -> None:
    print()
    print(_box_top())
    print(_box_line(_bold(title)))
    print(_box_bottom())
    print()


def _subsection(title: str) -> None:
    print("  ╭" + "─" * 54 + "╮")
    print("  │ " + title)
    print("  ╰" + "─" * 54 + "╯")
    print()


def _menu_line() -> None:
    print("  " + "─" * 54)


def _header(data_dir: Path | None, workspace: Path | None) -> None:
    print()
    print(_box_top())
    print(_box_line(_bold("  Hydrogenuine Setup")))
    print(_box_line(""))
    print(_box_line("  Data dir:  " + (str(data_dir) if data_dir else _dim("(not set — run Initial setup)"))))
    print(_box_line("  Workspace: " + (str(workspace) if workspace else _dim("(not set — choose 1)"))))
    print(_box_bottom())
    print()


def _prompt(prompt: str, default: str = "", secret: bool = False) -> str:
    """Read a line; if default and user hits Enter, return default. Use getpass when secret=True."""
    if secret:
        hint = " (Enter to keep current or skip)" if default else " (or Enter to skip)"
        line = getpass.getpass(f"  {prompt}{hint}: ").strip()
    else:
        if default:
            hint = f" [{default}]"
        else:
            hint = " (or Enter to skip)"
        line = input(f"  {prompt}{hint}: ").strip()
    if not line and default:
        return default
    return line


def _choice(prompt: str, options: list[str]) -> str:
    """Prompt for one of the option keys. Returns choice or empty."""
    while True:
        s = input(prompt).strip()
        if s in options:
            return s
        if s == "":
            return ""


def _test_openai_key(api_key: str) -> bool:
    """Try a minimal completion with the given OpenAI key. Return True on success."""
    try:
        from openai import OpenAI
    except ImportError:
        print(_yellow("  openai package not installed; skip test (pip install openai)"))
        return False
    try:
        client = OpenAI(api_key=api_key.strip())
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=5,
        )
        print(_green("  OpenAI key OK."))
        return True
    except Exception as e:
        print(_yellow(f"  OpenAI test failed: {e}"))
        return False


# ---------------------------------------------------------------------------
# Repo / workspace resolution
# ---------------------------------------------------------------------------

def _find_repo_root() -> Path | None:
    start = Path.cwd()
    for p in [start, *start.parents]:
        if (p / "pyproject.toml").exists() and (p / "hg_core").exists():
            return p
    return None


def _get_workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root()
    except Exception:
        return None


def _set_workspace_in_process(path: str) -> None:
    os.environ["HG_WORKSPACE"] = path


def _get_data_dir() -> Path | None:
    """Return current data dir if we've set HG_DATA_DIR or have a known path."""
    from hg_core.setup_data import get_data_dir
    return get_data_dir()


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def _action_set_workspace() -> None:
    _subsection("Set workspace path")
    path = _prompt("Workspace root path", str(Path.cwd()))
    if not path:
        path = str(Path.cwd())
    p = Path(path)
    if not p.exists():
        create = input("  Path does not exist. Create? [y/N]: ").strip().lower()
        if create == "y":
            p.mkdir(parents=True, exist_ok=True)
        else:
            print("  Skipped.")
            return
    if not p.is_dir():
        print("  Not a directory. Skipped.")
        return
    sentinel = p / ".hg_root"
    if not sentinel.exists():
        create = input("  Create .hg_root here? [Y/n]: ").strip().lower()
        if create != "n":
            try:
                sentinel.write_text("", encoding="utf-8")
                print(_green(f"  Created {sentinel}"))
            except Exception as e:
                print(f"  Failed: {e}")
    abs_path = str(p.resolve())
    _set_workspace_in_process(abs_path)
    print()
    print(_green("  Workspace set for this session."))
    print(_dim("  For persistence: set HG_WORKSPACE or keep .hg_root in that directory."))
    print()


def _action_init_dirs() -> None:
    _subsection("Initialize workspace directories")
    root = _get_workspace_root()
    if not root:
        print("  Workspace not set. Choose option 1 first.")
        return
    try:
        from hg_lib.config import ensure_workspace_initialized
        ensure_workspace_initialized(root)
        print(_green(f"  Initialized: memory, knowledge, skills/automation/tasks under {root}"))
    except Exception as e:
        print(f"  Error: {e}")
    print()


def _action_initial_setup() -> None:
    """Full wizard: data dir, workspace, API keys, write hg.json and optional credentials."""
    from hg_core.setup_data import (
        ensure_data_dir,
        ensure_operator_db_initialized,
        get_data_dir,
        write_docker_env_hint,
        write_env_file,
        write_hg_json,
        read_hg_json,
    )

    _section_title("Initial setup — data directory & API keys")

    # 1) Data directory
    default_data = str(get_data_dir())
    data_path = _prompt("Data directory (where hg.json and Redis data live)", default_data)
    if not data_path:
        data_path = default_data
    data_dir = Path(data_path).expanduser().resolve()
    ensure_data_dir(data_dir)
    os.environ["HG_DATA_DIR"] = str(data_dir)
    print(_green(f"  Using data dir: {data_dir}"))
    print()

    # 2) Workspace (for tasks and runs)
    repo = _find_repo_root()
    ws_default = str(repo) if repo else str(Path.cwd())
    ws_path = _prompt("Workspace root (for tasks and credentials)", ws_default)
    if not ws_path:
        ws_path = ws_default
    workspace = Path(ws_path).expanduser().resolve()
    if not workspace.exists():
        workspace.mkdir(parents=True, exist_ok=True)
    if not (workspace / ".hg_root").exists():
        (workspace / ".hg_root").write_text("", encoding="utf-8")
    _set_workspace_in_process(str(workspace))
    try:
        from hg_lib.config import ensure_workspace_initialized
        ensure_workspace_initialized(workspace)
    except Exception as e:
        print(_yellow(f"  Workspace init warning: {e}"))
    print(_green(f"  Workspace: {workspace}"))
    print()

    _subsection("API keys (stored in data dir hg.json)")
    print(_dim("  Leave blank to skip. You can edit ~/.hg/hg.json or set env vars later."))
    print()

    existing = read_hg_json(data_dir)
    env_vars = (existing.get("env") or {}).get("vars") or {}
    if not isinstance(env_vars, dict):
        env_vars = {}

    openai = _prompt("OPENAI_API_KEY", env_vars.get("OPENAI_API_KEY", ""), secret=True)
    if openai:
        env_vars["OPENAI_API_KEY"] = openai
    anthropic = _prompt("ANTHROPIC_API_KEY (Claude)", env_vars.get("ANTHROPIC_API_KEY", ""), secret=True)
    if anthropic:
        env_vars["ANTHROPIC_API_KEY"] = anthropic
    google_key = _prompt("GOOGLE_API_KEY (Gemini)", env_vars.get("GOOGLE_API_KEY", ""), secret=True)
    if google_key:
        env_vars["GOOGLE_API_KEY"] = google_key
    xai_key = _prompt("XAI_API_KEY (Grok)", env_vars.get("XAI_API_KEY", ""), secret=True)
    if xai_key:
        env_vars["XAI_API_KEY"] = xai_key
    hf_token = _prompt("HUGGINGFACE_HUB_TOKEN (for offline model downloads)", env_vars.get("HUGGINGFACE_HUB_TOKEN", ""), secret=True)
    if hf_token:
        env_vars["HUGGINGFACE_HUB_TOKEN"] = hf_token
    openvino_path = _prompt("HG_OPENVINO_MODEL_PATH (optional; path to OpenVINO model dir for Intel iGPU/CPU)", env_vars.get("HG_OPENVINO_MODEL_PATH", ""))
    if openvino_path:
        env_vars["HG_OPENVINO_MODEL_PATH"] = openvino_path
    openvino_device = _prompt("HG_OPENVINO_DEVICE (optional; GPU|CPU|AUTO)", env_vars.get("HG_OPENVINO_DEVICE", "AUTO"))
    if openvino_device:
        env_vars["HG_OPENVINO_DEVICE"] = openvino_device.strip().upper() or "AUTO"

    auth = (existing.get("gateway") or {}).get("auth") or {}
    current_token = auth.get("token", "") if isinstance(auth, dict) else ""
    hg_api = _prompt("HG_API_KEY (operator console / API auth)", env_vars.get("HG_API_KEY", "") or current_token, secret=True)
    if hg_api:
        env_vars["HG_API_KEY"] = hg_api
        env_vars["HG_GATEWAY_API_KEY"] = hg_api
        gateway_token: str | None = hg_api
        if not env_vars.get("HG_GATEWAY_TENANT_BY_KEY", "").strip():
            env_vars["HG_GATEWAY_TENANT_BY_KEY"] = f"{hg_api}:default"
    else:
        gateway_token = current_token or None

    admin_key = _prompt("HG_GATEWAY_ADMIN_KEY (superadmin / admin console; for tenant quotas, export, delete)", env_vars.get("HG_GATEWAY_ADMIN_KEY", ""), secret=True)
    if admin_key:
        env_vars["HG_GATEWAY_ADMIN_KEY"] = admin_key

    openai_key_to_test = env_vars.get("OPENAI_API_KEY", "").strip()
    if openai_key_to_test:
        test_choice = input("  Test OpenAI key now? [y/N]: ").strip().lower()
        if test_choice == "y":
            _test_openai_key(openai_key_to_test)
    print()

    _subsection("Optional platform API keys (stored in hg.json)")
    fourclaw = _prompt(
        "FOURCLAW_API_KEY (or 4CLAW_API_KEY)",
        env_vars.get("FOURCLAW_API_KEY", "") or env_vars.get("4CLAW_API_KEY", ""),
        secret=True,
    )
    if fourclaw:
        env_vars["FOURCLAW_API_KEY"] = fourclaw
        env_vars["4CLAW_API_KEY"] = fourclaw
    moltbook = _prompt(
        "MOLTBOOK_API_KEY",
        env_vars.get("MOLTBOOK_API_KEY", ""),
        secret=True,
    )
    if moltbook:
        env_vars["MOLTBOOK_API_KEY"] = moltbook
    if fourclaw or moltbook:
        print(_green("  Platform API keys will be written to hg.json"))
    else:
        print(_dim("  Skipped. Add later to hg.json or env vars if needed."))
    print()

    write_hg_json(
        data_dir,
        env_vars=env_vars,
        gateway_token=gateway_token,
        gateway_admin_key=admin_key if admin_key else None,
        merge=True,
    )
    print(_green(f"  Wrote {data_dir / 'hg.json'} (master config — all secrets live here only)"))
    safe_env = {"HG_DATA_DIR": str(data_dir), "HG_WORKSPACE": str(workspace)}
    if env_vars.get("HG_TIMEZONE"):
        safe_env["HG_TIMEZONE"] = env_vars["HG_TIMEZONE"]
    env_path = write_env_file(workspace, safe_env, merge=True)
    print(_green(f"  Wrote {env_path} (paths only; no secrets in .env)"))
    if ensure_operator_db_initialized(data_dir):
        print(_green(f"  Blank run-index DB ready: {data_dir / 'hg_console.db'}"))
    else:
        print(_dim("  Run-index DB will be created on first API start."))
    hint_path = write_docker_env_hint(data_dir)
    print(_green(f"  Wrote {hint_path.name}"))
    print()

    _section_title("Setup complete")
    print(_box_line("Next steps:"))
    print(_box_line(""))
    print(_box_line("  1. Start the stack (start scripts load .env automatically):"))
    print(_box_line("       Linux/macOS:  ./start.sh"))
    print(_box_line("       Windows:      .\\start.ps1"))
    print(_box_line("       Or:           docker compose up -d"))
    print(_box_line(""))
    print(_box_line("  2. Open in browser:"))
    print(_box_line("       API:          http://localhost:8080"))
    print(_box_line("       Gateway:      http://localhost:8000  (chat / v1)"))
    print(_box_line("       Operator UI:  http://localhost:5173"))
    print(_box_line("       Product UI:   http://localhost:3000"))
    print(_box_line("       Client UI:    http://localhost:3001  (chat)"))
    print(_box_line(""))
    print(_box_line("  3. Secrets: only in hg.json. .env = paths only. See docs/guides/CONFIG_AND_SECRETS.md"))
    print(_box_bottom())
    print()


def _action_verify() -> None:
    _subsection("Verify install")
    root = _get_workspace_root()
    if not root:
        print("  Workspace not set. Choose option 1 first.")
        return
    _set_workspace_in_process(str(root))
    ok = True
    try:
        from hg_core.job_registry import list_tasks
        tasks = list_tasks()
        print(f"  Registered tasks: {len(tasks)} — e.g. {tasks[:5]}")
    except Exception as e:
        print(f"  list_tasks failed: {e}")
        ok = False
    dag_path = root / "memory" / "automation" / "dags" / "linear_three_steps.json"
    if dag_path.exists():
        try:
            result = subprocess.run(
                [sys.executable, "-m", "hg_core.run_dag", str(dag_path)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(root),
                env=os.environ.copy(),
            )
            if result.returncode == 0 and "ok" in result.stdout and "true" in result.stdout:
                print(_green("  DAG run (linear_three_steps): OK"))
            else:
                print(_yellow("  DAG run returned non-zero or no ok:true"))
                ok = False
        except subprocess.TimeoutExpired:
            print(_yellow("  DAG run timed out."))
            ok = False
        except Exception as e:
            print(f"  DAG run error: {e}")
            ok = False
    else:
        print(_dim("  (Demo DAG not found — skip)"))
    if ok:
        print(_green("  Verification passed."))
    print()


def _action_dashboard() -> None:
    _subsection("Generate QA dashboard")
    root = _get_workspace_root()
    if not root:
        print("  Workspace not set. Choose option 1 first.")
        return
    _set_workspace_in_process(str(root))
    out = root / "docs" / "qa" / "dashboard.html"
    try:
        from hg_core.qa_dashboard import _build_html
        _build_html(root, out)
        print(_green(f"  Dashboard written to: {out}"))
        print("  Open it in a browser.")
    except Exception as e:
        print(f"  Error: {e}")
    print()


def _action_download_offline_models() -> None:
    """Download model(s) for offline LLMs from Hugging Face; ask and store HF token if needed."""
    from hg_core.setup_data import read_hg_json, write_hg_json

    _subsection("Download offline LLM models (Hugging Face)")
    data_dir = _get_data_dir()
    if not data_dir or not data_dir.exists():
        print("  Data directory not set or missing. Run option 4 (Initial setup) first.")
        print()
        return
    workspace = _get_workspace_root() or Path.cwd()
    existing = read_hg_json(data_dir)
    env_vars = (existing.get("env") or {}).get("vars") or {}
    if not isinstance(env_vars, dict):
        env_vars = {}
    hf_token = env_vars.get("HUGGINGFACE_HUB_TOKEN") or env_vars.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN") or os.environ.get("HF_TOKEN") or ""
    if not hf_token:
        hf_token = _prompt("Hugging Face API token (read or write; get one at https://huggingface.co/settings/tokens)", "", secret=True)
        if not hf_token:
            print(_dim("  Skipped. Set HUGGINGFACE_HUB_TOKEN in hg.json or env to download gated models."))
            print()
            return
        env_vars["HUGGINGFACE_HUB_TOKEN"] = hf_token
        write_hg_json(data_dir, env_vars=env_vars, merge=True)
        print(_green("  Stored HUGGINGFACE_HUB_TOKEN in hg.json."))
    else:
        print(_dim("  Using existing HUGGINGFACE_HUB_TOKEN from hg.json / env."))
    repo_id = _prompt("Hugging Face repo (e.g. Qwen/Qwen2.5-7B-Instruct-GPTQ-Int8)", "")
    if not repo_id:
        print("  No repo entered. Skipped.")
        print()
        return
    default_out = workspace / "models" / repo_id.replace("/", "_")
    out_prompt = _prompt("Local directory to save model", str(default_out))
    out_dir = Path(out_prompt).expanduser().resolve() if out_prompt else default_out
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print(_yellow("  Install huggingface_hub first: pip install huggingface_hub"))
        print("  Then re-run this option.")
        print()
        return
    print(f"  Downloading {repo_id} -> {out_dir} ...")
    out_dir.mkdir(parents=True, exist_ok=True)
    token = env_vars.get("HUGGINGFACE_HUB_TOKEN") or env_vars.get("HF_TOKEN") or hf_token
    try:
        snapshot_download(
            repo_id=repo_id.strip(),
            local_dir=str(out_dir),
            local_dir_use_symlinks=False,
            token=token or None,
        )
        print(_green(f"  Done. Model saved to {out_dir}"))
        print(_dim("  For vLLM: python scripts/hg_vllm_setup.py serve --model " + str(out_dir) + " --port 8001"))
        print(_dim("  For OpenVINO: convert to OpenVINO format then set HG_OPENVINO_MODEL_PATH (see docs/runbooks/OPENVINO_SETUP.md)."))
        use_openvino = input("  Save this path as HG_OPENVINO_MODEL_PATH in hg.json? (use after converting to OpenVINO) [y/N]: ").strip().lower()
        if use_openvino == "y":
            env_vars["HG_OPENVINO_MODEL_PATH"] = str(out_dir)
            write_hg_json(data_dir, env_vars=env_vars, merge=True)
            print(_green("  Saved. API/realtime-worker will use it when HG_LLM_BACKEND=openvino."))
    except Exception as e:
        print(f"  Download failed: {e}")
    print()


def _action_open_doc() -> None:
    _subsection("Open operations guide")
    root = _get_workspace_root() or Path.cwd()
    doc = root / "docs" / "guides" / "OPERATIONS_END_TO_END.md"
    if not doc.exists():
        doc = Path(__file__).resolve().parent.parent / "docs" / "guides" / "OPERATIONS_END_TO_END.md"
    if doc.exists():
        print(f"  Operations guide: {doc}")
        if sys.platform == "win32":
            try:
                os.startfile(str(doc))
            except Exception:
                pass
        elif sys.platform == "darwin":
            try:
                subprocess.run(["open", str(doc)], check=False)
            except Exception:
                pass
        else:
            try:
                subprocess.run(["xdg-open", str(doc)], check=False)
            except Exception:
                pass
    else:
        print("  OPERATIONS_END_TO_END.md not found.")
    print()


def main() -> None:
    repo = _find_repo_root()
    if repo is not None and not _get_workspace_root():
        if (repo / ".hg_root").exists():
            _set_workspace_in_process(str(repo))
        elif os.environ.get("HG_WORKSPACE"):
            pass
        else:
            _set_workspace_in_process(str(repo))
            print(_dim("  (Using repo root as workspace for this session.)"))
            print()

    while True:
        data_dir = _get_data_dir()
        workspace = _get_workspace_root()
        _header(data_dir, workspace)

        print("  1) Set workspace path")
        print("  2) Initialize workspace directories")
        print("  3) Verify install (list tasks, run demo DAG)")
        print(_bold("  4) Initial setup — data dir, API keys, multillm (recommended first)"))
        print("  5) Generate QA dashboard")
        print("  6) Open operations guide")
        print("  7) Download offline LLM models (Hugging Face)")
        print("  8) Exit")
        _menu_line()
        choice = _choice("  Choice [1-8]: ", ["1", "2", "3", "4", "5", "6", "7", "8"])
        if choice == "":
            choice = "8"
        if choice == "1":
            _action_set_workspace()
        elif choice == "2":
            _action_init_dirs()
        elif choice == "3":
            _action_verify()
        elif choice == "4":
            _action_initial_setup()
        elif choice == "5":
            _action_dashboard()
        elif choice == "6":
            _action_open_doc()
        elif choice == "7":
            _action_download_offline_models()
        elif choice == "8":
            print("  Bye.")
            break


if __name__ == "__main__":
    main()
