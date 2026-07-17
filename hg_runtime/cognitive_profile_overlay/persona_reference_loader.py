from __future__ import annotations

from typing import Any, Dict


def load_persona_reference(persona_id: str) -> Dict[str, Any]:
    return {"persona_id": persona_id, "available": False, "source": "community"}
