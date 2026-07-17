"""Workspace scope and mutation policy for Phase 29."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hg_runtime.workbench.schemas import WorkbenchError

CREDENTIAL_MARKERS = (".env", "id_rsa", "id_dsa", "id_ed25519", "credential", "credentials", "secret", "token", "key.pem")


@dataclass(frozen=True)
class WorkbenchPolicy:
    workspace_root: Path
    artifact_root: Path
    read_roots: tuple[Path, ...]
    mutation_permit_refs: tuple[str, ...] = ()
    allow_network: bool = False
    allow_package_install: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "workspace_root", self.workspace_root.resolve())
        object.__setattr__(self, "artifact_root", self.artifact_root.resolve())
        object.__setattr__(self, "read_roots", tuple(path.resolve() for path in self.read_roots))

    def _reject_credential_path(self, path: Path) -> None:
        lowered = str(path).lower()
        if any(marker in lowered for marker in CREDENTIAL_MARKERS):
            raise WorkbenchError("credential_path_read_rejected")

    def require_read_path(self, path: Path) -> Path:
        resolved = path.resolve()
        self._reject_credential_path(resolved)
        if not any(resolved == root or root in resolved.parents for root in self.read_roots):
            raise WorkbenchError("read_file_scope_violation")
        return resolved

    def require_artifact_path(self, path: Path) -> Path:
        resolved = path.resolve()
        self._reject_credential_path(resolved)
        if not (resolved == self.artifact_root or self.artifact_root in resolved.parents):
            raise WorkbenchError("write_artifact_scope_violation")
        return resolved

    def require_mutation_permit(self, refs: list[str]) -> None:
        if not refs:
            raise WorkbenchError("workspace_mutation_requires_policy")
        if not set(refs).issubset(set(self.mutation_permit_refs)):
            raise WorkbenchError("live_tool_requires_permit")


__all__ = ["WorkbenchPolicy"]
