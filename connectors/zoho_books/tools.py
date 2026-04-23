"""
Zoho Books MCP tools — all 51 tools exposed to Claude Desktop.

Indian accounting defaults applied throughout:
  GST: 18%  |  TDS: 10%  |  Currency: INR  |  Region: India (zoho.in)

IMPORTANT: GST 18% and TDS 10% are demo defaults only.
Verify all tax figures with your accountant before real filings.
"""
import logging
from registry.connector_registry import registry
from connectors.base_connector import ConnectorError, AuthenticationError

logger = logging.getLogger(__name__)

_ORG_PROP = {
    "organization_id": {
        "type": "string",
        "description": "Zoho Books organization ID. Omit to use the first/cached organization.",
    }
}
_LINE_ITEMS_PROP = {
    "line_items": {
        "type": "array",
        "description": (
            "List of line items. Each item: {item_id?, name?, description?, rate, quantity, "
            "tax_id?, unit?}. Rate in INR by default."
        ),
        "items": {"type": "object"},
    }
}


def _get_books():
    return registry.get("zoho_books")


def _safe(fn) -> dict:
    try:
        result = fn()
        if isinstance(result, dict) and "success" in result:
            return result
        return {"success": True, "data": result}
    except AuthenticationError as e:
        return {
            "success": False,
            "error": "authentication_required",
            "message": str(e),
            "next_step": "Use the zoho_books_authenticate tool to log in.",
        }
    except ConnectorError as e:
        return {"success": False, "error": "connector_error", "message": str(e)}
    except Exception as e:
        logger.exception("Unexpected error in Zoho Books tool")
        return {"success": False, "error": "unexpected_error", "message": str(e)}


# ===========================================================================
# Auth & Status (tools 50-51)
# ===========================================================================

def zoho_books_authenticate(params: dict) -> dict:
    """Authenticate with Zoho Books via OAuth (opens browser)."""
    return _safe(lambda: _get_books().authenticate())


def zoho_books_connection_status(params: dict) -> dict:
    """Check Zoho Books connection status and Indian accounting defaults."""
    return _safe(lambda: _get_books().connection_status())


# ===========================================================================
# Organizations (tools 27, 40)
# ===========================================================================

def zoho_books_list_organizations(params: dict) -> dict:
    """List all Zoho Books organizations accessible with your account."""
    return _safe(lambda: _get_books().list_organizations())


def zoho_books_get_organization(params: dict) -> dict:
    """Get details of a specific Zoho Books organization."""
    org_id = params.get("organization_id", "")
    if not org_id:
        return {"success": False, "error": "missing_param", "message": "'organization_id' is required"}
    return _safe(lambda: _get_books().get_organization(org_id))


# ===========================================================================
# Contacts (tools 2, 4, 19, 43, 44)
# ===========================================================================

def zoho_books_list_contacts(params: dict) -> dict:
    """List contacts (customers and/or vendors) from Zoho Books."""
    return _safe(lambda: _get_books().list_contacts(
        organization_id=params.get("organization_id"),
        contact_type=params.get("contact_type"),
        limit=int(params.get("limit", 25)),
    ))


def zoho_books_get_contact(params: dict) -> dict:
    """Get details of a specific contact by ID."""
    cid = params.get("contact_id", "")
    if not cid:
        return {"success": False, "error": "missing_param", "message": "'contact_id' is required"}
    return _safe(lambda: _get_books().get_contact(cid, params.get("organization_id")))


def zoho_books_create_contact(params: dict) -> dict:
    """Create a new contact (customer or vendor) with Indian GST defaults."""
    name = params.get("contact_name", "")
    if not name:
        return {"success": False, "error": "missing_param", "message": "'contact_name' is required"}
    fields = {k: v for k, v in params.items() if k not in ("contact_name", "organization_id")}
    return _safe(lambda: _get_books().create_contact(
        name, params.get("organization_id"), **fields
    ))


def zoho_books_update_contact(params: dict) -> dict:
    """Update an existing contact. Pass any Zoho Books contact fields to update."""
    cid = params.get("contact_id", "")
    if not cid:
        return {"success": False, "error": "missing_param", "message": "'contact_id' is required"}
    fields = {k: v for k, v in params.items() if k not in ("contact_id", "organization_id")}
    return _safe(lambda: _get_books().update_contact(
        cid, params.get("organization_id"), **fields
    ))


def zoho_books_delete_contact(params: dict) -> dict:
    """Delete a contact by ID."""
    cid = params.get("contact_id", "")
    if not cid:
        return {"success": False, "error": "missing_param", "message": "'contact_id' is required"}
    return _safe(lambda: _get_books().delete_contact(cid, params.get("organization_id")))


# ===========================================================================
# Invoices (tools 6, 13, 37, 38, 49)
# ===========================================================================

def zoho_books_list_invoices(params: dict) -> dict:
    """List invoices from Zoho Books. Filter by status: draft|sent|overdue|paid|void."""
    return _safe(lambda: _get_books().list_invoices(
        organization_id=params.get("organization_id"),
        status=params.get("status"),
        limit=int(params.get("limit", 25)),
    ))


def zoho_books_get_invoice(params: dict) -> dict:
    """Get details of a specific invoice by ID."""
    iid = params.get("invoice_id", "")
    if not iid:
        return {"success": False, "error": "missing_param", "message": "'invoice_id' is required"}
    return _safe(lambda: _get_books().get_invoice(iid, params.get("organization_id")))


