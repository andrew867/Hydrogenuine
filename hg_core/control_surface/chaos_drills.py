"""
Control Surface Pack 4: Chaos drill scripts — kill stream, lag materializers, revoke bridge trust root.
Run: python -m hg_core.control_surface.chaos_drills <drill> [workspace_root]
"""
from __future__ import annotations

import sys
from pathlib import Path


def _workspace(root: str | None) -> Path:
    if root:
        return Path(root)
    try:
        from hg_lib.config import get_workspace_root
        return Path(get_workspace_root())
    except ImportError:
        return Path(".").resolve()


def kill_stream(workspace_root: Path) -> str:
    """Create stream_disabled.flag so stream is treated as down. Returns path."""
    flag = workspace_root / "memory" / "overseer" / "stream_disabled.flag"
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text("chaos drill: stream disabled", encoding="utf-8")
    return str(flag)


def lag_materializers(workspace_root: Path) -> str:
    """Create materializer_lag.flag for lag simulation. Returns path."""
    flag = workspace_root / "memory" / "overseer" / "materializer_lag.flag"
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text("chaos drill: materializer lag", encoding="utf-8")
    return str(flag)


def revoke_bridge_trust_root(workspace_root: Path) -> str:
    """Rename bridge trust root so it is not loaded (if present). Else create revoked marker. Returns path."""
    root = workspace_root / "artifacts" / "trust"
    if not root.exists():
        root = workspace_root / "memory" / "overseer"
    root.mkdir(parents=True, exist_ok=True)
    candidates = list(root.glob("*bridge*")) if root.exists() else []
    if not candidates:
        marker = root / "bridge_trust_revoked.chaos"
        marker.write_text("chaos drill: bridge trust root revoked (no file to rename)", encoding="utf-8")
        return str(marker)
    target = candidates[0]
    backup = target.with_suffix(target.suffix + ".chaos_backup")
    if target.exists():
        target.rename(backup)
        return str(backup)
    marker = root / "bridge_trust_revoked.chaos"
    marker.write_text("chaos drill: already revoked or missing", encoding="utf-8")
    return str(marker)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m hg_core.control_surface.chaos_drills <kill_stream|lag_materializers|revoke_bridge_trust_root> [workspace_root]")
        return 2
    drill = sys.argv[1].strip().lower()
    workspace_root = _workspace(sys.argv[2] if len(sys.argv) > 2 else None)
    if drill == "kill_stream":
        path = kill_stream(workspace_root)
        print("Created:", path)
        return 0
    if drill == "lag_materializers":
        path = lag_materializers(workspace_root)
        print("Created:", path)
        return 0
    if drill == "revoke_bridge_trust_root":
        path = revoke_bridge_trust_root(workspace_root)
        print("Result:", path)
        return 0
    print("Unknown drill:", drill)
    return 2


if __name__ == "__main__":
    sys.exit(main())
