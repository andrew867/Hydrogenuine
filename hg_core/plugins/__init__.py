"""
OS Phase 5: Plugin SDK — manifest, install/enable/disable, capability checks.
"""

from .sdk import (
    load_plugin_manifest,
    register_plugin,
    enable_plugin,
    disable_plugin,
    list_plugins,
    check_plugin_capability,
)

__all__ = [
    "load_plugin_manifest",
    "register_plugin",
    "enable_plugin",
    "disable_plugin",
    "list_plugins",
    "check_plugin_capability",
]