def zoho_books_create_invoice(params: dict) -> dict:
    """Create an invoice in Zoho Books. Defaults: currency INR, GST 18% (demo default)."""
    cid = params.get("customer_id", "")
    if not cid:
        return {"success": False, "error": "missing_param", "message": "'customer_id' is required"}
    line_items = params.get("line_items")
    if not line_items:
        return {"success": False, "error": "missing_param", "message": "'line_items' is required"}
    fields = {k: v for k, v in params.items() if k not in ("customer_id", "line_items", "organization_id")}
    return _safe(lambda: _get_books().create_invoice(
        cid, line_items, params.get("organization_id"), **fields
    ))


def zoho_books_update_invoice(params: dict) -> dict:
    """Update an existing invoice. Pass any Zoho Books invoice fields to update."""
    iid = params.get("invoice_id", "")
    if not iid:
        return {"success": False, "error": "missing_param", "message": "'invoice_id' is required"}
    fields = {k: v for k, v in params.items() if k not in ("invoice_id", "organization_id")}
    return _safe(lambda: _get_books().update_invoice(
        iid, params.get("organization_id"), **fields
    ))


def zoho_books_delete_invoice(params: dict) -> dict:
    """Delete an invoice by ID."""
    iid = params.get("invoice_id", "")
    if not iid:
        return {"success": False, "error": "missing_param", "message": "'invoice_id' is required"}
    return _safe(lambda: _get_books().delete_invoice(iid, params.get("organization_id")))


# ===========================================================================
# Estimates (tools 12, 14, 25, 26, 36)
# ===========================================================================

def zoho_books_list_estimates(params: dict) -> dict:
    """List estimates from Zoho Books. Filter by status: draft|sent|accepted|declined|invoiced."""
    return _safe(lambda: _get_books().list_estimates(
        organization_id=params.get("organization_id"),
        status=params.get("status"),
        limit=int(params.get("limit", 25)),
    ))


def zoho_books_get_estimate(params: dict) -> dict:
    """Get details of a specific estimate by ID."""
    eid = params.get("estimate_id", "")
    if not eid:
        return {"success": False, "error": "missing_param", "message": "'estimate_id' is required"}
    return _safe(lambda: _get_books().get_estimate(eid, params.get("organization_id")))


def zoho_books_create_estimate(params: dict) -> dict:
    """Create an estimate (quote) in Zoho Books. Defaults: currency INR."""
    cid = params.get("customer_id", "")
    if not cid:
        return {"success": False, "error": "missing_param", "message": "'customer_id' is required"}
    line_items = params.get("line_items")
    if not line_items:
        return {"success": False, "error": "missing_param", "message": "'line_items' is required"}
    fields = {k: v for k, v in params.items() if k not in ("customer_id", "line_items", "organization_id")}
    return _safe(lambda: _get_books().create_estimate(
        cid, line_items, params.get("organization_id"), **fields
    ))


def zoho_books_update_estimate(params: dict) -> dict:
    """Update an existing estimate. Pass any Zoho Books estimate fields to update."""
    eid = params.get("estimate_id", "")
    if not eid:
        return {"success": False, "error": "missing_param", "message": "'estimate_id' is required"}
    fields = {k: v for k, v in params.items() if k not in ("estimate_id", "organization_id")}
    return _safe(lambda: _get_books().update_estimate(
        eid, params.get("organization_id"), **fields
    ))


def zoho_books_delete_estimate(params: dict) -> dict:
    """Delete an estimate by ID."""
    eid = params.get("estimate_id", "")
    if not eid:
        return {"success": False, "error": "missing_param", "message": "'estimate_id' is required"}
    return _safe(lambda: _get_books().delete_estimate(eid, params.get("organization_id")))


# ===========================================================================
# Sales Orders (tools 9, 17, 23, 24, 29, 39)  [note: tool 24 is get_purchase_order]
# ===========================================================================

def zoho_books_list_sales_orders(params: dict) -> dict:
    """List sales orders from Zoho Books. Filter by status: draft|open|closed|void."""
    return _safe(lambda: _get_books().list_sales_orders(
        organization_id=params.get("organization_id"),
        status=params.get("status"),
        limit=int(params.get("limit", 25)),
    ))


def zoho_books_get_sales_order(params: dict) -> dict:
    """Get details of a specific sales order by ID."""
    sid = params.get("salesorder_id", "")
    if not sid:
        return {"success": False, "error": "missing_param", "message": "'salesorder_id' is required"}
    return _safe(lambda: _get_books().get_sales_order(sid, params.get("organization_id")))


def zoho_books_create_sales_order(params: dict) -> dict:
    """Create a sales order in Zoho Books. Defaults: currency INR."""
    cid = params.get("customer_id", "")
    if not cid:
        return {"success": False, "error": "missing_param", "message": "'customer_id' is required"}
    line_items = params.get("line_items")
    if not line_items:
        return {"success": False, "error": "missing_param", "message": "'line_items' is required"}
    fields = {k: v for k, v in params.items() if k not in ("customer_id", "line_items", "organization_id")}
    return _safe(lambda: _get_books().create_sales_order(
        cid, line_items, params.get("organization_id"), **fields
    ))


def zoho_books_update_sales_order(params: dict) -> dict:
    """Update an existing sales order. Pass any Zoho Books sales order fields to update."""
    sid = params.get("salesorder_id", "")
    if not sid:
        return {"success": False, "error": "missing_param", "message": "'salesorder_id' is required"}
    fields = {k: v for k, v in params.items() if k not in ("salesorder_id", "organization_id")}
    return _safe(lambda: _get_books().update_sales_order(
        sid, params.get("organization_id"), **fields
    ))


def zoho_books_delete_sales_order(params: dict) -> dict:
    """Delete a sales order by ID."""
    sid = params.get("salesorder_id", "")
    if not sid:
        return {"success": False, "error": "missing_param", "message": "'salesorder_id' is required"}
    return _safe(lambda: _get_books().delete_sales_order(sid, params.get("organization_id")))


