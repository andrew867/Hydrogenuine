"""Docker Compose profile metadata."""

from __future__ import annotations

PROFILES = {
    "fixture": {
        "description": "Default fixture-only mode. No live model, no external providers.",
        "requires_lmstudio": False,
        "requires_openvino": False,
        "requires_database": False,
        "safe_for_demo": True,
    },
    "lmstudio": {
        "description": "Connect to LM Studio on host or network. Model must be allowlisted.",
        "requires_lmstudio": True,
        "requires_openvino": False,
        "requires_database": False,
        "safe_for_demo": True,
    },
    "openvino": {
        "description": "Use OpenVINO runtime with mounted models. Downloads disabled by default.",
        "requires_lmstudio": False,
        "requires_openvino": True,
        "requires_database": False,
        "safe_for_demo": True,
    },
    "db": {
        "description": "Enable database persistence for runs, receipts, proofs.",
        "requires_lmstudio": False,
        "requires_openvino": False,
        "requires_database": True,
        "safe_for_demo": True,
    },
    "demo": {
        "description": "Demo profile with fixture data, safe commands, no live effects.",
        "requires_lmstudio": False,
        "requires_openvino": False,
        "requires_database": False,
        "safe_for_demo": True,
    },
    "dev": {
        "description": "Development profile with test runner access.",
        "requires_lmstudio": False,
        "requires_openvino": False,
        "requires_database": False,
        "safe_for_demo": False,
    },
}
