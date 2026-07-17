"""
OS Phase 3: Merkle anchoring and integrity verification.
ANCHOR_PUBLISHED, ANCHOR_VERIFIED; Merkle root over event ranges.
"""

from .merkle import merkle_root, compute_merkle_root_for_range
from .anchor import publish_anchor, verify_anchor

__all__ = [
    "merkle_root",
    "compute_merkle_root_for_range",
    "publish_anchor",
    "verify_anchor",
]
