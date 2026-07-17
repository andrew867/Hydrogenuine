"""
OS Phase 2: Red-team and chaos testing.
Generates deterministic adversarial ledgers for CI/nightly; tests verify expected detections and enforcement.
"""

from .generate_adversarial_run import generate_adversarial_run

__all__ = ["generate_adversarial_run"]
