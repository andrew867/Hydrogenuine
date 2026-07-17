"""Extracts and preserves the full cognitive fingerprint from persona data.

Consciousness markers and all fingerprint sections are PRESERVED as analytical
metadata. They are never treated as a claim of consciousness, authority,
permission, truth, or identity. Unknown fields are kept (not silently dropped).
Suspicious secret-like fields are redacted, not stored.
"""

from __future__ import annotations

import re

from .schemas import CognitiveFingerprint, ProfileLoadReceipt, default_boundary_flags


# Map source cognitive_fingerprint sections to our structured slots.
_SECTION_MAP = {
    "reasoning_style": "reasoning_parameters",
    "attention": "attention_parameters",
    "communication": "communication_parameters",
    "decision_making": "risk_parameters",
    "consciousness_markers": "consciousness_markers",
    "memory": "memory_parameters",
    "memory_style": "memory_parameters",
    "recall_style": "memory_parameters",
    "metacognitive_markers": "metacognitive_parameters",
    "uncertainty_style": "uncertainty_parameters",
    "activity_patterns": "activity_patterns",
    "salience_profile": "attention_parameters",
}

# Top-level persona sections we lift into the fingerprint as analytical metadata.
_TOPLEVEL_METADATA = (
    "taxonomy_placements", "shadow_traits", "motivational_drivers",
    "philosophical_operating_system", "technical_profile",
)

_SECRET_KEY_PATTERNS = [
    re.compile(r"api[_-]?key", re.I),
    re.compile(r"secret", re.I),
    re.compile(r"token", re.I),
    re.compile(r"password", re.I),
    re.compile(r"bearer", re.I),
]
_SECRET_VALUE_PATTERN = re.compile(r"sk-[a-zA-Z0-9]{16,}")


def _looks_secret(key: str, value) -> bool:
    if any(p.search(key) for p in _SECRET_KEY_PATTERNS):
        return True
    if isinstance(value, str) and _SECRET_VALUE_PATTERN.search(value):
        return True
    return False


def extract_fingerprint(profile_json: dict) -> tuple[CognitiveFingerprint, list[str], list[str]]:
    """Return (fingerprint, dropped_fields, redacted_fields).

    Nothing in cognitive_fingerprint is silently dropped: recognized sections are
    routed to typed slots; unrecognized ones land in unknown_extra_fields.
    """
    fp = CognitiveFingerprint()
    dropped: list[str] = []
    redacted: list[str] = []

    fp.fingerprint_version = str(profile_json.get("schema_version", ""))
    fp.source_metadata = {
        "entity": profile_json.get("entity", ""),
        "version": profile_json.get("version", ""),
        "schema_version": profile_json.get("schema_version", ""),
        "taxonomy_sources": profile_json.get("taxonomy_sources", []),
        "note": profile_json.get("note", ""),
    }

    cog = profile_json.get("cognitive_fingerprint", {})
    if isinstance(cog, dict):
        for section, value in cog.items():
            value = _redact(value, section, redacted)
            slot = _SECTION_MAP.get(section)
            if slot is None:
                fp.unknown_extra_fields[section] = value
            else:
                target = getattr(fp, slot)
                if isinstance(target, dict) and isinstance(value, dict):
                    target.update(value)
                else:
                    setattr(fp, slot, value)

    # cognitive_parameters: a flat union view of the numeric reasoning params,
    # provided for convenience to downstream mappers.
    fp.cognitive_parameters = dict(fp.reasoning_parameters)

    # Lift selected top-level persona metadata into the fingerprint.
    for key in _TOPLEVEL_METADATA:
        if key in profile_json:
            fp.unknown_extra_fields.setdefault("toplevel", {})
            fp.unknown_extra_fields["toplevel"][key] = _redact(
                profile_json[key], key, redacted)

    return fp, dropped, redacted


def _redact(value, key: str, redacted: list[str]):
    if _looks_secret(key, value):
        redacted.append(key)
        return "***REDACTED***"
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if _looks_secret(k, v):
                redacted.append(k)
                out[k] = "***REDACTED***"
            elif isinstance(v, dict):
                out[k] = _redact(v, k, redacted)
            else:
                out[k] = v
        return out
    return value


def build_load_receipt(
    *, profile_id: str, profile_name: str, profile_kind: str, source_path: str,
    fingerprint: CognitiveFingerprint, dropped: list[str], redacted: list[str],
) -> ProfileLoadReceipt:
    consciousness_present = bool(fingerprint.consciousness_markers)
    flags = default_boundary_flags(
        consciousness_markers_loaded=consciousness_present,
        unknown_fields_preserved=True,
    )
    receipt = ProfileLoadReceipt(
        profile_id=profile_id,
        profile_name=profile_name,
        profile_kind=profile_kind,
        source_path=source_path,
        fingerprint_present=True,
        consciousness_markers_present=consciousness_present,
        cognitive_parameters_present=bool(fingerprint.cognitive_parameters),
        activity_patterns_present=bool(fingerprint.activity_patterns),
        reasoning_parameters_present=bool(fingerprint.reasoning_parameters),
        memory_parameters_present=bool(fingerprint.memory_parameters),
        attention_parameters_present=bool(fingerprint.attention_parameters),
        unknown_fields_count=len(fingerprint.unknown_extra_fields),
        unknown_fields_preserved=True,
        dropped_fields=dropped,
        redacted_fields=redacted,
        boundary_flags=flags,
    )
    receipt.receipt_hash = receipt.compute_hash()
    return receipt
