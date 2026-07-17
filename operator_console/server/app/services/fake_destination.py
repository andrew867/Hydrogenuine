"""Demo-mode destination logger for non-destructive action records."""

import json
from pathlib import Path
from typing import Any


class FakeDestinationLogger:
    """Append-only logger for no-op external action records."""

    def __init__(self, log_path: str | Path):
        self.log_path = Path(log_path)

    @staticmethod
    def _redact_payload(value: Any) -> Any:
        if isinstance(value, dict):
            redacted: dict[str, Any] = {}
            for key, nested in value.items():
                key_l = str(key).lower()
                if key_l in {"secret", "api_key", "password", "token", "bearer"}:
                    continue
                redacted[str(key)] = FakeDestinationLogger._redact_payload(nested)
            return redacted
        if isinstance(value, list):
            return [FakeDestinationLogger._redact_payload(item) for item in value]
        return value

    def log_would_act(self, workflow_id: str, run_id: str, action: str, payload: dict[str, Any]) -> None:
        """Record one simulated external action."""
        import time

        entry = {
            "event": "would_act",
            "workflow_id": workflow_id,
            "run_id": run_id,
            "action": action,
            "payload": self._redact_payload(payload),
            "timestamp": time.time(),
        }
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
