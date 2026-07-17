"""External Start Anchor — GitHub witness continuity for Agent Zero boot.

A public anchor is continuity evidence only: not authority, not memory, not consent.
"""

from hg_runtime.external_start_anchor.agent0_context import (
    ANCHOR_BOOT_INSTRUCTION,
    build_agent0_anchor_boot_context,
    load_anchor_handoff,
)
from hg_runtime.external_start_anchor.schema import (
    ANCHOR_SCHEMA_VERSION,
    AnchorConfidence,
    BootContinuityBundle,
    ExternalStartAnchorContext,
    GitHubAnchorConfig,
    PublicAnchorBundle,
)

__all__ = [
    "ANCHOR_BOOT_INSTRUCTION",
    "ANCHOR_SCHEMA_VERSION",
    "AnchorConfidence",
    "BootContinuityBundle",
    "ExternalStartAnchorContext",
    "GitHubAnchorConfig",
    "PublicAnchorBundle",
    "build_agent0_anchor_boot_context",
    "load_anchor_handoff",
]
