"""Local Inference QA Orchestrator artifact writer."""

from __future__ import annotations

import json

from hg_runtime.local_inference_qa_orchestrator.schemas import (
    _stable_hash,
    reject_qa_overreach,
)


def build_qa_artifacts(qa_result: dict) -> dict:
    reject_qa_overreach(qa_result.get("manifest", {}))
    result = {
        "qa_result": qa_result,
        "qa_complete": qa_result.get("qa_complete", False),
        "patches_applied": qa_result.get("patches_applied", False),
        "tests_auto_created": qa_result.get("tests_auto_created", False),
        "tools_authorized": qa_result.get("tools_authorized", False),
    }
    result["artifact_hash"] = _stable_hash(result)
    return result


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    patterns = {
        '"sk-': "sk-",
        "api_key=": "api_key=",
        "Bearer ": "Bearer ",
        "token=": "token=",
        "password=": "password=",
    }
    return [label for key, label in patterns.items() if key.lower() in text.lower()]
