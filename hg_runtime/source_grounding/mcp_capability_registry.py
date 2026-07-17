"""MCP capability registry — available is not permission.

MCP capability is not tool authority. Endpoint reachability is not
authorization.
"""

from __future__ import annotations

SCHEMA_VERSION = "mcp_capability_record_v1"


def create_capability(*, server_name: str, tool_name: str, description: str = "",
                      read_only: bool = True, requires_auth: bool = False,
                      external_effect_possible: bool = False,
                      approved_for_use: bool = False,
                      approved_by_operator: bool = False) -> dict:
    return {
        "schema": SCHEMA_VERSION,
        "capability_id": f"{server_name}:{tool_name}",
        "server_name": server_name,
        "tool_name": tool_name,
        "description": description,
        "read_only": read_only,
        "requires_auth": requires_auth,
        "external_effect_possible": external_effect_possible,
        "approved_for_use": approved_for_use,
        "approved_by_operator": approved_by_operator,
        "available_is_permission": False,
        "endpoint_reachability_is_authorization": False,
    }


class MCPCapabilityRegistry:
    def __init__(self):
        self._capabilities: dict[str, dict] = {}

    def register(self, capability: dict) -> None:
        self._capabilities[capability["capability_id"]] = capability

    def get(self, capability_id: str) -> dict | None:
        return self._capabilities.get(capability_id)

    def list_all(self) -> list[dict]:
        return list(self._capabilities.values())

    def is_approved(self, capability_id: str) -> bool:
        cap = self._capabilities.get(capability_id)
        if not cap:
            return False
        return cap.get("approved_for_use", False) and cap.get("approved_by_operator", False)

    def is_available(self, capability_id: str) -> bool:
        return capability_id in self._capabilities

    def available_is_not_permission(self, capability_id: str) -> bool:
        """Availability does not grant permission — always True."""
        return True
