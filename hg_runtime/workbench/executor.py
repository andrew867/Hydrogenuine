"""Governed dry-run workbench executor."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.workbench.artifacts import artifact_hash, draft_artifact_receipt
from hg_runtime.workbench.policy import WorkbenchPolicy
from hg_runtime.workbench.receipts import build_invocation_receipt
from hg_runtime.workbench.registry import ToolRegistry, WorkbenchReceiptLog
from hg_runtime.workbench.sandbox import classify_command
from hg_runtime.workbench.schemas import (
    ARTIFACT_RECEIPT_SCHEMA,
    PATCH_CANDIDATE_RECEIPT_SCHEMA,
    TOOL_INVOCATION_RECEIPT_SCHEMA,
    WorkbenchError,
    preempt_if_needed,
    validate_workbench_request,
)


class Workbench:
    def __init__(self, *, registry: ToolRegistry, policy: WorkbenchPolicy, receipt_log: WorkbenchReceiptLog) -> None:
        self.registry = registry
        self.policy = policy
        self.receipt_log = receipt_log

    def invoke(self, request: Mapping[str, Any], *, control: OperationControl | None = None) -> dict[str, Any]:
        preempt_if_needed(control)
        req = validate_workbench_request(request)
        tool = self.registry.get(req["tool_id"])
        kind = tool["capability"]["tool_kind"]
        if req["mode"] != "dry_run":
            self.policy.require_mutation_permit(list(req.get("receipt_refs", [])))
        if kind == "network":
            raise WorkbenchError("network_tool_refuses_by_default")
        if kind == "package_install":
            raise WorkbenchError("package_install_command_is_rejected")
        if kind == "credential_read":
            raise WorkbenchError("credential_path_read_rejected")
        if kind == "shell":
            raise WorkbenchError("arbitrary_shell_command_rejected")
        handler = {
            "read_file": self._read_file,
            "inspect_log": self._read_file,
            "compare_outputs": self._compare_outputs,
            "write_artifact": self._write_artifact,
            "patch_candidate": self._patch_candidate,
            "build_artifact": self._build_artifact,
            "test_run": self._test_run,
        }.get(kind)
        if handler is None:
            raise WorkbenchError("unknown_tool_rejected")
        result = handler(req)
        receipt = build_invocation_receipt(request=req, status=result["status"], result=result, receipt_refs=list(req.get("receipt_refs", [])))
        self.receipt_log.append(TOOL_INVOCATION_RECEIPT_SCHEMA, receipt)
        return {"result": result, "receipt": receipt}

    def _read_file(self, req: Mapping[str, Any]) -> dict[str, Any]:
        path = self.policy.require_read_path(Path(req["inputs"]["path"]))
        content = path.read_text(encoding="utf-8")
        return {"status": "observed", "path": str(path), "content_hash": artifact_hash(content), "preview": content[:200], "mutated": False}

    def _compare_outputs(self, req: Mapping[str, Any]) -> dict[str, Any]:
        left = artifact_hash(str(req["inputs"].get("left", "")))
        right = artifact_hash(str(req["inputs"].get("right", "")))
        return {"status": "observed", "left_hash": left, "right_hash": right, "equal": left == right, "mutated": False}

    def _write_artifact(self, req: Mapping[str, Any]) -> dict[str, Any]:
        path = self.policy.require_artifact_path(Path(req["inputs"]["path"]))
        content = str(req["inputs"].get("content", ""))
        receipt = draft_artifact_receipt(artifact_path=str(path), content=content, receipt_refs=list(req.get("receipt_refs", [])))
        self.receipt_log.append(ARTIFACT_RECEIPT_SCHEMA, receipt)
        if req["mode"] == "dry_run":
            return {"status": "drafted", "would_write": str(path), "artifact_hash": receipt["artifact_hash"], "mutated": False}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"status": "written", "path": str(path), "artifact_hash": receipt["artifact_hash"], "mutated": True}

    def _patch_candidate(self, req: Mapping[str, Any]) -> dict[str, Any]:
        content = str(req["inputs"].get("patch", ""))
        receipt = draft_artifact_receipt(
            artifact_path=str(self.policy.artifact_root / (req["request_id"] + ".patch")),
            content=content,
            receipt_refs=list(req.get("receipt_refs", [])),
            patch_candidate=True,
        )
        self.receipt_log.append(PATCH_CANDIDATE_RECEIPT_SCHEMA, receipt)
        return {"status": "drafted", "patch_hash": receipt["artifact_hash"], "draft_only": True, "merged": False, "mutated": False}

    def _build_artifact(self, req: Mapping[str, Any]) -> dict[str, Any]:
        return {"status": "modeled", "artifact_hash": artifact_hash(str(req["inputs"])), "mutated": False}

    def _test_run(self, req: Mapping[str, Any]) -> dict[str, Any]:
        if not req.get("receipt_refs"):
            raise WorkbenchError("test_run_receipt_required")
        command = str(req["inputs"].get("command", ""))
        classification = classify_command(command)
        if not classification.allowed:
            raise WorkbenchError(classification.reason)
        return {"status": "modeled", "command": command, "command_classification": classification.reason, "mutated": False}


__all__ = ["Workbench"]
