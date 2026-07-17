"""OEA argument validation and canonical hashing."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple

from hg_core.ledger.canonical_json import canonical_dumps
from hg_core.secrets.redact import contains_raw_secret_pattern, redact_text as central_redact_text
from hg_oea.registry import LOCAL_REPORT_ARGS_SCHEMA
from hg_oea.types import CapabilityDefinition

SECRET_PATTERNS = (
    re.compile(r"Bearer\s+\S+", re.I),
    re.compile(r"api[_-]?key\s*[:=]\s*\S+", re.I),
    re.compile(r"password\s*[:=]\s*\S+", re.I),
    re.compile(r"token\s*[:=]\s*\S+", re.I),
)

FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MAX_CONTENT_BYTES = 65536


class ValidationError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def canonical_hash(payload: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(canonical_dumps(dict(payload))).hexdigest()
    return f"sha256:{digest}"


def redact_text(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def validate_arguments(
    capability: CapabilityDefinition,
    arguments: Mapping[str, Any],
) -> Dict[str, Any]:
    if not isinstance(arguments, Mapping):
        raise ValidationError("arguments_must_be_object")
    args = dict(arguments)
    schema = capability.allowed_argument_schema
    required = schema.get("required", [])
    for key in required:
        if key not in args:
            raise ValidationError(f"missing_required:{key}")
    allowed_props = set(schema.get("properties", {}))
    if schema.get("additionalProperties") is False:
        extra = set(args) - allowed_props
        if extra:
            raise ValidationError(f"unexpected_fields:{','.join(sorted(extra))}")
    for key, value in args.items():
        prop = schema.get("properties", {}).get(key, {})
        if prop.get("type") == "string" and isinstance(value, str):
            max_len = prop.get("maxLength")
            if max_len is not None and len(value) > int(max_len):
                raise ValidationError(f"field_too_long:{key}")
        if prop.get("type") == "boolean" and not isinstance(value, bool):
            raise ValidationError(f"invalid_boolean:{key}")
    raw = canonical_dumps(args).decode("utf-8")
    for pattern in capability.forbidden_argument_patterns:
        if pattern in raw:
            raise ValidationError(f"forbidden_pattern:{pattern}")
    if capability.capability_id == "local_report_file.write":
        _validate_local_report_args(args)
    _validate_secret_handles(capability, args)
    return args


def _validate_secret_handles(capability: CapabilityDefinition, args: Mapping[str, Any]) -> None:
    for field in capability.secret_requirements:
        if field not in args:
            continue
        value = args[field]
        if not isinstance(value, str) or not value.startswith("secret_ref:"):
            raise ValidationError("secret_must_use_handle")
    for key, value in args.items():
        if isinstance(value, str) and contains_raw_secret_pattern(value):
            if not value.startswith("secret_ref:"):
                raise ValidationError(f"raw_secret_in_argument:{key}")


def _validate_local_report_args(args: Mapping[str, Any]) -> None:
    filename = str(args.get("filename", ""))
    if not FILENAME_PATTERN.match(filename):
        raise ValidationError("invalid_filename")
    content = str(args.get("content", ""))
    if len(content.encode("utf-8")) > MAX_CONTENT_BYTES:
        raise ValidationError("content_too_large")


def resolve_proof_path(proof_dir: Path, filename: str) -> Path:
    base = proof_dir.resolve()
    target = (base / filename).resolve()
    if base not in target.parents and target != base:
        raise ValidationError("path_traversal")
    return target


def argument_schema_hash(capability: CapabilityDefinition) -> str:
    return canonical_hash(capability.allowed_argument_schema)


def input_hash(arguments: Mapping[str, Any]) -> str:
    return canonical_hash({"arguments": dict(arguments)})


__all__ = [
    "ValidationError",
    "argument_schema_hash",
    "canonical_hash",
    "input_hash",
    "redact_text",
    "resolve_proof_path",
    "validate_arguments",
]
