"""Product stack ↔ organism bridge (CT-08 BRG)."""

from hg_core.product_bridge.manifest import (
    BridgeSurface,
    ProductOrganismBridgeManifest,
    default_manifest_path,
    load_manifest,
    manifest_hash,
)
from hg_core.product_bridge.validator import ValidationFinding, validate_manifest
from hg_core.product_bridge.plt_crosscheck import crosscheck_plt_statuses

__all__ = [
    "BridgeSurface",
    "ProductOrganismBridgeManifest",
    "ValidationFinding",
    "crosscheck_plt_statuses",
    "default_manifest_path",
    "load_manifest",
    "manifest_hash",
    "validate_manifest",
]
