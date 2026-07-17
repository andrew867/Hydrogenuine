"""
Merkle tree over event IDs (or hashes). Deterministic ordering.
Computes root for a list of hashes; used by anchor service for ranges.
"""
from __future__ import annotations

import hashlib
from typing import List, Sequence


def _hash_pair(a: str, b: str) -> str:
    """Single SHA-256 over two hex strings, ordered."""
    return hashlib.sha256((a + b).encode()).hexdigest()


def merkle_root(hashes: Sequence[str]) -> str:
    """
    Compute Merkle root from an ordered list of leaf hashes (event_id or body hash).
    If odd number, duplicate last. Deterministic.
    """
    if not hashes:
        return hashlib.sha256(b"").hexdigest()
    layer = list(hashes)
    while len(layer) > 1:
        next_layer: List[str] = []
        for i in range(0, len(layer), 2):
            if i + 1 < len(layer):
                next_layer.append(_hash_pair(layer[i], layer[i + 1]))
            else:
                next_layer.append(_hash_pair(layer[i], layer[i]))
        layer = next_layer
    return layer[0]


def compute_merkle_root_for_range(
    event_ids: Sequence[str],
    from_event_id: str,
    to_event_id: str,
) -> str:
    """
    Compute Merkle root over event_ids in range [from_event_id, to_event_id] (inclusive).
    Uses event_id as leaf hash (event_id is already a hash). Returns root hex.
    """
    in_range: List[str] = []
    started = False
    for eid in event_ids:
        if eid == from_event_id:
            started = True
        if started:
            in_range.append(eid)
        if started and eid == to_event_id:
            break
    return merkle_root(in_range)
