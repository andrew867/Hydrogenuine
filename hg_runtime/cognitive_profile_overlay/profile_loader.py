from __future__ import annotations

from typing import Any, Dict


def load_profile(profile_id: str) -> Dict[str, Any]:
    return {"profile_id": profile_id, "available": False, "source": "community"}
