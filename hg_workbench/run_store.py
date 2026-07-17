"""WorkbenchRunStore — governed run lifecycle over a per-run chained receipt ledger.

Each run gets a sealed directory `<root>/<run_id>/` holding `run.json` and the
append-only `receipt_chain.jsonl`. INV-RUN-ISO: every mutation is checked to
belong to the addressed run; cross-run access raises RunIsolationError. No raw
tokens are ever accepted or stored (only a sha256 session hash). No external
effects.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from hg_core.governance.canonical_hash import canonical_hash
from hg_operator_auth.identity import OperatorIdentity
from hg_workbench.artifact_store import store_upload
from hg_operator_auth.roles import can_approve_as_human
from hg_operator_auth.stepup_policy import ACTION_CLASS_POLICY, evaluate_step_up
from hg_workbench.models import (
    PROGRESS_EVENT_TYPES, WorkbenchArtifact, WorkbenchProgressEvent,
    WorkbenchRun, WorkbenchSettingChange, WorkbenchSteeringMessage,
    WorkbenchSubagentLane,
)
from hg_workbench.receipts import (
    ArtifactReceipt, ProgressEventReceipt, SettingChangeReceipt, SteeringReceipt,
    WorkbenchRunReceipt, validate_no_raw_token,
)

_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{10,}")
_SHA256_RE = re.compile(r"^(sha256:)?[0-9a-f]{64}$")


class WorkbenchError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class RunIsolationError(WorkbenchError):
    """Raised when a caller addresses a run they do not own or that mismatches."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _text_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _run_from_json(data: dict[str, Any]) -> WorkbenchRun:
    for k in ("artifact_ids", "progress_event_ids", "subagent_lane_ids"):
        if k in data and isinstance(data[k], list):
            data[k] = tuple(data[k])
    return WorkbenchRun(**data)


class WorkbenchRunStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    # ---- internal ledger ----

    def _run_dir(self, run_id: str) -> Path:
        # run_id is the isolation key; reject path escapes.
        if not re.fullmatch(r"wbr-[0-9a-f-]{8,}", run_id):
            raise RunIsolationError("bad_run_id")
        return self.root / run_id

    def _load_run(self, run_id: str) -> WorkbenchRun:
        f = self._run_dir(run_id) / "run.json"
        if not f.exists():
            raise WorkbenchError("run_not_found")
        return _run_from_json(json.loads(f.read_text(encoding="utf-8")))

    def _save_run(self, run: WorkbenchRun) -> None:
        d = self._run_dir(run.run_id)
        d.mkdir(parents=True, exist_ok=True)
        (d / "run.json").write_text(json.dumps({
            **run.to_payload(),
            "artifact_ids": list(run.artifact_ids),
            "progress_event_ids": list(run.progress_event_ids),
            "subagent_lane_ids": list(run.subagent_lane_ids),
        }, indent=1), encoding="utf-8")

    def _chain(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "receipt_chain.jsonl"

    def _last(self, run_id: str) -> tuple[Optional[str], int]:
        c = self._chain(run_id)
        if not c.exists():
            return None, -1
        lines = [l for l in c.read_text(encoding="utf-8").splitlines() if l.strip()]
        if not lines:
            return None, -1
        last = json.loads(lines[-1])
        return last.get("receipt_hash"), int(last.get("seq", -1))

    def _append(self, run_id: str, receipt_cls, **kwargs) -> Any:
        prev, last_seq = self._last(run_id)
        receipt = receipt_cls(run_id=run_id, seq=last_seq + 1, at=_now(),
                              previous_receipt_hash=prev, **kwargs)
        validate_no_raw_token(receipt)
        payload = receipt.to_payload()
        assert not _JWT_RE.search(json.dumps(payload)), "raw token in receipt"
        with self._chain(run_id).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")
        return receipt

    def _require_owner(self, run: WorkbenchRun, identity: OperatorIdentity) -> None:
        if run.operator_subject != identity.subject:
            raise RunIsolationError("run_not_owned_by_operator")

    # ---- public API ----

    def create_run(self, *, identity: OperatorIdentity, request_text: str,
                   workflow_id: str = "adhoc", risk_level: str = "low") -> WorkbenchRun:
        if not can_approve_as_human(identity.roles):
            raise WorkbenchError("not_a_human_operator")
        if identity.session_id_hash and not _SHA256_RE.match(identity.session_id_hash):
            raise WorkbenchError("session_id_not_hashed")
        with self._lock:
            run_id = f"wbr-{uuid.uuid4()}"
            run = WorkbenchRun(
                run_id=run_id, operator_subject=identity.subject,
                session_id_hash=identity.session_id_hash,
                request_text=request_text, workflow_id=workflow_id,
                status="created", created_at=_now(), risk_level=risk_level,
                external_effects_enabled=False)
            self._save_run(run)
            receipt = self._append(
                run_id, WorkbenchRunReceipt, receipt_id=f"wbrr-{run_id[4:16]}",
                operator_subject=identity.subject,
                session_id_hash=identity.session_id_hash,
                request_hash=_text_hash(request_text), workflow_id=workflow_id,
                risk_level=risk_level, external_effects_enabled=False)
            run = replace(run, receipt_chain_head=receipt.receipt_hash)
            self._save_run(run)
            return run

    def list_runs(self, identity: OperatorIdentity) -> list[WorkbenchRun]:
        out = []
        for d in sorted(self.root.iterdir()):
            f = d / "run.json"
            if f.is_file():
                run = _run_from_json(json.loads(f.read_text(encoding="utf-8")))
                if run.operator_subject == identity.subject:
                    out.append(run)
        return out

    def get_run(self, run_id: str, identity: OperatorIdentity) -> WorkbenchRun:
        run = self._load_run(run_id)
        self._require_owner(run, identity)
        return run

    def register_artifact(self, *, run_id: str, identity: OperatorIdentity,
                          filename: str, mime_type: str, size_bytes: int,
                          content_hash: str, source: str = "upload",
                          document_ref: Optional[str] = None,
                          label: str = "") -> WorkbenchArtifact:
        with self._lock:
            run = self._load_run(run_id)
            self._require_owner(run, identity)
            artifact_id = f"wba-{uuid.uuid4().hex[:16]}"
            artifact = WorkbenchArtifact(
                artifact_id=artifact_id, run_id=run_id, filename=filename,
                mime_type=mime_type, size_bytes=size_bytes,
                content_hash=content_hash, source=source, document_ref=document_ref,
                label=label)
            self._append(run_id, ArtifactReceipt,
                         receipt_id=f"wbar-{artifact_id[4:16]}",
                         artifact_id=artifact_id, filename=filename,
                         content_hash=content_hash, source=source, label=label)
            self._save_run(replace(run, artifact_ids=run.artifact_ids + (artifact_id,)))
            return artifact

    def register_uploaded_artifact(
            self, *, run_id: str, identity: OperatorIdentity, filename: str,
            mime_type: str, chunks, expected_sha256: Optional[str] = None,
            sensitivity: str = "unclassified", label: str = "",
            max_bytes: Optional[int] = None) -> tuple[WorkbenchArtifact, str]:
        """Write uploaded *bytes* to the bounded local store, then receipt the
        metadata (hash/size/path-ref — never the bytes). Returns the artifact and
        the appended receipt's hash. Optional ``expected_sha256`` is treated as a
        client *expectation*: a mismatch against the server hash rejects the upload
        and removes the stored file. ``ArtifactStoreError``/``ArtifactTooLargeError``
        propagate for the route to map to 4xx.
        """
        with self._lock:
            run = self._load_run(run_id)
            self._require_owner(run, identity)
            artifact_id = f"wba-{uuid.uuid4().hex[:16]}"
            stored = store_upload(
                run_dir=self._run_dir(run_id), artifact_id=artifact_id,
                filename=filename, chunks=chunks, max_bytes=max_bytes)
            if expected_sha256:
                exp = expected_sha256.strip().lower()
                exp = exp if exp.startswith("sha256:") else f"sha256:{exp}"
                if exp != stored.content_hash.lower():
                    Path(stored.absolute_path).unlink(missing_ok=True)
                    raise WorkbenchError("content_hash_mismatch")
            artifact = WorkbenchArtifact(
                artifact_id=artifact_id, run_id=run_id,
                filename=stored.sanitized_filename, mime_type=mime_type,
                size_bytes=stored.size_bytes, content_hash=stored.content_hash,
                source="upload_bytes", sensitivity=sensitivity,
                stored_path_ref=stored.stored_path_ref, label=label)
            receipt = self._append(
                run_id, ArtifactReceipt, receipt_id=f"wbar-{artifact_id[4:16]}",
                artifact_id=artifact_id, filename=stored.sanitized_filename,
                content_hash=stored.content_hash, source="upload_bytes",
                stored_path_ref=stored.stored_path_ref,
                size_bytes=stored.size_bytes, label=label)
            self._save_run(replace(run, artifact_ids=run.artifact_ids + (artifact_id,)))
            return artifact, receipt.receipt_hash

    def append_progress(self, *, run_id: str, identity: OperatorIdentity,
                        event_type: str, subagent_lane_id: Optional[str] = None,
                        persona: Optional[str] = None,
                        detail: str = "") -> WorkbenchProgressEvent:
        if event_type not in PROGRESS_EVENT_TYPES:
            raise WorkbenchError("unknown_event_type")
        with self._lock:
            run = self._load_run(run_id)
            self._require_owner(run, identity)
            _, last_seq = self._last(run_id)
            event_id = f"wbe-{uuid.uuid4().hex[:16]}"
            event = WorkbenchProgressEvent(
                event_id=event_id, run_id=run_id, seq=last_seq + 1,
                event_type=event_type, at=_now(),
                subagent_lane_id=subagent_lane_id, persona=persona,
                detail=detail, authority=False)   # observation, never authority
            self._append(run_id, ProgressEventReceipt,
                         receipt_id=f"wber-{event_id[4:16]}", event_id=event_id,
                         event_type=event_type, subagent_lane_id=subagent_lane_id,
                         authority=False)
            new_lanes = run.subagent_lane_ids
            if subagent_lane_id and subagent_lane_id not in new_lanes:
                new_lanes = new_lanes + (subagent_lane_id,)
            self._save_run(replace(
                run, progress_event_ids=run.progress_event_ids + (event_id,),
                subagent_lane_ids=new_lanes, status="in_progress"))
            return event

    def append_steering(self, *, run_id: str, identity: OperatorIdentity,
                        text: str) -> WorkbenchSteeringMessage:
        with self._lock:
            run = self._load_run(run_id)
            self._require_owner(run, identity)
            message_id = f"wbs-{uuid.uuid4().hex[:16]}"
            msg = WorkbenchSteeringMessage(
                message_id=message_id, run_id=run_id, text=text, at=_now())
            self._append(run_id, SteeringReceipt,
                         receipt_id=f"wbsr-{message_id[4:16]}",
                         message_id=message_id, text_hash=_text_hash(text),
                         authority="advice_not_authority")
            return msg

    def request_setting_change(self, *, run_id: str, identity: OperatorIdentity,
                               setting: str, action_class: str, old_value: str,
                               new_value: str,
                               last_step_up_at: Optional[datetime] = None,
                               ) -> WorkbenchSettingChange:
        """Governed setting change. High/restricted held pending step-up."""
        if action_class not in ACTION_CLASS_POLICY:
            raise WorkbenchError("unknown_action_class")
        with self._lock:
            run = self._load_run(run_id)
            self._require_owner(run, identity)
            verdict = evaluate_step_up(
                action_class=action_class, decision="approve", identity=identity,
                now=datetime.now(timezone.utc), last_step_up_at=last_step_up_at)
            applied = verdict.allowed
            change_id = f"wbc-{uuid.uuid4().hex[:16]}"
            change = WorkbenchSettingChange(
                change_id=change_id, run_id=run_id, setting=setting,
                action_class=action_class, old_value=old_value,
                new_value=new_value, at=_now(), applied=applied,
                hold_reason="" if applied else verdict.reason)
            self._append(run_id, SettingChangeReceipt,
                         receipt_id=f"wbcr-{change_id[4:16]}", change_id=change_id,
                         setting=setting, action_class=action_class,
                         new_value_hash=_text_hash(new_value), applied=applied,
                         hold_reason="" if applied else verdict.reason)
            if not applied:
                self._save_run(replace(run, status="held"))
            return change

    def read_chain(self, run_id: str, identity: OperatorIdentity) -> list[dict[str, Any]]:
        run = self._load_run(run_id)
        self._require_owner(run, identity)
        c = self._chain(run_id)
        if not c.exists():
            return []
        return [json.loads(l) for l in c.read_text(encoding="utf-8").splitlines()
                if l.strip()]


__all__ = ["RunIsolationError", "WorkbenchError", "WorkbenchRunStore"]
