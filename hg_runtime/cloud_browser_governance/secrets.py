"""Secret reference and credential policy."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.cloud_browser_governance.types import advisory_envelope, redact_secrets

WORKSPACE = Path(__file__).resolve().parents[2]
SECRET_REFS = WORKSPACE / "configs" / "secrets" / "secret_refs.example.json"


@dataclass(frozen=True)
class SecretRef:
    name: str
    env_var: str

    def presence(self, env: dict[str, str] | None = None) -> bool:
        env = env or dict(os.environ)
        return bool(env.get(self.env_var, "").strip())


def load_secret_refs(path: Path | None = None) -> dict[str, SecretRef]:
    p = path or SECRET_REFS
    data = json.loads(p.read_text(encoding="utf-8"))
    refs: dict[str, SecretRef] = {}
    for name, cfg in data.get("providers", {}).items():
        refs[name] = SecretRef(name=name, env_var=cfg["api_key_env"])
    return refs


def secret_presence_check(env: dict[str, str] | None = None) -> dict[str, Any]:
    from hg_runtime.cloud_browser_governance.env_loader import load_local_env_files

    load_local_env_files()
    env = env or dict(os.environ)
    refs = load_secret_refs()
    presence = {name: ref.presence(env) for name, ref in refs.items()}
    return advisory_envelope(
        schema="secret-presence-check",
        presence=presence,
        secret_values_included=False,
    )


def credential_policy_gate(tracked_files: list[str] | None = None) -> dict[str, Any]:
    failures: list[str] = []
    if tracked_files:
        for path in tracked_files:
            try:
                text = Path(path).read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "sk-" in text and ".example" not in path and "REDACTED" not in text:
                redacted = redact_secrets(text)
                if redacted != text:
                    failures.append(path)
    return advisory_envelope(
        schema="credential-policy-gate",
        ok=not failures,
        failures=failures,
    )


__all__ = ["SecretRef", "credential_policy_gate", "load_secret_refs", "secret_presence_check"]