# ===========================================================================
# Purchase Orders (tools 15, 16, 20, 24, 48)
# ===========================================================================

def zoho_books_list_purchase_orders(params: dict) -> dict:
    """List purchase orders from Zoho Books. Filter by status: draft|open|billed|cancelled."""
    return _safe(lambda: _get_books().list_purchase_orders(
        organization_id=params.get("organization_id"),
        status=params.get("status"),
        limit=int(params.get("limit", 25)),
    ))


def zoho_books_get_purchase_order(params: dict) -> dict:
    """Get details of a specific purchase order by ID."""
    pid = params.get("purchaseorder_id", "")
    if not pid:
        return {"success": False, "error": "missing_param", "message": "'purchaseorder_id' is required"}
    return _safe(lambda: _get_books().get_purchase_order(pid, params.get("organization_id")))


def zoho_books_create_purchase_order(params: dict) -> dict:
    """Create a purchase order in Zoho Books. Defaults: currency INR."""
    vid = params.get("vendor_id", "")
    if not vid:
        return {"success": False, "error": "missing_param", "message": "'vendor_id' is required"}
    line_items = params.get("line_items")
    if not line_items:
        return {"success": False, "error": "missing_param", "message": "'line_items' is required"}
    fields = {k: v for k, v in params.items() if k not in ("vendor_id", "line_items", "organization_id")}
    return _safe(lambda: _get_books().create_purchase_order(
        vid, line_items, params.get("organization_id"), **fields
    ))


def zoho_books_update_purchase_order(params: dict) -> dict:
    """Update an existing purchase order. Pass any Zoho Books purchase order fields to update."""
    pid = params.get("purchaseorder_id", "")
    if not pid:
        return {"success": False, "error": "missing_param", "message": "'purchaseorder_id' is required"}
    fields = {k: v for k, v in params.items() if k not in ("purchaseorder_id", "organization_id")}
    return _safe(lambda: _get_books().update_purchase_order(
        pid, params.get("organization_id"), **fields
    ))


def zoho_books_delete_purchase_order(params: dict) -> dict:
    """Delete a purchase order by ID."""
    pid = params.get("purchaseorder_id", "")
    if not pid:
        return {"success": False, "error": "missing_param", "message": "'purchaseorder_id' is required"}
    return _safe(lambda: _get_books().delete_purchase_order(pid, params.get("organization_id")))


# ===========================================================================
# Expenses (tools 5, 28, 30, 31, 46)
# ===========================================================================

def zoho_books_list_expenses(params: dict) -> dict:
    """List expenses from Zoho Books. Filter by status: unbilled|invoiced."""
    return _safe(lambda: _get_books().list_expenses(
        organization_id=params.get("organization_id"),
        status=params.get("status"),
        limit=int(params.get("limit", 25)),
    ))


def zoho_books_get_expense(params: dict) -> dict:
    """Get details of a specific expense by ID."""
    eid = params.get("expense_id", "")
    if not eid:
        return {"success": False, "error": "missing_param", "message": "'expense_id' is required"}
    return _safe(lambda: _get_books().get_expense(eid, params.get("organization_id")))


def zoho_books_create_expense(params: dict) -> dict:
    """Create an expense in Zoho Books. Defaults: currency INR."""
    aid = params.get("account_id", "")
    if not aid:
        return {"success": False, "error": "missing_param", "message": "'account_id' is required"}
    amt = params.get("amount")
    if amt is None:
        return {"success": False, "error": "missing_param", "message": "'amount' is required"}
    fields = {k: v for k, v in params.items() if k not in ("account_id", "amount", "organization_id")}
    return _safe(lambda: _get_books().create_expense(
        aid, float(amt), params.get("organization_id"), **fields
    ))


def zoho_books_update_expense(params: dict) -> dict:
    """Update an existing expense. Pass any Zoho Books expense fields to update."""
    eid = params.get("expense_id", "")
    if not eid:
        return {"success": False, "error": "missing_param", "message": "'expense_id' is required"}
    fields = {k: v for k, v in params.items() if k not in ("expense_id", "organization_id")}
    return _safe(lambda: _get_books().update_expense(
        eid, params.get("organization_id"), **fields
    ))


def zoho_books_delete_expense(params: dict) -> dict:
    """Delete an expense by ID."""
    eid = params.get("expense_id", "")
    if not eid:
        return {"success": False, "error": "missing_param", "message": "'expense_id' is required"}
    return _safe(lambda: _get_books().delete_expense(eid, params.get("organization_id")))


# ===========================================================================
# Items (tools 1, 8, 10, 32, 33)
# ===========================================================================

def zoho_books_list_items(params: dict) -> dict:
    """List items (products/services) from Zoho Books."""
    return _safe(lambda: _get_books().list_items(
        organization_id=params.get("organization_id"),
        limit=int(params.get("limit", 25)),
    ))


def zoho_books_get_item(params: dict) -> dict:
    """Get details of a specific item by ID."""
    iid = params.get("item_id", "")
    if not iid:
        return {"success": False, "error": "missing_param", "message": "'item_id' is required"}
    return _safe(lambda: _get_books().get_item(iid, params.get("organization_id")))


def zoho_books_create_item(params: dict) -> dict:
    """Create an item in Zoho Books. Defaults: currency INR."""
    name = params.get("name", "")
    if not name:
        return {"success": False, "error": "missing_param", "message": "'name' is required"}
    rate = params.get("rate")
    if rate is None:
        return {"success": False, "error": "missing_param", "message": "'rate' is required"}
    fields = {k: v for k, v in params.items() if k not in ("name", "rate", "organization_id")}
    return _safe(lambda: _get_books().create_item(
        name, float(rate), params.get("organization_id"), **fields
    ))


