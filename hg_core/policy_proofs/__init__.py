"""
Differentiators Pack 1: Policy proofs.
Machine-checkable proof objects for policy evaluations; exportable in offline bundles.
"""

from .proofs import (
    create_proof,
    get_proof,
    evaluate_with_proof,
)

__all__ = [
    "create_proof",
    "get_proof",
    "evaluate_with_proof",
]
