"""
Hydrogenuine workspace config. Hardened workspace resolution.
Policy: HG_WORKSPACE env -> ~/.hg/workspace -> cwd with .hg_root sentinel -> else raise.
"""

from pathlib import Path
import os
import re

from hg_lib.errors import HydrogenuineError

SENTINEL_FILE = ".hg_root"
HG_CREATE_DEFAULT_WORKSPACE = "HG_CREATE_DEFAULT_WORKSPACE"
TASK_FILE_ALIASES = {
    "fourclaw-auto-post-cadence": "fourclaw-auto-post",
}
TASK_FILE_PREFIX_ALIASES = (
    "newfoundland-bayman-",
)


def get_workspace_root() -> Path:
    """
    Get workspace root. No silent fallback to raw cwd.
    Priority:
    1. HG_WORKSPACE env var (use it)
    2. ~/.hg/workspace exists (use it)
    3. cwd contains .hg_root sentinel (use cwd)
    4. Else raise HydrogenuineError with clear message

    Always returns a resolved absolute Path so downstream path ops (e.g. / "memory")
    are correct on Windows. Use forward slashes in HG_WORKSPACE on Windows
    to avoid backslash/escape issues (e.g. C:/Users/you/.hg/workspace).
    """
    workspace_env = os.environ.get("HG_WORKSPACE")
    if workspace_env:
        # Normalize: strip, fix Windows missing backslash before .hg, then Path
        s = workspace_env.strip()
        # Windows: andrew.hg -> andrew\.hg (only when not already \ or / before .hg)
        if os.name == "nt" and ".hg" in s:
            s = re.sub(r"(?<![\\/])\.hg", r"\\.hg", s)
        p = Path(s).expanduser().resolve()
        return p

    default_workspace = (Path.home() / ".hg" / "workspace").resolve()
    if default_workspace.exists():
        return default_workspace

    cwd = Path.cwd().resolve()
    if (cwd / SENTINEL_FILE).exists():
        return cwd

    raise HydrogenuineError(
        "Set HG_WORKSPACE or create .hg_root in workspace root.",
        code="WORKSPACE_ROOT_REQUIRED",
    )


def ensure_workspace_initialized(root: Path) -> None:
    """
    Create required subdirs if missing. Call only from CLI entry points, not on import.
    Rules:
    - If env set and path does not exist: create root then subdirs
    - If sentinel cwd used and subdirs missing: create subdirs
    - If ~/.hg/workspace does not exist: do not create unless HG_CREATE_DEFAULT_WORKSPACE is set
    """
    subdirs = [
        root / "memory",
        root / "knowledge",
        root / "skills" / "automation" / "tasks",
    ]
    default_workspace = Path.home() / ".hg" / "workspace"
    workspace_env = os.environ.get("HG_WORKSPACE")

    # If using ~/.hg/workspace and it doesn't exist, don't create unless flag set
    if root == default_workspace and not default_workspace.exists():
        if not os.environ.get(HG_CREATE_DEFAULT_WORKSPACE):
            return
        default_workspace.mkdir(parents=True, exist_ok=True)

    # If env points to non-existent path, create root (use same normalization as get_workspace_root)
    if workspace_env:
        s = workspace_env.strip()
        if os.name == "nt" and ".hg" in s:
            s = re.sub(r"(?<![\\/])\.hg", r"\\.hg", s)
        env_path = Path(s).expanduser().resolve()
        if not env_path.exists():
            env_path.mkdir(parents=True, exist_ok=True)

    for d in subdirs:
        d.mkdir(parents=True, exist_ok=True)


def get_memory_dir() -> Path:
    return get_workspace_root() / "memory"


def get_overseer_specs_dir() -> Path:
    """
    Canonical directory for overseer spec YAML files (overseer_spec_v1, human_factors, etc.).
    Always: workspace_root / memory / overseer / specs (the new file location).
    """
    return get_workspace_root() / "memory" / "overseer" / "specs"


def get_knowledge_dir() -> Path:
    return get_workspace_root() / "knowledge"


def get_docs_dir() -> Path:
    return get_workspace_root() / "docs"


def get_incoming_dir() -> Path:
    return get_workspace_root() / "incoming"


def get_skills_dir() -> Path:
    return get_workspace_root() / "skills"


def get_automation_tasks_dir() -> Path:
    return get_workspace_root() / "skills" / "automation" / "tasks"


def get_automation_memory_dir(agent_id: str) -> Path:
    return get_workspace_root() / "memory" / "automation" / f"automation-{agent_id}"


def resolve_task_file_name(task_name: str) -> str:
    """Resolve task markdown aliases while preserving runtime task identity."""
    resolved = TASK_FILE_ALIASES.get(task_name, task_name)
    for prefix in TASK_FILE_PREFIX_ALIASES:
        if resolved.startswith(prefix):
            return resolved[len(prefix):]
    return resolved


def get_task_file_path(task_name: str) -> Path:
    resolved_name = resolve_task_file_name(task_name)
    return get_workspace_root() / "skills" / "automation" / "tasks" / f"{resolved_name}.md"


def get_personas_base_dir() -> Path:
    """Base directory for personas (skills/automation/personas)."""
    return get_workspace_root() / "skills" / "automation" / "personas"


def get_persona_schema_path() -> Path:
    """Path to persona_file_schema.json."""
    return get_workspace_root() / "skills" / "automation" / "persona_file_schema.json"


def get_persona_dir(platform: str, persona_set: str | None) -> Path:
    return get_personas_base_dir() / platform / (persona_set or "default")


def get_persona_config_path(platform: str) -> Path:
    """Path to persona_config.json for platform (skills/automation/{platform}/persona_config.json)."""
    return get_workspace_root() / "skills" / "automation" / platform / "persona_config.json"


def get_cron_jobs_path() -> Path:
    return Path.home() / ".hg" / "cron" / "jobs.json"


def get_posting_lock_path(platform: str = "global") -> Path:
    return get_workspace_root() / "memory" / f"posting_lock_{platform}.lock"
