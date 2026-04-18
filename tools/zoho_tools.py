"""
Zoho MCP tools — routes CRM and Books calls through ZohoConnector.
Tools never access external APIs directly; always go through the connector.
"""
import logging
from registry.connector_registry import registry
from connectors.base_connector import ConnectorError, AuthenticationError

logger = logging.getLogger(__name__)


def _get_zoho():
    connector = registry.get("zoho")
    if not connector._authenticated:
        connector.authenticate()
    return connector


def _safe_execute(fn) -> dict:
    try:
        result = fn()
        return {"success": True, "data": result}
    except AuthenticationError as e:
        return {
            "success": False,
            "error": "authentication_required",
            "message": str(e),
            "next_step": "Use zoho_authenticate tool to start the OAuth flow.",
        }
    except ConnectorError as e:
        return {"success": False, "error": "connector_error", "message": str(e)}
    except Exception as e:
        logger.exception("Unexpected error in Zoho tool")
        return {"success": False, "error": "unexpected_error", "message": str(e)}


# ------------------------------------------------------------------
# Auth tools
# ------------------------------------------------------------------

def zoho_authenticate(params: dict) -> dict:
    """Start Zoho OAuth2 flow (covers CRM + Books). Browser opens automatically."""
    connector = registry.get("zoho")
    return _safe_execute(connector.authenticate)


def zoho_get_auth_url(params: dict) -> dict:
    connector = registry.get("zoho")
    return {"success": True, "data": {"url": connector.get_auth_url()}}


def zoho_exchange_code(params: dict) -> dict:
    code = params.get("code")
    if not code:
        return {"success": False, "error": "missing_param", "message": "'code' required"}
    connector = registry.get("zoho")
    return _safe_execute(lambda: connector.exchange_code(code))


def zoho_service_status(params: dict) -> dict:
    """Check which Zoho services (CRM, Books) are available for this account."""
    connector = registry.get("zoho")
    status = connector.get_service_status()
    messages = []
    if status.get("crm_available"):
        messages.append("Zoho CRM connected successfully.")
    else:
        messages.append("Zoho CRM not available for this account.")
    if status.get("books_available"):
        messages.append("Zoho Books connected successfully.")
    else:
        messages.append("Zoho Books not available for this account.")
    return {"success": True, "data": {**status, "messages": messages}}


# ------------------------------------------------------------------
# CRM tools
# ------------------------------------------------------------------

def get_zoho_leads(params: dict) -> dict:
    """Fetch leads from Zoho CRM. Params: {limit, page, fields}"""
    return _safe_execute(lambda: _get_zoho().get_leads(
        limit=int(params.get("limit", 20)),
        page=int(params.get("page", 1)),
        fields=params.get("fields"),
    ))


def get_zoho_contacts(params: dict) -> dict:
    """Fetch contacts from Zoho CRM. Params: {limit, page, fields}"""
    return _safe_execute(lambda: _get_zoho().get_contacts(
        limit=int(params.get("limit", 20)),
        page=int(params.get("page", 1)),
        fields=params.get("fields"),
    ))


def get_zoho_accounts(params: dict) -> dict:
    """Fetch accounts from Zoho CRM. Params: {limit}"""
    return _safe_execute(lambda: _get_zoho().get_accounts(
        limit=int(params.get("limit", 20))
    ))


def search_zoho_leads(params: dict) -> dict:
    """Search Zoho CRM leads. Params: {criteria} e.g. 'Email:equals:x@y.com'"""
    criteria = params.get("criteria")
    if not criteria:
        return {"success": False, "error": "missing_param", "message": "'criteria' required"}
    return _safe_execute(lambda: _get_zoho().search_leads(criteria=criteria))


# ------------------------------------------------------------------
# Books tools
# ------------------------------------------------------------------

def get_zoho_invoices(params: dict) -> dict:
    """Fetch invoices from Zoho Books. Params: {limit, page, status}
    status: draft | sent | overdue | paid | void | unpaid | partially_paid | viewed"""
    return _safe_execute(lambda: _get_zoho().get_invoices(
        limit=int(params.get("limit", 20)),
        page=int(params.get("page", 1)),
        status=params.get("status"),
    ))