def zoho_books_update_item(params: dict) -> dict:
    """Update an existing item. Pass any Zoho Books item fields to update."""
    iid = params.get("item_id", "")
    if not iid:
        return {"success": False, "error": "missing_param", "message": "'item_id' is required"}
    fields = {k: v for k, v in params.items() if k not in ("item_id", "organization_id")}
    return _safe(lambda: _get_books().update_item(
        iid, params.get("organization_id"), **fields
    ))


def zoho_books_delete_item(params: dict) -> dict:
    """Delete an item by ID."""
    iid = params.get("item_id", "")
    if not iid:
        return {"success": False, "error": "missing_param", "message": "'item_id' is required"}
    return _safe(lambda: _get_books().delete_item(iid, params.get("organization_id")))


# ===========================================================================
# Taxes (tools 3, 11, 34, 35, 41)
# ===========================================================================

def zoho_books_list_taxes(params: dict) -> dict:
    """List all taxes configured in Zoho Books. Note: GST 18% is the demo default."""
    return _safe(lambda: _get_books().list_taxes(params.get("organization_id")))


def zoho_books_get_tax(params: dict) -> dict:
    """Get details of a specific tax by ID."""
    tid = params.get("tax_id", "")
    if not tid:
        return {"success": False, "error": "missing_param", "message": "'tax_id' is required"}
    return _safe(lambda: _get_books().get_tax(tid, params.get("organization_id")))


def zoho_books_create_tax(params: dict) -> dict:
    """Create a tax entry. Default tax_percentage=18 (GST demo default — verify before use)."""
    name = params.get("tax_name", "")
    if not name:
        return {"success": False, "error": "missing_param", "message": "'tax_name' is required"}
    pct = params.get("tax_percentage")
    fields = {k: v for k, v in params.items()
              if k not in ("tax_name", "tax_percentage", "organization_id")}
    return _safe(lambda: _get_books().create_tax(
        name,
        params.get("organization_id"),
        float(pct) if pct is not None else None,
        **fields,
    ))


def zoho_books_update_tax(params: dict) -> dict:
    """Update an existing tax entry. Pass any Zoho Books tax fields to update."""
    tid = params.get("tax_id", "")
    if not tid:
        return {"success": False, "error": "missing_param", "message": "'tax_id' is required"}
    fields = {k: v for k, v in params.items() if k not in ("tax_id", "organization_id")}
    return _safe(lambda: _get_books().update_tax(
        tid, params.get("organization_id"), **fields
    ))


def zoho_books_delete_tax(params: dict) -> dict:
    """Delete a tax entry by ID."""
    tid = params.get("tax_id", "")
    if not tid:
        return {"success": False, "error": "missing_param", "message": "'tax_id' is required"}
    return _safe(lambda: _get_books().delete_tax(tid, params.get("organization_id")))


# ===========================================================================
# Customer Payments (tools 18, 22, 42, 45, 47)
# ===========================================================================

def zoho_books_list_customer_payments(params: dict) -> dict:
    """List customer payments recorded in Zoho Books."""
    return _safe(lambda: _get_books().list_customer_payments(
        organization_id=params.get("organization_id"),
        limit=int(params.get("limit", 25)),
    ))


def zoho_books_get_customer_payment(params: dict) -> dict:
    """Get details of a specific customer payment by ID."""
    pid = params.get("payment_id", "")
    if not pid:
        return {"success": False, "error": "missing_param", "message": "'payment_id' is required"}
    return _safe(lambda: _get_books().get_customer_payment(pid, params.get("organization_id")))


def zoho_books_create_customer_payment(params: dict) -> dict:
    """Record a customer payment in Zoho Books. Defaults: currency INR."""
    cid = params.get("customer_id", "")
    if not cid:
        return {"success": False, "error": "missing_param", "message": "'customer_id' is required"}
    amt = params.get("amount")
    if amt is None:
        return {"success": False, "error": "missing_param", "message": "'amount' is required"}
    fields = {k: v for k, v in params.items() if k not in ("customer_id", "amount", "organization_id")}
    return _safe(lambda: _get_books().create_customer_payment(
        cid, float(amt), params.get("organization_id"), **fields
    ))


def zoho_books_update_customer_payment(params: dict) -> dict:
    """Update an existing customer payment. Pass any Zoho Books payment fields to update."""
    pid = params.get("payment_id", "")
    if not pid:
        return {"success": False, "error": "missing_param", "message": "'payment_id' is required"}
    fields = {k: v for k, v in params.items() if k not in ("payment_id", "organization_id")}
    return _safe(lambda: _get_books().update_customer_payment(
        pid, params.get("organization_id"), **fields
    ))


def zoho_books_delete_customer_payment(params: dict) -> dict:
    """Delete a customer payment record by ID."""
    pid = params.get("payment_id", "")
    if not pid:
        return {"success": False, "error": "missing_param", "message": "'payment_id' is required"}
    return _safe(lambda: _get_books().delete_customer_payment(
        pid, params.get("organization_id")
    ))


# ===========================================================================
# Users (tools 7, 21)
# ===========================================================================

def zoho_books_list_users(params: dict) -> dict:
    """List all users in the Zoho Books organization."""
    return _safe(lambda: _get_books().list_users(params.get("organization_id")))


def zoho_books_get_user(params: dict) -> dict:
    """Get details of a specific user by ID."""
    uid = params.get("user_id", "")
    if not uid:
        return {"success": False, "error": "missing_param", "message": "'user_id' is required"}
    return _safe(lambda: _get_books().get_user(uid, params.get("organization_id")))


# ===========================================================================
# Tool registry — all 51 tools
# ===========================================================================

