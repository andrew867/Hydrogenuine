"""Shared CLI helpers for break-glass ops scripts (CT-15 RUN)."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from hg_core.iam.authority import validate_operator_authority
from hg_core.operator_runbook.manifest import OperatorProcedure, load_manifest
from hg_core.operator_runbook.ops_state import save_ops_state
from hg_core.operator_runbook.receipts import record_emergency_receipt


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "hg_core").is_dir() and (parent / "config").is_dir():
            return parent
    return here.parents[2]


def workspace_root() -> Path:
    return repo_root()


def build_parser(procedure: OperatorProcedure, description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--operator-id", required=True, help="Registered operator id (e.g. op:local)")
    if procedure.requires_confirm:
        parser.add_argument(
            "--confirm",
            required=True,
            help=f"Explicit confirmation; must equal procedure id ({procedure.procedure_id})",
        )
    parser.add_argument("--workspace", default=str(workspace_root()), help="Workspace root")
    parser.add_argument("--dry-run", action="store_true", help="Validate only; do not mutate state")
    parser.add_argument("--json", action="store_true", help="Emit JSON result")
    return parser


def validate_break_glass(
    args: argparse.Namespace,
    procedure: OperatorProcedure,
) -> tuple[bool, str]:
    if procedure.requires_confirm and args.confirm != procedure.procedure_id:
        return False, f"confirmation mismatch: expected {procedure.procedure_id}"
    authority = validate_operator_authority(args.operator_id, scope=procedure.scope)
    if not authority.ok:
        return False, authority.reason_code
    return True, "ok"


def emit_result(payload: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")


def run_mutating_procedure(
    procedure_id: str,
    *,
    mutate: Callable[[Path, argparse.Namespace], dict[str, Any]],
    description: str,
) -> int:
    repo_manifest = load_manifest(workspace=workspace_root())
    procedure = repo_manifest.by_id(procedure_id)
    if procedure is None:
        print(f"unknown procedure: {procedure_id}", file=sys.stderr)
        return 2
    parser = build_parser(procedure, description)
    args = parser.parse_args()
    try:
        manifest = load_manifest(workspace=Path(args.workspace))
    except FileNotFoundError:
        manifest = repo_manifest
    ok, reason = validate_break_glass(args, procedure)
    if not ok:
        emit_result({"ok": False, "reason": reason, "procedure_id": procedure_id}, as_json=args.json)
        return 1
    workspace = Path(args.workspace)
    if args.dry_run:
        emit_result(
            {
                "ok": True,
                "dry_run": True,
                "procedure_id": procedure_id,
                "operator_id": args.operator_id,
                "scope": procedure.scope,
            },
            as_json=args.json,
        )
        return 0
    effect = mutate(workspace, args)
    receipt_payload = dict(effect)
    state_obj = receipt_payload.pop("state", None)
    if state_obj is not None and hasattr(state_obj, "to_payload"):
        receipt_payload["state"] = state_obj.to_payload()
    receipt = record_emergency_receipt(
        workspace,
        procedure_id=procedure_id,
        operator_id=args.operator_id,
        scope=procedure.scope,
        payload=receipt_payload,
        receipts_relative=manifest.emergency_receipts_path,
        ledger_reachable=effect.get("ledger_reachable", True),
    )
    state = save_ops_state(
        workspace,
        effect["state"],
        relative=manifest.ops_state_path,
        procedure_id=procedure_id,
        operator_id=args.operator_id,
    )
    emit_result(
        {
            "ok": True,
            "procedure_id": procedure_id,
            "receipt_id": receipt["receipt_id"],
            "status": effect.get("status_summary"),
            "ops_state": state.to_payload(),
        },
        as_json=args.json,
    )
    return 0


def run_read_procedure(
    procedure_id: str,
    *,
    read: Callable[[Path, argparse.Namespace], dict[str, Any]],
    description: str,
) -> int:
    repo_manifest = load_manifest(workspace=workspace_root())
    procedure = repo_manifest.by_id(procedure_id)
    if procedure is None:
        print(f"unknown procedure: {procedure_id}", file=sys.stderr)
        return 2
    parser = build_parser(procedure, description)
    args = parser.parse_args()
    try:
        manifest = load_manifest(workspace=Path(args.workspace))
    except FileNotFoundError:
        manifest = repo_manifest
    ok, reason = validate_break_glass(args, procedure)
    if not ok:
        emit_result({"ok": False, "reason": reason, "procedure_id": procedure_id}, as_json=args.json)
        return 1
    workspace = Path(args.workspace)
    payload = read(workspace, args)
    emit_result(payload, as_json=args.json)
    return 0 if payload.get("ok", True) else 1


__all__ = [
    "build_parser",
    "emit_result",
    "run_mutating_procedure",
    "run_read_procedure",
    "validate_break_glass",
    "workspace_root",
]
