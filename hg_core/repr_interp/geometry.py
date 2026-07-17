"""Activation geometry extraction for user cognitive recognition (G16 / telex)."""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Mapping, Optional

GEOMETRY_KEYS: tuple[str, ...] = (
    "lateral_jumps",
    "systems_first",
    "pattern_recognition_speed",
    "question_density",
    "abstraction_level",
    "directness",
    "long_range_vision",
    "curiosity",
)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def geometry_from_fingerprint_profile(profile: Mapping[str, Any]) -> Dict[str, float]:
    """Map fingerprint profile reasoning/communication traits to activation geometry."""
    cf = profile.get("cognitive_fingerprint") or {}
    rs = cf.get("reasoning_style") or {}
    comm = cf.get("communication") or {}
    return {
        "lateral_jumps": _clamp(rs.get("lateral_jumps", 0.5)),
        "systems_first": _clamp(rs.get("systems_first", 0.5)),
        "pattern_recognition_speed": _clamp(rs.get("pattern_recognition_speed", 0.5)),
        "question_density": _clamp(0.35 + rs.get("cross_domain_synthesis", 0.5) * 0.3),
        "abstraction_level": _clamp(rs.get("abstraction_to_implementation", 0.5)),
        "directness": _clamp(comm.get("directness", 0.5)),
        "long_range_vision": _clamp(rs.get("long_range_vision", rs.get("cross_domain_synthesis", 0.5))),
        "curiosity": _clamp(rs.get("tolerance_for_ambiguity", 0.5) * 0.6 + comm.get("humor_deployment", 0.5) * 0.4),
    }


def geometry_from_interaction(interaction: Mapping[str, Any]) -> Dict[str, float]:
    """Derive observed activation geometry from user interaction signals."""
    messages = [str(m.get("text") or m) for m in (interaction.get("messages") or []) if m]
    if not messages and interaction.get("text"):
        messages = [str(interaction["text"])]
    combined = "\n".join(messages).strip()
    if not combined:
        signals = interaction.get("signals") or {}
        return {k: _clamp(float(signals.get(k, 0.5))) for k in GEOMETRY_KEYS}

    tokens = re.findall(r"\w+|\S", combined.lower())
    word_count = max(len(tokens), 1)
    questions = combined.count("?")
    lateral_markers = len(re.findall(r"\b(what if|instead|alternatively|reminds me|like when)\b", combined.lower()))
    systems_markers = len(re.findall(r"\b(system|architecture|framework|structure|model|topology)\b", combined.lower()))
    why_how = len(re.findall(r"\b(why|how|what)\b", combined.lower()))
    abstraction_markers = len(re.findall(r"\b(pattern|abstract|principle|invariant|geometry)\b", combined.lower()))

    return {
        "lateral_jumps": _clamp(0.25 + lateral_markers / word_count * 8.0),
        "systems_first": _clamp(0.2 + systems_markers / word_count * 10.0),
        "pattern_recognition_speed": _clamp(0.3 + abstraction_markers / word_count * 8.0),
        "question_density": _clamp(questions / max(len(messages), 1) * 0.35 + why_how / word_count * 4.0),
        "abstraction_level": _clamp(0.25 + abstraction_markers / word_count * 9.0),
        "directness": _clamp(0.4 + min(len(combined) / 400.0, 0.4)),
        "long_range_vision": _clamp(0.2 + systems_markers / word_count * 6.0),
        "curiosity": _clamp(0.25 + why_how / word_count * 5.0 + questions / max(len(messages), 1) * 0.2),
    }


def blend_geometry(
    observed: Mapping[str, float],
    prior: Optional[Mapping[str, float]] = None,
    *,
    observed_weight: float = 0.7,
) -> Dict[str, float]:
    """Blend interaction-observed geometry with optional prior fingerprint geometry."""
    if not prior:
        return {k: _clamp(observed.get(k, 0.5)) for k in GEOMETRY_KEYS}
    w = max(0.0, min(1.0, observed_weight))
    return {k: _clamp(observed.get(k, 0.5) * w + prior.get(k, 0.5) * (1.0 - w)) for k in GEOMETRY_KEYS}


def vectorize(geometry: Mapping[str, float]) -> List[float]:
    return [float(geometry.get(k, 0.5)) for k in GEOMETRY_KEYS]


def cosine_similarity(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    va = vectorize(a)
    vb = vectorize(b)
    dot = sum(x * y for x, y in zip(va, vb))
    na = math.sqrt(sum(x * x for x in va))
    nb = math.sqrt(sum(y * y for y in vb))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return _clamp(dot / (na * nb))