def get_zoho_bills(params: dict) -> dict:
    """Fetch bills (payables) from Zoho Books. Params: {limit, page, status}"""
    return _safe_execute(lambda: _get_zoho().get_bills(
        limit=int(params.get("limit", 20)),
        page=int(params.get("page", 1)),
        status=params.get("status"),
    ))


def get_zoho_organizations(params: dict) -> dict:
    """Fetch Zoho Books organizations linked to this account."""
    return _safe_execute(lambda: _get_zoho().get_organizations())


def get_zoho_customers(params: dict) -> dict:
    """Fetch customers from Zoho Books. Params: {limit, page}"""
    return _safe_execute(lambda: _get_zoho().get_customers(
        limit=int(params.get("limit", 20)),
        page=int(params.get("page", 1)),
    ))


def get_zoho_vendors(params: dict) -> dict:
    """Fetch vendors from Zoho Books. Params: {limit, page}"""
    return _safe_execute(lambda: _get_zoho().get_vendors(
        limit=int(params.get("limit", 20)),
        page=int(params.get("page", 1)),
    ))


# ------------------------------------------------------------------
# Tool manifest
# ------------------------------------------------------------------

ZOHO_TOOLS = [
    # Auth
    {
        "name": "zoho_authenticate",
        "description": "Start Zoho OAuth2 authentication (covers CRM + Books). Browser opens automatically — no manual input.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "fn": zoho_authenticate,
    },
    {
        "name": "zoho_service_status",
        "description": "Check which Zoho services are available: CRM and/or Books.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "fn": zoho_service_status,
    },
    {
        "name": "zoho_get_auth_url",
        "description": "Get the Zoho OAuth URL for manual/headless setup.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "fn": zoho_get_auth_url,
    },
    {
        "name": "zoho_exchange_code",
        "description": "Exchange an OAuth code for tokens (headless flow only).",
        "input_schema": {
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
        },
        "fn": zoho_exchange_code,
    },
    # CRM
    {
        "name": "get_zoho_leads",
        "description": "Fetch leads from Zoho CRM.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 20},
                "page": {"type": "integer", "default": 1},
                "fields": {"type": "array", "items": {"type": "string"}},
            },
            "required": [],
        },
        "fn": get_zoho_leads,
    },
    {
        "name": "get_zoho_contacts",
        "description": "Fetch contacts from Zoho CRM.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 20},
                "page": {"type": "integer", "default": 1},
                "fields": {"type": "array", "items": {"type": "string"}},
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
            "properties": {"limit": {"type": "integer", "default": 20}},
            "required": [],
        },
        "fn": get_zoho_accounts,
    },
    {
        "name": "search_zoho_leads",
        "description": "Search Zoho CRM leads by criteria e.g. 'Email:equals:x@y.com'.",
        "input_schema": {
            "type": "object",
            "properties": {"criteria": {"type": "string"}},
            "required": ["criteria"],
        },
        "fn": search_zoho_leads,
    },
    # Books
    {
        "name": "get_zoho_invoices",
        "description": "Fetch invoices from Zoho Books. Filter by status: draft, sent, overdue, paid, void.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 20},
                "page": {"type": "integer", "default": 1},
                "status": {"type": "string", "description": "draft | sent | overdue | paid | void"},
            },
            "required": [],
        },
        "fn": get_zoho_invoices,
    },
    {
        "name": "get_zoho_bills",
        "description": "Fetch bills (payables) from Zoho Books.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 20},
                "page": {"type": "integer", "default": 1},
                "status": {"type": "string"},
            },
            "required": [],
        },
        "fn": get_zoho_bills,
    },
    {
        "name": "get_zoho_organizations",
        "description": "List Zoho Books organizations linked to this account.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "fn": get_zoho_organizations,
    },
    {
        "name": "get_zoho_customers",
        "description": "Fetch customers from Zoho Books.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 20},
                "page": {"type": "integer", "default": 1},
            },
            "required": [],
        },
        "fn": get_zoho_customers,
    },
    {
        "name": "get_zoho_vendors",
        "description": "Fetch vendors from Zoho Books.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 20},
                "page": {"type": "integer", "default": 1},
            },
            "required": [],
        },
        "fn": get_zoho_vendors,
    },
]
