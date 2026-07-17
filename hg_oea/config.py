"""OEA runtime configuration from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OEAConfig:
    mode: str = "stub"
    real_enabled: bool = False
    allowed_capabilities: frozenset[str] = frozenset()
    proof_dir: Path = Path("docs/proofs/oea")
    require_confirmation_for_medium: bool = True
    disable_network: bool = True
    dry_run_ttl_seconds: float = 300.0
    lockdown: bool = False

    @classmethod
    def from_env(cls, *, repo_root: Path | None = None) -> "OEAConfig":
        root = repo_root or Path.cwd()
        mode = os.environ.get("HG_OEA_MODE", "stub").strip().lower()
        real_flag = os.environ.get("HG_OEA_REAL", "0").strip() in {"1", "true", "yes"}
        if real_flag:
            mode = "real"
        allowed_raw = os.environ.get(
            "HG_OEA_ALLOWED_CAPABILITIES",
            "local_report_file.write",
        )
        allowed = frozenset(
            item.strip()
            for item in allowed_raw.split(",")
            if item.strip()
        )
        proof_raw = os.environ.get("HG_OEA_PROOF_DIR", "docs/proofs/oea")
        proof_dir = Path(proof_raw)
        if not proof_dir.is_absolute():
            proof_dir = root / proof_dir
        require_medium = os.environ.get("HG_OEA_REQUIRE_CONFIRMATION_FOR_MEDIUM", "1").strip() in {
            "1",
            "true",
            "yes",
        }
        disable_network = os.environ.get("HG_OEA_DISABLE_NETWORK", "1").strip() in {
            "1",
            "true",
            "yes",
        }
        dry_run_ttl = float(os.environ.get("HG_OEA_DRY_RUN_TTL_SECONDS", "300"))
        lockdown = os.environ.get("HG_OEA_LOCKDOWN", "0").strip() in {"1", "true", "yes"}
        return cls(
            mode=mode,
            real_enabled=real_flag or mode == "real",
            allowed_capabilities=allowed,
            proof_dir=proof_dir,
            require_confirmation_for_medium=require_medium,
            disable_network=disable_network,
            dry_run_ttl_seconds=dry_run_ttl,
            lockdown=lockdown,
        )

    @property
    def is_real(self) -> bool:
        return self.mode == "real" and self.real_enabled


__all__ = ["OEAConfig"]
