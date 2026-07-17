"""CT-12 OEA capability risk catalog — read-only classification."""

from hg_core.capability_risk.catalog import (
    CapabilityCatalog,
    CapabilityEntry,
    CatalogEntry,
    default_catalog_path,
    load_catalog,
)
from hg_core.capability_risk.enforce import (
    REASON_UNCATALOGED,
    CatalogRefusal,
    classify_capability,
    effective_execution_mode,
    lookup_catalog_entry,
    validate_binding_authorization,
)

__all__ = [
    "REASON_UNCATALOGED",
    "CapabilityCatalog",
    "CapabilityEntry",
    "CatalogEntry",
    "CatalogRefusal",
    "classify_capability",
    "default_catalog_path",
    "effective_execution_mode",
    "load_catalog",
    "lookup_catalog_entry",
    "validate_binding_authorization",
]
