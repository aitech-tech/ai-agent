"""
Platform-level MCP tools — license management and platform status.
These are the tools Claude uses to interact with the ReckLabs platform layer.
"""
import logging

from license.license_manager import activate_license, get_license_status
from config.settings import PLATFORM_VERSION, MCP_SERVER_VERSION

logger = logging.getLogger(__name__)


def check_license(params: dict) -> dict:
    """Return current license status and plan details."""
    return {"success": True, "data": get_license_status()}


def activate_license_key(params: dict) -> dict:
    """Activate a ReckLabs license key. Params: {key: str}"""
    key = params.get("key", "").strip()
    if not key:
        return {"success": False, "error": "missing_param", "message": "'key' parameter required"}
    return activate_license(key)


def get_platform_status(params: dict) -> dict:
    """Return platform version, registered connectors, and license status."""
    from registry.connector_registry import registry
    return {
        "success": True,
        "data": {
            "platform": "ReckLabs AI Agent",
            "platform_version": PLATFORM_VERSION,
            "mcp_server_version": MCP_SERVER_VERSION,
            "registered_connectors": registry.list_connectors(),
            "license": get_license_status(),
        },
    }


PLATFORM_TOOLS = [
    {
        "name": "check_license",
        "description": "Check your ReckLabs license status and current plan (Free/Starter/Professional/Enterprise).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "fn": check_license,
    },
    {
        "name": "activate_license",
        "description": "Activate a ReckLabs license key to unlock additional connectors and features.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "License key in format XXXX-XXXX-XXXX-XXXX",
                },
            },
            "required": ["key"],
        },
        "fn": activate_license_key,
    },
    {
        "name": "get_platform_status",
        "description": "Get ReckLabs platform version, registered connectors, and license info.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "fn": get_platform_status,
    },
]