ZOHO_BOOKS_TOOLS = [
    # ---- Auth & Status ----
    {
        "name": "zoho_books_authenticate",
        "description": "Authenticate with Zoho Books. Opens your browser for OAuth login. Run this first.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "fn": zoho_books_authenticate,
    },
    {
        "name": "zoho_books_connection_status",
        "description": "Check Zoho Books connection status and view Indian accounting defaults (GST 18%, TDS 10%, INR).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "fn": zoho_books_connection_status,
    },
    # ---- Organizations ----
    {
        "name": "zoho_books_list_organizations",
        "description": "List all Zoho Books organizations on this account.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "fn": zoho_books_list_organizations,
    },
    {
        "name": "zoho_books_get_organization",
        "description": "Get details of a specific Zoho Books organization.",
        "input_schema": {
            "type": "object",
            "properties": {"organization_id": {"type": "string"}},
            "required": ["organization_id"],
        },
        "fn": zoho_books_get_organization,
    },
    # ---- Contacts ----
    {
        "name": "zoho_books_list_contacts",
        "description": "List contacts from Zoho Books. Use contact_type='customer' or 'vendor' to filter.",
        "input_schema": {
            "type": "object",
            "properties": {
                **_ORG_PROP,
                "contact_type": {"type": "string", "enum": ["customer", "vendor"], "description": "Filter by contact type"},
                "limit": {"type": "integer", "default": 25},
            },
            "required": [],
        },
        "fn": zoho_books_list_contacts,
    },
    {
        "name": "zoho_books_get_contact",
        "description": "Get details of a specific contact by ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact_id": {"type": "string"},
                **_ORG_PROP,
            },
            "required": ["contact_id"],
        },
        "fn": zoho_books_get_contact,
    },
    {
        "name": "zoho_books_create_contact",
        "description": "Create a contact. Never guess gst_no, currency, or place_of_contact — ask the user. Use zoho_books_list_contacts first to avoid duplicates. Show a draft summary and ask for confirmation before creating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact_name": {"type": "string"},
                "contact_type": {"type": "string", "enum": ["customer", "vendor"]},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "gst_treatment": {"type": "string", "default": "business_gst"},
                "gst_no": {"type": "string"},
                "currency_code": {"type": "string", "default": "INR"},
                "place_of_contact": {"type": "string", "description": "State code e.g. MH, KA, DL"},
                **_ORG_PROP,
            },
            "required": ["contact_name"],
        },
        "fn": zoho_books_create_contact,
    },
    {
        "name": "zoho_books_update_contact",
        "description": "Update a contact. Never guess contact_id — use zoho_books_list_contacts to find it first. Never reuse an ID from a prior turn without looking it up again. Show proposed changes and ask for confirmation before updating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact_id": {"type": "string"},
                "contact_name": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "gst_treatment": {"type": "string"},
                "gst_no": {"type": "string"},
                **_ORG_PROP,
            },
            "required": ["contact_id"],
        },
        "fn": zoho_books_update_contact,
    },
    {
        "name": "zoho_books_delete_contact",
        "description": "Delete a contact. Irreversible. Never guess contact_id — use zoho_books_list_contacts to confirm the record first. Show record details and ask for explicit confirmation before deleting.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact_id": {"type": "string"},
                **_ORG_PROP,
            },
            "required": ["contact_id"],
        },
        "fn": zoho_books_delete_contact,
    },
    # ---- Invoices ----
    {
        "name": "zoho_books_list_invoices",
        "description": "List invoices from Zoho Books. Filter by status: draft|sent|overdue|paid|void.",
        "input_schema": {
            "type": "object",
            "properties": {
                **_ORG_PROP,
                "status": {"type": "string", "enum": ["draft", "sent", "overdue", "paid", "void"]},
                "limit": {"type": "integer", "default": 25},
            },
            "required": [],
        },
        "fn": zoho_books_list_invoices,
    },
    {
        "name": "zoho_books_get_invoice",
        "description": "Get details of a specific invoice by ID.",
        "input_schema": {
            "type": "object",
            "properties": {"invoice_id": {"type": "string"}, **_ORG_PROP},
            "required": ["invoice_id"],
        },
        "fn": zoho_books_get_invoice,
    },
    {
        "name": "zoho_books_create_invoice",
        "description": "Create an invoice. Never guess customer_id, item_id, or tax_id. Use zoho_books_list_contacts for customer_id, zoho_books_list_items for item IDs, zoho_books_list_taxes for tax_id. Ask for date, due date, and line items explicitly. Show a draft summary and ask for confirmation before creating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                **_LINE_ITEMS_PROP,
                "date": {"type": "string", "description": "Invoice date YYYY-MM-DD"},
                "due_date": {"type": "string"},
                "currency_code": {"type": "string", "default": "INR"},
                "notes": {"type": "string"},
                "terms": {"type": "string"},
                **_ORG_PROP,
            },
            "required": ["customer_id", "line_items"],
        },
        "fn": zoho_books_create_invoice,
    },
    {
        "name": "zoho_books_update_invoice",
        "description": "Update an invoice. Never guess invoice_id, item_id, or tax_id — look them up first. Never reuse IDs from a prior turn without verifying. Show proposed changes and ask for confirmation before updating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "string"},
                "due_date": {"type": "string"},
                "notes": {"type": "string"},
                **_LINE_ITEMS_PROP,
                **_ORG_PROP,
            },
            "required": ["invoice_id"],
        },
        "fn": zoho_books_update_invoice,
    },
    {
        "name": "zoho_books_delete_invoice",
        "description": "Delete an invoice. Irreversible. Never guess invoice_id — use zoho_books_get_invoice or zoho_books_list_invoices to confirm the record first. Show invoice details and ask for explicit confirmation before deleting.",
        "input_schema": {
            "type": "object",
            "properties": {"invoice_id": {"type": "string"}, **_ORG_PROP},
            "required": ["invoice_id"],
        },
        "fn": zoho_books_delete_invoice,
    },
    # ---- Estimates ----
    {
        "name": "zoho_books_list_estimates",
        "description": "List estimates (quotes) from Zoho Books. Filter by status: draft|sent|accepted|declined|invoiced.",
        "input_schema": {
            "type": "object",
            "properties": {
                **_ORG_PROP,
                "status": {"type": "string"},
                "limit": {"type": "integer", "default": 25},
            },
            "required": [],
        },
        "fn": zoho_books_list_estimates,
    },
    {
        "name": "zoho_books_get_estimate",
        "description": "Get details of a specific estimate by ID.",
        "input_schema": {
            "type": "object",
            "properties": {"estimate_id": {"type": "string"}, **_ORG_PROP},
            "required": ["estimate_id"],
        },
        "fn": zoho_books_get_estimate,
    },
    {
        "name": "zoho_books_create_estimate",
        "description": "Create an estimate (quote). Never guess customer_id, item_id, or tax_id. Use zoho_books_list_contacts, zoho_books_list_items, and zoho_books_list_taxes to find IDs. Ask for dates and line items. Show a draft summary and ask for confirmation before creating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                **_LINE_ITEMS_PROP,
                "date": {"type": "string"},
                "expiry_date": {"type": "string"},
                "currency_code": {"type": "string", "default": "INR"},
                **_ORG_PROP,
            },
            "required": ["customer_id", "line_items"],
        },
        "fn": zoho_books_create_estimate,
    },
    {
        "name": "zoho_books_update_estimate",
        "description": "Update an estimate. Never guess estimate_id, item_id, or tax_id — look them up first. Show proposed changes and ask for confirmation before updating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "estimate_id": {"type": "string"},
                "expiry_date": {"type": "string"},
                **_LINE_ITEMS_PROP,
                **_ORG_PROP,
            },
            "required": ["estimate_id"],
        },
        "fn": zoho_books_update_estimate,
    },
    {
        "name": "zoho_books_delete_estimate",
        "description": "Delete an estimate. Never guess estimate_id — confirm the record with zoho_books_get_estimate first. Show details and ask for explicit confirmation before deleting.",
        "input_schema": {
            "type": "object",
            "properties": {"estimate_id": {"type": "string"}, **_ORG_PROP},
            "required": ["estimate_id"],
        },
        "fn": zoho_books_delete_estimate,
    },
    # ---- Sales Orders ----
    {
        "name": "zoho_books_list_sales_orders",
        "description": "List sales orders from Zoho Books. Filter by status: draft|open|closed|void.",
        "input_schema": {
            "type": "object",
            "properties": {
                **_ORG_PROP,
                "status": {"type": "string"},
                "limit": {"type": "integer", "default": 25},
            },
            "required": [],
        },
        "fn": zoho_books_list_sales_orders,
    },
    {
        "name": "zoho_books_get_sales_order",
        "description": "Get details of a specific sales order by ID.",
        "input_schema": {
            "type": "object",
            "properties": {"salesorder_id": {"type": "string"}, **_ORG_PROP},
            "required": ["salesorder_id"],
        },
        "fn": zoho_books_get_sales_order,
    },
    {
        "name": "zoho_books_create_sales_order",
        "description": "Create a sales order. Never guess customer_id, item_id, or tax_id. Use zoho_books_list_contacts, zoho_books_list_items, and zoho_books_list_taxes to find IDs. Ask for dates and line items. Show a draft summary and ask for confirmation before creating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                **_LINE_ITEMS_PROP,
                "date": {"type": "string"},
                "currency_code": {"type": "string", "default": "INR"},
                **_ORG_PROP,
            },
            "required": ["customer_id", "line_items"],
        },
        "fn": zoho_books_create_sales_order,
    },
    {
        "name": "zoho_books_update_sales_order",
        "description": "Update a sales order. Never guess salesorder_id, item_id, or tax_id — look them up first. Show proposed changes and ask for confirmation before updating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "salesorder_id": {"type": "string"},
                **_LINE_ITEMS_PROP,
                **_ORG_PROP,
            },
            "required": ["salesorder_id"],
        },
        "fn": zoho_books_update_sales_order,
    },
    {
        "name": "zoho_books_delete_sales_order",
        "description": "Delete a sales order. Never guess salesorder_id — confirm the record first. Show details and ask for explicit confirmation before deleting.",
        "input_schema": {
            "type": "object",
            "properties": {"salesorder_id": {"type": "string"}, **_ORG_PROP},
            "required": ["salesorder_id"],
        },
        "fn": zoho_books_delete_sales_order,
    },
    # ---- Purchase Orders ----
    {
        "name": "zoho_books_list_purchase_orders",
        "description": "List purchase orders from Zoho Books. Filter by status: draft|open|billed|cancelled.",
        "input_schema": {
            "type": "object",
            "properties": {
                **_ORG_PROP,
                "status": {"type": "string"},
                "limit": {"type": "integer", "default": 25},
            },
            "required": [],
        },
        "fn": zoho_books_list_purchase_orders,
    },
    {
        "name": "zoho_books_get_purchase_order",
        "description": "Get details of a specific purchase order by ID.",
        "input_schema": {
            "type": "object",
            "properties": {"purchaseorder_id": {"type": "string"}, **_ORG_PROP},
            "required": ["purchaseorder_id"],
        },
        "fn": zoho_books_get_purchase_order,
    },
    {
        "name": "zoho_books_create_purchase_order",
        "description": "Create a purchase order. Never guess vendor_id, item_id, or tax_id. Use zoho_books_list_contacts (vendor type) for vendor_id, zoho_books_list_items for item IDs, zoho_books_list_taxes for tax_id. Show a draft summary and ask for confirmation before creating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "vendor_id": {"type": "string"},
                **_LINE_ITEMS_PROP,
                "date": {"type": "string"},
                "currency_code": {"type": "string", "default": "INR"},
                **_ORG_PROP,
            },
            "required": ["vendor_id", "line_items"],
        },
        "fn": zoho_books_create_purchase_order,
    },
    {
        "name": "zoho_books_update_purchase_order",
        "description": "Update a purchase order. Never guess purchaseorder_id, item_id, or tax_id — look them up first. Show proposed changes and ask for confirmation before updating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "purchaseorder_id": {"type": "string"},
                **_LINE_ITEMS_PROP,
                **_ORG_PROP,
            },
            "required": ["purchaseorder_id"],
        },
        "fn": zoho_books_update_purchase_order,
    },
    {
        "name": "zoho_books_delete_purchase_order",
        "description": "Delete a purchase order. Never guess purchaseorder_id — confirm the record first. Show details and ask for explicit confirmation before deleting.",
        "input_schema": {
            "type": "object",
            "properties": {"purchaseorder_id": {"type": "string"}, **_ORG_PROP},
            "required": ["purchaseorder_id"],
        },
        "fn": zoho_books_delete_purchase_order,
    },
    # ---- Expenses ----
    {
        "name": "zoho_books_list_expenses",
        "description": "List expenses from Zoho Books. Filter by status: unbilled|invoiced.",
        "input_schema": {
            "type": "object",
            "properties": {
                **_ORG_PROP,
                "status": {"type": "string"},
                "limit": {"type": "integer", "default": 25},
            },
            "required": [],
        },
        "fn": zoho_books_list_expenses,
    },
    {
        "name": "zoho_books_get_expense",
        "description": "Get details of a specific expense by ID.",
        "input_schema": {
            "type": "object",
            "properties": {"expense_id": {"type": "string"}, **_ORG_PROP},
            "required": ["expense_id"],
        },
        "fn": zoho_books_get_expense,
    },
    {
        "name": "zoho_books_create_expense",
        "description": "Record an expense. Never guess account_id or vendor_id — ask the user for the expense account and use zoho_books_list_contacts for vendor_id if needed. Ask for date, amount, and description explicitly. Show a draft summary and ask for confirmation before recording.",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Expense account ID from Zoho Books chart of accounts"},
                "amount": {"type": "number"},
                "date": {"type": "string", "description": "Expense date YYYY-MM-DD"},
                "currency_code": {"type": "string", "default": "INR"},
                "description": {"type": "string"},
                "vendor_id": {"type": "string"},
                **_ORG_PROP,
            },
            "required": ["account_id", "amount"],
        },
        "fn": zoho_books_create_expense,
    },
    {
        "name": "zoho_books_update_expense",
        "description": "Update an expense. Never guess expense_id or account_id — use zoho_books_get_expense to confirm the record first. Show proposed changes and ask for confirmation before updating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expense_id": {"type": "string"},
                "amount": {"type": "number"},
                "description": {"type": "string"},
                **_ORG_PROP,
            },
            "required": ["expense_id"],
        },
        "fn": zoho_books_update_expense,
    },
    {
        "name": "zoho_books_delete_expense",
        "description": "Delete an expense. Never guess expense_id — use zoho_books_get_expense to confirm the record first. Show details and ask for explicit confirmation before deleting.",
        "input_schema": {
            "type": "object",
            "properties": {"expense_id": {"type": "string"}, **_ORG_PROP},
            "required": ["expense_id"],
        },
        "fn": zoho_books_delete_expense,
    },
    # ---- Items ----
    {
        "name": "zoho_books_list_items",
        "description": "List items (products/services) from Zoho Books.",
        "input_schema": {
            "type": "object",
            "properties": {**_ORG_PROP, "limit": {"type": "integer", "default": 25}},
            "required": [],
        },
        "fn": zoho_books_list_items,
    },
    {
        "name": "zoho_books_get_item",
        "description": "Get details of a specific item by ID.",
        "input_schema": {
            "type": "object",
            "properties": {"item_id": {"type": "string"}, **_ORG_PROP},
            "required": ["item_id"],
        },
        "fn": zoho_books_get_item,
    },
    {
        "name": "zoho_books_create_item",
        "description": "Create an item (product/service). Never guess tax_id — use zoho_books_list_taxes to find the correct GST rate. Ask for name, rate, and unit explicitly. Show a draft summary and ask for confirmation before creating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "rate": {"type": "number", "description": "Price in INR"},
                "description": {"type": "string"},
                "sku": {"type": "string"},
                "unit": {"type": "string"},
                "tax_id": {"type": "string", "description": "Tax ID from zoho_books_list_taxes"},
                "currency_code": {"type": "string", "default": "INR"},
                **_ORG_PROP,
            },
            "required": ["name", "rate"],
        },
        "fn": zoho_books_create_item,
    },
    {
        "name": "zoho_books_update_item",
        "description": "Update an item. Never guess item_id or tax_id — use zoho_books_list_items and zoho_books_list_taxes first. Show proposed changes and ask for confirmation before updating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "item_id": {"type": "string"},
                "name": {"type": "string"},
                "rate": {"type": "number"},
                "description": {"type": "string"},
                "tax_id": {"type": "string"},
                **_ORG_PROP,
            },
            "required": ["item_id"],
        },
        "fn": zoho_books_update_item,
    },
    {
        "name": "zoho_books_delete_item",
        "description": "Delete an item. Never guess item_id — use zoho_books_list_items to confirm the record first. Show details and ask for explicit confirmation before deleting.",
        "input_schema": {
            "type": "object",
            "properties": {"item_id": {"type": "string"}, **_ORG_PROP},
            "required": ["item_id"],
        },
        "fn": zoho_books_delete_item,
    },
    # ---- Taxes ----
    {
        "name": "zoho_books_list_taxes",
        "description": "List all taxes configured in Zoho Books. Default GST assumption: 18% (demo value — verify).",
        "input_schema": {
            "type": "object",
            "properties": {**_ORG_PROP},
            "required": [],
        },
        "fn": zoho_books_list_taxes,
    },
    {
        "name": "zoho_books_get_tax",
        "description": "Get details of a specific tax by ID.",
        "input_schema": {
            "type": "object",
            "properties": {"tax_id": {"type": "string"}, **_ORG_PROP},
            "required": ["tax_id"],
        },
        "fn": zoho_books_get_tax,
    },
    {
        "name": "zoho_books_create_tax",
        "description": "Create a tax entry. Never guess the tax percentage — ask the user for the exact rate and confirm with their accountant. Ask for tax_name and tax_type. Show a draft and ask for confirmation before creating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tax_name": {"type": "string"},
                "tax_percentage": {"type": "number", "description": "Tax % — defaults to 18 (GST demo)"},
                "tax_type": {"type": "string", "description": "e.g. tax, compound_tax"},
                **_ORG_PROP,
            },
            "required": ["tax_name"],
        },
        "fn": zoho_books_create_tax,
    },
    {
        "name": "zoho_books_update_tax",
        "description": "Update a tax entry. Never guess tax_id or tax_percentage — use zoho_books_list_taxes to find the record and confirm the rate with the user. Show proposed changes and ask for confirmation before updating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tax_id": {"type": "string"},
                "tax_name": {"type": "string"},
                "tax_percentage": {"type": "number"},
                **_ORG_PROP,
            },
            "required": ["tax_id"],
        },
        "fn": zoho_books_update_tax,
    },
    {
        "name": "zoho_books_delete_tax",
        "description": "Delete a tax entry. Never guess tax_id — use zoho_books_list_taxes to confirm the record first. Show details and ask for explicit confirmation before deleting.",
        "input_schema": {
            "type": "object",
            "properties": {"tax_id": {"type": "string"}, **_ORG_PROP},
            "required": ["tax_id"],
        },
        "fn": zoho_books_delete_tax,
    },
    # ---- Customer Payments ----
    {
        "name": "zoho_books_list_customer_payments",
        "description": "List customer payments recorded in Zoho Books.",
        "input_schema": {
            "type": "object",
            "properties": {**_ORG_PROP, "limit": {"type": "integer", "default": 25}},
            "required": [],
        },
        "fn": zoho_books_list_customer_payments,
    },
    {
        "name": "zoho_books_get_customer_payment",
        "description": "Get details of a specific customer payment by ID.",
        "input_schema": {
            "type": "object",
            "properties": {"payment_id": {"type": "string"}, **_ORG_PROP},
            "required": ["payment_id"],
        },
        "fn": zoho_books_get_customer_payment,
    },
    {
        "name": "zoho_books_create_customer_payment",
        "description": "Record a customer payment. Never guess customer_id, invoice_id, or payment_mode. Use zoho_books_list_contacts for customer_id. Ask for date, amount, and payment mode explicitly. Show a draft summary and ask for confirmation before recording.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "amount": {"type": "number"},
                "date": {"type": "string", "description": "Payment date YYYY-MM-DD"},
                "payment_mode": {"type": "string", "description": "e.g. cash, check, bank_transfer, upi"},
                "invoice_id": {"type": "string", "description": "Link to an invoice"},
                "currency_code": {"type": "string", "default": "INR"},
                **_ORG_PROP,
            },
            "required": ["customer_id", "amount"],
        },
        "fn": zoho_books_create_customer_payment,
    },
    {
        "name": "zoho_books_update_customer_payment",
        "description": "Update a customer payment. Never guess payment_id or payment_mode — use zoho_books_get_customer_payment to confirm the record first. Show proposed changes and ask for confirmation before updating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "payment_id": {"type": "string"},
                "amount": {"type": "number"},
                "payment_mode": {"type": "string"},
                **_ORG_PROP,
            },
            "required": ["payment_id"],
        },
        "fn": zoho_books_update_customer_payment,
    },
    {
        "name": "zoho_books_delete_customer_payment",
        "description": "Delete a customer payment. Never guess payment_id — use zoho_books_get_customer_payment to confirm the record first. Show details and ask for explicit confirmation before deleting.",
        "input_schema": {
            "type": "object",
            "properties": {"payment_id": {"type": "string"}, **_ORG_PROP},
            "required": ["payment_id"],
        },
        "fn": zoho_books_delete_customer_payment,
    },
    # ---- Users ----
    {
        "name": "zoho_books_list_users",
        "description": "List all users in the Zoho Books organization.",
        "input_schema": {
            "type": "object",
            "properties": {**_ORG_PROP},
            "required": [],
        },
        "fn": zoho_books_list_users,
    },
    {
        "name": "zoho_books_get_user",
        "description": "Get details of a specific Zoho Books user by ID.",
        "input_schema": {
            "type": "object",
            "properties": {"user_id": {"type": "string"}, **_ORG_PROP},
            "required": ["user_id"],
        },
        "fn": zoho_books_get_user,
    },
]

assert len(ZOHO_BOOKS_TOOLS) == 51, f"Expected 51 tools, got {len(ZOHO_BOOKS_TOOLS)}"
