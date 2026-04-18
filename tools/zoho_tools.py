"""
Zoho MCP tools — thin adapter layer between MCP and the Zoho connector.
Tools never access external APIs directly; always go through the connector.
"""
import json
import logging
from typing import Any

from registry.connector_registry import registry
from connectors.base_connector import ConnectorError, AuthenticationError

logger = logging.getLogger(__name__)


def _get_zoho():
    """Return the Zoho connector, initializing auth if needed."""
    connector = registry.get("zoho")
    if not connector._authenticated:
        connector.authenticate()
    return connector


def _safe_execute(fn) -> dict:
    """Wrap connector calls to return a consistent JSON structure."""
    try:
        result = fn()
        return {"success": True, "data": result}
    except AuthenticationError as e:
        return {
            "success": False,
            "error": "authentication_required",
            "message": str(e),
            "next_step": "Use the zoho_authenticate tool to start the OAuth flow",
        }
    except ConnectorError as e:
        return {"success": False, "error": "connector_error", "message": str(e)}
    except Exception as e:
        logger.exception("Unexpected error in Zoho tool")
        return {"success": False, "error": "unexpected_error", "message": str(e)}


# ------------------------------------------------------------------
# Tool functions — these are registered with the MCP server
# ------------------------------------------------------------------

def zoho_authenticate(params: dict) -> dict:
    """
    Start the Zoho OAuth2 flow or check authentication status.
    If credentials are configured, opens browser for authorization.
    """
    connector = registry.get("zoho")
    return _safe_execute(connector.authenticate)


def zoho_get_auth_url(params: dict) -> dict:
    """Return the Zoho OAuth authorization URL (for manual/headless setup)."""
    connector = registry.get("zoho")
    return {"success": True, "data": {"url": connector.get_auth_url()}}


def zoho_exchange_code(params: dict) -> dict:
    """Exchange an OAuth authorization code for tokens. Params: {code: str}"""
    code = params.get("code")
    if not code:
        return {"success": False, "error": "missing_param", "message": "'code' parameter required"}
    connector = registry.get("zoho")
    return _safe_execute(lambda: connector.exchange_code(code))


def get_zoho_leads(params: dict) -> dict:
    """
    Fetch leads from Zoho CRM.
    Params: {limit: int, page: int, fields: list[str]}
    """
    limit = int(params.get("limit", 20))
    page = int(params.get("page", 1))
    fields = params.get("fields")
    return _safe_execute(lambda: _get_zoho().get_leads(limit=limit, page=page, fields=fields))


def get_zoho_contacts(params: dict) -> dict:
    """
    Fetch contacts from Zoho CRM.
    Params: {limit: int, page: int, fields: list[str]}
    """
    limit = int(params.get("limit", 20))
    page = int(params.get("page", 1))
    fields = params.get("fields")
    return _safe_execute(lambda: _get_zoho().get_contacts(limit=limit, page=page, fields=fields))


def get_zoho_accounts(params: dict) -> dict:
    """Fetch accounts from Zoho CRM. Params: {limit: int}"""
    limit = int(params.get("limit", 20))
    return _safe_execute(lambda: _get_zoho().get_accounts(limit=limit))


def search_zoho_leads(params: dict) -> dict:
    """
    Search Zoho leads by criteria.
    Params: {criteria: str}  e.g. "Email:equals:test@example.com"
    """
    criteria = params.get("criteria")
    if not criteria:
        return {"success": False, "error": "missing_param", "message": "'criteria' parameter required"}
    return _safe_execute(lambda: _get_zoho().search_leads(criteria=criteria))


# ------------------------------------------------------------------
# Tool manifest — used by MCP server to register tools
# ------------------------------------------------------------------

ZOHO_TOOLS = [
    {
        "name": "zoho_authenticate",
        "description": "Start Zoho CRM OAuth2 authentication or check auth status. Call this first before using other Zoho tools.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "fn": zoho_authenticate,
    },
    {
        "name": "zoho_get_auth_url",
        "description": "Get the Zoho OAuth authorization URL for manual authentication setup.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "fn": zoho_get_auth_url,
    },
    {
        "name": "zoho_exchange_code",
        "description": "Exchange an OAuth authorization code for Zoho access tokens.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Authorization code from Zoho OAuth redirect"},
            },
            "required": ["code"],
        },
        "fn": zoho_exchange_code,
    },
    {
        "name": "get_zoho_leads",
        "description": "Fetch leads from Zoho CRM. Returns a list of lead records.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of leads to fetch (max 200)", "default": 20},
                "page": {"type": "integer", "description": "Page number for pagination", "default": 1},
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific fields to return (e.g. ['First_Name','Email','Company'])",
                },
            },
            "required": [],
        },
        "fn": get_zoho_leads,
    },
    {
        "name": "get_zoho_contacts",
        "description": "Fetch contacts from Zoho CRM. Returns a list of contact records.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of contacts to fetch", "default": 20},
                "page": {"type": "integer", "description": "Page number for pagination", "default": 1},
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific fields to return",
                },
            },
            "required": [],
        },
        "fn": get_zoho_contacts,
    },
    {
        "name": "get_zoho_accounts",
        "description": "Fetch company accounts from Zoho CRM.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of accounts to fetch", "default": 20},
            },
            "required": [],
        },
        "fn": get_zoho_accounts,
    },
    {
        "name": "search_zoho_leads",
        "description": "Search Zoho CRM leads using a criteria string.",
        "input_schema": {
            "type": "object",
            "properties": {
                "criteria": {
                    "type": "string",
                    "description": "Search criteria e.g. 'Email:equals:test@example.com' or 'Company:contains:Acme'",
                },
            },
            "required": ["criteria"],
        },
        "fn": search_zoho_leads,
    },
]
