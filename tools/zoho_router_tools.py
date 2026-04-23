"""
Customer-mode router tools for Zoho Books.

In customer mode these four tools replace the 40 zb_* report scripts and
51 raw zoho_books_list/get tools, keeping Claude Desktop's tool list short
and focused on natural-language interaction.

  recklabs_zoho_assistant   — NL query → run the right report tool
  recklabs_zoho_report      — Direct report runner by name or alias
  recklabs_zoho_capabilities — Catalog of available reports
  recklabs_zoho_action      — Operational bridge: list/find/write via hidden raw tools
"""
import importlib
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Report alias table
# Maps script module name → list of keyword phrases (lowercase).
# Sorted by phrase length at match time so longest phrase wins.
# ---------------------------------------------------------------------------

_ALIASES: dict[str, list[str]] = {
    # AR / Receivables
    "ar_aging":               [
        "ar aging", "receivables aging", "accounts receivable aging", "ar buckets",
        "receivables", "receivable", "accounts receivable", "money owed to me",
        "who owes me money", "who owes us money",
    ],
    "overdue_invoices":       ["overdue invoices", "overdue invoice", "past due invoices"],
    "outstanding_invoices":   ["outstanding invoices", "unpaid invoices", "sent invoices"],
    "draft_invoices":         ["draft invoices", "draft invoice"],
    "invoice_summary":        ["invoice summary", "invoice status", "invoices status"],
    # Contacts
    "contact_list":           ["contact list", "list contacts", "all contacts", "contacts"],
    "contact_aging":          ["contact aging", "contact balances aging"],
    "customer_balances":      ["customer balances", "customer outstanding", "customer balance"],
    "vendor_balances":        ["vendor balances", "vendor outstanding", "vendor balance"],
    # Revenue / Payments
    "payments_received":      ["payments received", "payment received", "receipts"],
    "revenue_by_month":       ["revenue by month", "monthly revenue", "revenue trend"],
    "top_customers_revenue":  ["top customers", "top customers by revenue", "best customers"],
    "recurring_invoices":     ["recurring invoices", "recurring invoice", "recurring billing"],
    # Sales
    "sales_summary":          ["sales summary", "sales for period", "sales period"],
    "sales_orders_summary":   ["sales orders", "open orders", "sales order pipeline", "sales order summary"],
    "estimates_summary":      ["estimates", "proposals", "estimate summary", "quotes"],
    "sales_by_item":          ["sales by item", "item sales", "product sales", "item revenue"],
    # Expenses
    "expense_summary":        ["expense summary", "expenses for period", "spend summary"],
    "expense_by_category":    ["expense by category", "expenses by category", "expense categories", "expense breakdown"],
    "top_vendors_expense":    ["top vendors by expense", "top vendors expense", "vendor expense ranking"],
    # AP / Payables
    "ap_aging":               ["ap aging", "payables aging", "accounts payable aging", "ap buckets"],
    "outstanding_bills":      ["outstanding bills", "unpaid bills", "open bills"],
    "overdue_bills":          ["overdue bills", "overdue bill", "past due bills"],
    "bills_by_vendor":        ["bills by vendor", "vendor bills"],
    "purchase_orders_summary":["purchase orders", "open purchase orders", "po summary", "purchase order summary"],
    "vendor_payments":        ["vendor payments", "payments made", "bills paid"],
    "top_vendors_spend":      ["top vendors", "top vendors by spend", "biggest vendors", "vendor spend"],
    # Cash & Banking
    "cash_position":          ["cash position", "current cash", "bank balance", "cash balance"],
    "bank_accounts":          ["bank accounts", "bank account list", "list bank accounts"],
    # Financial Statements
    "profit_loss":            ["profit and loss", "profit & loss", "p&l", "income statement"],
    "balance_sheet":          ["balance sheet", "assets and liabilities"],
    "cash_flow":              ["cash flow", "cash flows"],
    "trial_balance":          ["trial balance"],
    "financial_overview":     ["financial overview", "financial summary", "one page financials"],
    # Tax
    "gst_summary":            ["gst summary", "gst report", "gst"],
    "tax_liability":          ["tax liability", "net tax", "tax owed"],
    "tds_summary":            ["tds summary", "tds report", "tds", "withholding tax"],
    # Inventory
    "inventory_summary":      ["inventory summary", "stock summary", "inventory levels", "stock levels"],
    "top_selling_items":      ["top selling items", "best selling items", "top items sold"],
    "item_price_list":        ["item price list", "price list", "product catalog", "item catalog"],
}

# Flat list of (phrase, script_name) sorted longest phrase first
_PHRASE_MAP: list[tuple[str, str]] = sorted(
    [(phrase, script) for script, phrases in _ALIASES.items() for phrase in phrases],
    key=lambda x: -len(x[0]),
)

# CUD / write keywords that should be handled by raw tools
_WRITE_KEYWORDS = {"create", "add new", "new invoice", "new contact", "new expense",
                   "update", "edit", "modify", "change", "delete", "remove", "void"}

# Auth keywords
_AUTH_KEYWORDS = {"authenticate", "login", "log in", "connect zoho", "zoho auth"}

# Human-readable category labels for capability catalog
_CAPABILITIES = {
    "Receivables / AR":       ["ar_aging", "overdue_invoices", "outstanding_invoices", "draft_invoices", "invoice_summary"],
    "Contacts":               ["contact_list", "contact_aging", "customer_balances", "vendor_balances"],
    "Revenue & Payments":     ["payments_received", "revenue_by_month", "top_customers_revenue", "recurring_invoices"],
    "Sales":                  ["sales_summary", "sales_orders_summary", "estimates_summary", "sales_by_item"],
    "Expenses":               ["expense_summary", "expense_by_category", "top_vendors_expense"],
    "Payables / AP":          ["ap_aging", "outstanding_bills", "overdue_bills", "bills_by_vendor",
                               "purchase_orders_summary", "vendor_payments", "top_vendors_spend"],
    "Cash & Banking":         ["cash_position", "bank_accounts"],
    "Financial Statements":   ["profit_loss", "balance_sheet", "cash_flow", "trial_balance", "financial_overview"],
    "Tax":                    ["gst_summary", "tax_liability", "tds_summary"],
    "Inventory":              ["inventory_summary", "top_selling_items", "item_price_list"],
}

# ---------------------------------------------------------------------------
# Action intent phrase table — NL query → operational intent name
# ---------------------------------------------------------------------------

_ACTION_PHRASES: dict[str, list[str]] = {
    # Invoice write
    "create_invoice":          ["create invoice", "new invoice", "make invoice", "issue invoice",
                                 "raise invoice", "generate invoice"],
    "update_invoice":          ["update invoice", "edit invoice", "modify invoice",
                                 "change invoice", "amend invoice"],
    "delete_invoice":          ["delete invoice", "remove invoice", "void invoice",
                                 "cancel invoice", "delete an invoice", "delete the invoice"],
    # Contact write
    "create_contact":          ["create contact", "add contact", "new contact",
                                 "add customer", "new customer", "add vendor", "new vendor"],
    "update_contact":          ["update contact", "edit contact", "modify contact",
                                 "change contact", "update the contact", "edit the contact"],
    "delete_contact":          ["delete contact", "remove contact",
                                 "delete a contact", "delete the contact"],
    # Expense write
    "create_expense":          ["create expense", "add expense", "new expense",
                                 "record expense", "log expense"],
    "update_expense":          ["update expense", "edit expense", "modify expense",
                                 "update the expense", "edit the expense"],
    "delete_expense":          ["delete expense", "remove expense",
                                 "delete an expense", "delete the expense"],
    # Estimate write
    "create_estimate":         ["create estimate", "new estimate", "create quote",
                                 "new quote", "create proposal", "new proposal"],
    "update_estimate":         ["update estimate", "edit estimate", "modify estimate"],
    "delete_estimate":         ["delete estimate", "remove estimate"],
    # Sales order write
    "create_sales_order":      ["create sales order", "new sales order", "create order"],
    "update_sales_order":      ["update sales order", "edit sales order", "modify sales order"],
    "delete_sales_order":      ["delete sales order", "remove sales order"],
    # Purchase order write
    "create_purchase_order":   ["create purchase order", "new purchase order",
                                 "create po", "new po"],
    "update_purchase_order":   ["update purchase order", "edit purchase order",
                                 "modify purchase order"],
    "delete_purchase_order":   ["delete purchase order", "remove purchase order"],
    # Item write
    "create_item":             ["create item", "add item", "new item",
                                 "create product", "add product"],
    "update_item":             ["update item", "edit item", "modify item"],
    "delete_item":             ["delete item", "remove item", "delete the item"],
    # Tax write
    "create_tax":              ["create tax", "add tax", "new tax rate"],
    "update_tax":              ["update tax", "edit tax", "modify tax"],
    "delete_tax":              ["delete tax", "remove tax"],
    # Customer payment write
    "create_customer_payment": ["record payment", "create payment", "add payment",
                                 "new payment", "apply payment"],
    "update_customer_payment": ["update payment", "edit payment", "modify payment"],
    "delete_customer_payment": ["delete payment", "remove payment"],
    # List intents
    "list_invoices":           ["list all invoices", "list invoices", "show all invoices",
                                 "show invoices", "find invoices"],
    "list_expenses":           ["list all expenses", "list expenses", "show all expenses",
                                 "show expenses", "find expenses"],
    "list_estimates":          ["list all estimates", "list estimates", "show all estimates",
                                 "show estimates", "list all quotes", "list quotes"],
    "list_sales_orders":       ["list all sales orders", "list sales orders",
                                 "show sales orders"],
    "list_purchase_orders":    ["list all purchase orders", "list purchase orders",
                                 "show purchase orders", "list all pos", "list pos"],
    "list_customer_payments":  ["list all payments", "list customer payments",
                                 "show all payments", "show customer payments"],
    "list_bills":              ["list all bills", "list bills", "show all bills", "show bills"],
    "list_items":              ["list all items", "list items", "show all items",
                                 "show items", "list all products", "list products"],
    "list_taxes":              ["list all taxes", "list taxes", "show all taxes", "show taxes"],
    # Get intents
    "get_invoice":             ["get invoice", "find invoice", "look up invoice",
                                 "show invoice details"],
    "get_contact":             ["get contact", "find contact", "look up contact"],
    "get_expense":             ["get expense", "find expense", "look up expense"],
    "get_estimate":            ["get estimate", "find estimate", "look up estimate"],
    "get_sales_order":         ["get sales order", "find sales order", "look up sales order"],
    "get_purchase_order":      ["get purchase order", "find purchase order",
                                 "look up purchase order"],
    "get_customer_payment":    ["get payment details", "find payment", "look up payment"],
    # Special
    "find_customer_activity":  ["customer activity", "activity for customer",
                                 "customer history", "find customer activity"],
}

# Flat sorted list of (phrase, intent) — longest phrase wins
_ACTION_PHRASE_MAP: list[tuple[str, str]] = sorted(
    [(phrase, intent) for intent, phrases in _ACTION_PHRASES.items() for phrase in phrases],
    key=lambda x: -len(x[0]),
)

# ---------------------------------------------------------------------------
# Write intent metadata
# ---------------------------------------------------------------------------

_WRITE_REQUIRED_PARAMS: dict[str, list[str]] = {
    "create_invoice":          ["customer_id", "line_items"],
    "update_invoice":          ["invoice_id"],
    "delete_invoice":          ["invoice_id"],
    "create_contact":          ["contact_name"],
    "update_contact":          ["contact_id"],
    "delete_contact":          ["contact_id"],
    "create_expense":          ["account_id", "total"],
    "update_expense":          ["expense_id"],
    "delete_expense":          ["expense_id"],
    "create_estimate":         ["customer_id", "line_items"],
    "update_estimate":         ["estimate_id"],
    "delete_estimate":         ["estimate_id"],
    "create_sales_order":      ["customer_id", "line_items"],
    "update_sales_order":      ["salesorder_id"],
    "delete_sales_order":      ["salesorder_id"],
    "create_purchase_order":   ["vendor_id", "line_items"],
    "update_purchase_order":   ["purchaseorder_id"],
    "delete_purchase_order":   ["purchaseorder_id"],
    "create_item":             ["name", "rate"],
    "update_item":             ["item_id"],
    "delete_item":             ["item_id"],
    "create_tax":              ["tax_name", "tax_percentage"],
    "update_tax":              ["tax_id"],
    "delete_tax":              ["tax_id"],
    "create_customer_payment": ["customer_id", "amount", "payment_mode"],
    "update_customer_payment": ["payment_id"],
    "delete_customer_payment": ["payment_id"],
}

_PARAM_QUESTIONS: dict[str, str] = {
    "customer_id":    "What is the customer ID? (use zoho_books_list_contacts to find it)",
    "vendor_id":      "What is the vendor ID? (use zoho_books_list_contacts to find it)",
    "invoice_id":     "What is the invoice ID?",
    "expense_id":     "What is the expense ID?",
    "contact_id":     "What is the contact ID?",
    "estimate_id":    "What is the estimate ID?",
    "salesorder_id":  "What is the sales order ID?",
    "purchaseorder_id": "What is the purchase order ID?",
    "item_id":        "What is the item ID? (use zoho_books_list_items to find it)",
    "tax_id":         "What is the tax ID? (use zoho_books_list_taxes to find it)",
    "payment_id":     "What is the payment ID?",
    "line_items":     "What items/services are on this transaction? (provide item_id, rate, quantity for each)",
    "account_id":     "What expense account category? (use zoho_books_list_accounts to find it)",
    "total":          "What is the total amount?",
    "contact_name":   "What is the contact/company name?",
    "name":           "What is the item name?",
    "rate":           "What is the item rate/price?",
    "tax_name":       "What is the tax name?",
    "tax_percentage": "What is the tax percentage rate?",
    "amount":         "What is the payment amount?",
    "payment_mode":   "What is the payment mode? (cash, bank_transfer, UPI, cheque)",
}

# ---------------------------------------------------------------------------
# Intent → raw tool name mapping
# ---------------------------------------------------------------------------

_INTENT_TO_RAW_TOOL: dict[str, str] = {
    # List
    "list_invoices":           "zoho_books_list_invoices",
    "list_expenses":           "zoho_books_list_expenses",
    "list_contacts":           "zoho_books_list_contacts",
    "list_estimates":          "zoho_books_list_estimates",
    "list_sales_orders":       "zoho_books_list_sales_orders",
    "list_purchase_orders":    "zoho_books_list_purchase_orders",
    "list_customer_payments":  "zoho_books_list_customer_payments",
    "list_bills":              "zoho_books_list_bills",
    "list_vendor_payments":    "zoho_books_list_vendor_payments",
    "list_items":              "zoho_books_list_items",
    "list_taxes":              "zoho_books_list_taxes",
    # Get
    "get_invoice":             "zoho_books_get_invoice",
    "get_expense":             "zoho_books_get_expense",
    "get_contact":             "zoho_books_get_contact",
    "get_estimate":            "zoho_books_get_estimate",
    "get_sales_order":         "zoho_books_get_sales_order",
    "get_purchase_order":      "zoho_books_get_purchase_order",
    "get_customer_payment":    "zoho_books_get_customer_payment",
    # Write
    "create_invoice":          "zoho_books_create_invoice",
    "update_invoice":          "zoho_books_update_invoice",
    "delete_invoice":          "zoho_books_delete_invoice",
    "create_contact":          "zoho_books_create_contact",
    "update_contact":          "zoho_books_update_contact",
    "delete_contact":          "zoho_books_delete_contact",
    "create_expense":          "zoho_books_create_expense",
    "update_expense":          "zoho_books_update_expense",
    "delete_expense":          "zoho_books_delete_expense",
    "create_estimate":         "zoho_books_create_estimate",
    "update_estimate":         "zoho_books_update_estimate",
    "delete_estimate":         "zoho_books_delete_estimate",
    "create_sales_order":      "zoho_books_create_sales_order",
    "update_sales_order":      "zoho_books_update_sales_order",
    "delete_sales_order":      "zoho_books_delete_sales_order",
    "create_purchase_order":   "zoho_books_create_purchase_order",
    "update_purchase_order":   "zoho_books_update_purchase_order",
    "delete_purchase_order":   "zoho_books_delete_purchase_order",
    "create_item":             "zoho_books_create_item",
    "update_item":             "zoho_books_update_item",
    "delete_item":             "zoho_books_delete_item",
    "create_tax":              "zoho_books_create_tax",
    "update_tax":              "zoho_books_update_tax",
    "delete_tax":              "zoho_books_delete_tax",
    "create_customer_payment": "zoho_books_create_customer_payment",
    "update_customer_payment": "zoho_books_update_customer_payment",
    "delete_customer_payment": "zoho_books_delete_customer_payment",
}

# Intent → entity type key (for compact record extraction)
_INTENT_TO_ENTITY: dict[str, str] = {
    "list_invoices":          "invoices",
    "list_expenses":          "expenses",
    "list_contacts":          "contacts",
    "list_estimates":         "estimates",
    "list_sales_orders":      "salesorders",
    "list_purchase_orders":   "purchaseorders",
    "list_customer_payments": "customerpayments",
    "list_bills":             "bills",
    "list_vendor_payments":   "vendorpayments",
    "list_items":             "items",
    "list_taxes":             "taxes",
}


# ---------------------------------------------------------------------------
# Internal helpers — report routing
# ---------------------------------------------------------------------------

def _match_report(query: str) -> "str | None":
    """Return script name for the first phrase that appears in query, or None."""
    q = query.lower()
    for phrase, script in _PHRASE_MAP:
        if phrase in q:
            return script
    return None


def _classify_query(query: str) -> tuple[str, "str | None"]:
    """
    Return (intent, script_name_or_None).
    intent: "report" | "write" | "authenticate" | "capabilities" | "unknown"
    """
    q = query.lower()

    if any(kw in q for kw in _AUTH_KEYWORDS):
        return ("authenticate", None)

    if any(kw in q for kw in ("what can you do", "what reports", "capabilities", "available reports")):
        return ("capabilities", None)

    if any(kw in q for kw in _WRITE_KEYWORDS):
        return ("write", None)

    script = _match_report(q)
    if script:
        return ("report", script)

    return ("unknown", None)


def _run_report(script_name: str, params: dict) -> dict:
    """Dynamically import and run a report script."""
    try:
        mod = importlib.import_module(f"products.zoho_books.{script_name}")
        return mod.run(params)
    except ModuleNotFoundError:
        return {
            "success": False,
            "error": "unknown_report",
            "message": f"No report named '{script_name}'. Use recklabs_zoho_capabilities to see available reports.",
        }
    except Exception as exc:
        logger.exception("Report '%s' failed", script_name)
        return {"success": False, "error": "report_failed", "message": str(exc)}


def _resolve_alias(name: str) -> "str | None":
    """Return script name for a given alias or tool name (e.g. 'zb_ar_aging' → 'ar_aging')."""
    clean = name.strip().lower()
    if clean.startswith("zb_"):
        clean = clean[3:]
    if clean in _ALIASES:
        return clean
    return _match_report(name)


# ---------------------------------------------------------------------------
# Internal helpers — action routing
# ---------------------------------------------------------------------------

def _match_action_intent(query: str) -> "str | None":
    """Return action intent for the first phrase that appears in query, or None."""
    q = query.lower()
    for phrase, intent in _ACTION_PHRASE_MAP:
        if phrase in q:
            return intent
    return None


# ---------------------------------------------------------------------------
# Internal raw-tool bridge
# ---------------------------------------------------------------------------

_RAW_TOOL_MAP: "dict | None" = None


def _build_raw_tool_map() -> dict:
    """Lazily build name→fn map from ZOHO_BOOKS_TOOLS."""
    global _RAW_TOOL_MAP
    if _RAW_TOOL_MAP is None:
        try:
            from connectors.zoho_books.tools import ZOHO_BOOKS_TOOLS
            _RAW_TOOL_MAP = {t["name"]: t["fn"] for t in ZOHO_BOOKS_TOOLS}
        except Exception:
            _RAW_TOOL_MAP = {}
    return _RAW_TOOL_MAP


def _call_raw_tool(tool_name: str, params: dict) -> dict:
    """Call a hidden raw Zoho Books tool by name."""
    tool_map = _build_raw_tool_map()
    fn = tool_map.get(tool_name)
    if fn is None:
        return {
            "success": False,
            "error": "unknown_tool",
            "message": f"Tool '{tool_name}' not found in raw tool map.",
        }
    try:
        return fn(params)
    except Exception as exc:
        logger.exception("Raw tool '%s' failed", tool_name)
        return {"success": False, "error": "tool_failed", "message": str(exc)}


# ---------------------------------------------------------------------------
# Compact record helper
# ---------------------------------------------------------------------------

_COMPACT_FIELDS: dict[str, list[str]] = {
    "invoices":        ["invoice_id", "invoice_number", "customer_name", "date",
                        "due_date", "total", "balance", "status", "currency_code"],
    "expenses":        ["expense_id", "date", "account_name", "total",
                        "vendor_name", "description", "status", "currency_code"],
    "contacts":        ["contact_id", "contact_name", "email", "phone",
                        "company_name", "balance"],
    "estimates":       ["estimate_id", "estimate_number", "customer_name", "date",
                        "expiry_date", "total", "status", "currency_code"],
    "salesorders":     ["salesorder_id", "salesorder_number", "customer_name", "date",
                        "shipment_date", "total", "status", "currency_code"],
    "purchaseorders":  ["purchaseorder_id", "purchaseorder_number", "vendor_name", "date",
                        "delivery_date", "total", "status", "currency_code"],
    "customerpayments":["payment_id", "payment_number", "customer_name", "payment_date",
                        "amount", "payment_mode", "invoice_numbers"],
    "bills":           ["bill_id", "bill_number", "vendor_name", "date",
                        "due_date", "total", "balance", "status", "currency_code"],
    "vendorpayments":  ["payment_id", "vendor_name", "payment_date", "amount", "payment_mode"],
    "items":           ["item_id", "name", "rate", "unit", "description", "status"],
    "taxes":           ["tax_id", "tax_name", "tax_percentage", "tax_type"],
}


def _compact_records(records: list, entity_type: str, limit: int = 20) -> list:
    """Return compact (key fields only) records, capped at limit."""
    fields = _COMPACT_FIELDS.get(entity_type, [])
    result = []
    for rec in records[:limit]:
        if fields:
            result.append({k: rec[k] for k in fields if k in rec})
        else:
            result.append(rec)
    return result


# ---------------------------------------------------------------------------
# Action intent handlers
# ---------------------------------------------------------------------------

def _handle_list_get(intent: str, action_params: dict) -> dict:
    """Handle list_* and get_* intents by calling the hidden raw tool."""
    raw_tool = _INTENT_TO_RAW_TOOL.get(intent)
    if not raw_tool:
        return {
            "success": False,
            "error": "unknown_intent",
            "message": f"No raw tool mapped for intent '{intent}'.",
        }

    result = _call_raw_tool(raw_tool, action_params)

    # Compact list results to reduce context window usage
    if result.get("success") and intent in _INTENT_TO_ENTITY:
        entity_type = _INTENT_TO_ENTITY[intent]
        limit = int(action_params.get("limit", 20))

        data = result.get("data", result)
        # Try the plural entity key first, then "data", then treat data as list
        if isinstance(data, dict):
            records = data.get(entity_type) or data.get("data") or []
        elif isinstance(data, list):
            records = data
        else:
            records = []

        if isinstance(records, list):
            compacted = _compact_records(records, entity_type, limit)
            return {
                "success": True,
                "intent": intent,
                "count": len(compacted),
                "records": compacted,
            }

    return result


def _handle_write(intent: str, action_params: dict, confirmed: bool) -> dict:
    """Handle write intents: validate required params, gate on confirmation, then execute."""
    required = _WRITE_REQUIRED_PARAMS.get(intent, [])
    missing = [p for p in required if not action_params.get(p)]

    if missing:
        questions = [_PARAM_QUESTIONS.get(p, f"Please provide '{p}'.") for p in missing]
        return {
            "success": False,
            "error": "missing_parameters",
            "intent": intent,
            "missing": missing,
            "questions": questions,
            "safe_next_step": (
                "Never guess IDs. Look up required IDs first: "
                "zoho_books_list_contacts (customer/vendor), "
                "zoho_books_list_items (items), "
                "zoho_books_list_taxes (taxes). "
                "Then call recklabs_zoho_action again with all params filled."
            ),
        }

    if not confirmed:
        is_delete = intent.startswith("delete_")
        entity = intent.split("_", 1)[1].replace("_", " ")
        if is_delete:
            message = (
                f"You are about to permanently delete a {entity}. "
                "This action cannot be undone. "
                "Call this tool again with confirmed=true to proceed."
            )
        else:
            verb = "create" if intent.startswith("create_") else "update"
            message = (
                f"Ready to {verb} {entity} with the provided parameters. "
                "Review the draft and call this tool again with confirmed=true to execute."
            )
        return {
            "success": False,
            "error": "confirmation_required",
            "intent": intent,
            "draft": action_params,
            "message": message,
        }

    raw_tool = _INTENT_TO_RAW_TOOL.get(intent)
    if not raw_tool:
        return {
            "success": False,
            "error": "unknown_intent",
            "message": f"No raw tool mapped for intent '{intent}'.",
        }
    return _call_raw_tool(raw_tool, action_params)


def _handle_find_customer_activity(action_params: dict, query: str) -> dict:
    """Aggregate invoices, estimates, and payments for a named customer."""
    customer_name = action_params.get("customer_name") or query
    if not customer_name:
        return {
            "success": False,
            "error": "missing_parameters",
            "intent": "find_customer_activity",
            "missing": ["customer_name"],
            "questions": ["Which customer are you looking for?"],
            "safe_next_step": "Provide customer_name in params or as the query string.",
        }

    search_params = {**action_params, "search_text": customer_name}
    inv_result = _call_raw_tool("zoho_books_list_invoices", search_params)
    est_result = _call_raw_tool("zoho_books_list_estimates", search_params)
    pay_result = _call_raw_tool("zoho_books_list_customer_payments", search_params)

    def _extract(result, key):
        if not result.get("success"):
            return []
        data = result.get("data", result)
        if isinstance(data, dict):
            return data.get(key) or []
        return []

    return {
        "success": True,
        "intent": "find_customer_activity",
        "customer_name": customer_name,
        "invoices": _compact_records(_extract(inv_result, "invoices"), "invoices", 10),
        "estimates": _compact_records(_extract(est_result, "estimates"), "estimates", 10),
        "customer_payments": _compact_records(
            _extract(pay_result, "customer_payments"), "customerpayments", 10
        ),
    }


# ---------------------------------------------------------------------------
# Tool handler functions
# ---------------------------------------------------------------------------

def recklabs_zoho_assistant(params: dict) -> dict:
    """
    Natural-language Zoho Books assistant.
    Routes the query to the right pre-built report and returns the result.
    For operational actions (list/find/write), delegates to recklabs_zoho_action.
    """
    query = str(params.get("query", "")).strip()
    if not query:
        return {
            "success": False,
            "error": "missing_query",
            "message": "Provide a 'query' parameter describing what you want to know.",
        }

    intent, script = _classify_query(query)

    if intent == "report":
        report_params = {k: v for k, v in params.items() if k not in ("query",)}
        return _run_report(script, report_params)

    if intent == "authenticate":
        return {
            "success": False,
            "error": "use_raw_tool",
            "guidance": "Use the zoho_books_authenticate tool to connect to Zoho Books.",
        }

    if intent == "capabilities":
        return recklabs_zoho_capabilities({})

    if intent == "write":
        action_intent = _match_action_intent(query)
        if action_intent:
            return recklabs_zoho_action({"intent": action_intent, "query": query})
        return {
            "success": False,
            "error": "use_raw_tool",
            "workflow": "lookup_first",
            "guidance": (
                "Write operations require a safe lookup-first workflow. "
                "Use recklabs_zoho_action with the appropriate intent "
                "(e.g. 'create_invoice', 'update_contact', 'delete_expense'). "
                "Never guess IDs — always look them up first. "
                "Always confirm with the user before executing any write action."
            ),
        }

    # Unknown — try action intent match before giving up
    action_intent = _match_action_intent(query)
    if action_intent:
        return recklabs_zoho_action({"intent": action_intent, "query": query})

    return {
        "success": False,
        "error": "query_not_understood",
        "message": (
            f"Could not map '{query}' to a known report or action. "
            "Try recklabs_zoho_capabilities to see available reports, "
            "or use recklabs_zoho_action with an explicit intent."
        ),
    }


def recklabs_zoho_report(params: dict) -> dict:
    """
    Run a specific Zoho Books report by name or alias.
    Pass 'report' as the report name (e.g. 'ar_aging', 'zb_ar_aging',
    'profit and loss'). Optional extra params are forwarded to the report.
    """
    name = str(params.get("report", "")).strip()
    if not name:
        return {
            "success": False,
            "error": "missing_report",
            "message": "Provide a 'report' parameter with the report name or alias.",
        }

    script = _resolve_alias(name)
    if not script:
        return {
            "success": False,
            "error": "unknown_report",
            "message": (
                f"No report matched '{name}'. "
                "Use recklabs_zoho_capabilities to see available report names."
            ),
        }

    report_params = {k: v for k, v in params.items() if k not in ("report",)}
    return _run_report(script, report_params)


def recklabs_zoho_capabilities(params: dict) -> dict:
    """Return a catalog of all available Zoho Books reports grouped by category."""
    catalog = {}
    for category, scripts in _CAPABILITIES.items():
        entries = []
        for script in scripts:
            try:
                mod = importlib.import_module(f"products.zoho_books.{script}")
                desc = getattr(mod, "TOOL_DESCRIPTION", "")
                tool_params = getattr(mod, "TOOL_PARAMS", {})
                entries.append({
                    "name": getattr(mod, "TOOL_NAME", f"zb_{script}"),
                    "description": desc,
                    "params": list(tool_params.keys()) if tool_params else [],
                })
            except ModuleNotFoundError:
                pass
        if entries:
            catalog[category] = entries

    total = sum(len(v) for v in catalog.values())
    return {
        "success": True,
        "report": "Capabilities Catalog",
        "total_reports": total,
        "catalog": catalog,
        "usage": (
            "Use recklabs_zoho_assistant with a natural-language query, "
            "or recklabs_zoho_report with an explicit report name."
        ),
    }


def recklabs_zoho_action(params: dict) -> dict:
    """
    Operational bridge tool for Zoho Books.

    Handles list/find queries and write operations via hidden raw tools.
    For list/find intents: calls the raw tool and returns compact records.
    For write intents: validates required params, gates on confirmation,
    then executes the raw tool on confirmed=true.

    Intents:
      List:  list_invoices, list_expenses, list_contacts, list_estimates,
             list_sales_orders, list_purchase_orders, list_customer_payments,
             list_bills, list_items, list_taxes
      Get:   get_invoice, get_contact, get_expense, get_estimate,
             get_sales_order, get_purchase_order, get_customer_payment
      Write: create_invoice, update_invoice, delete_invoice,
             create_contact, update_contact, delete_contact,
             create_expense, update_expense, delete_expense,
             create_estimate, update_estimate, delete_estimate,
             create_sales_order, update_sales_order, delete_sales_order,
             create_purchase_order, update_purchase_order, delete_purchase_order,
             create_item, update_item, delete_item,
             create_tax, update_tax, delete_tax,
             create_customer_payment, update_customer_payment, delete_customer_payment
      Special: find_customer_activity
    """
    intent = str(params.get("intent", "")).strip().lower()
    query = str(params.get("query", "")).strip()
    action_params = params.get("params") or {}
    confirmed = bool(params.get("confirmed", False))

    if not intent:
        return {
            "success": False,
            "error": "missing_intent",
            "message": (
                "Provide an 'intent' parameter describing the action. "
                "Examples: 'list_invoices', 'create_invoice', 'delete_contact'."
            ),
        }

    if intent == "find_customer_activity":
        return _handle_find_customer_activity(action_params, query)

    if intent.startswith("list_") or intent.startswith("get_"):
        if intent in _INTENT_TO_RAW_TOOL:
            return _handle_list_get(intent, action_params)

    if intent in _WRITE_REQUIRED_PARAMS:
        return _handle_write(intent, action_params, confirmed)

    return {
        "success": False,
        "error": "unknown_intent",
        "message": (
            f"Unknown intent '{intent}'. Valid intents: "
            "list_invoices, list_expenses, list_contacts, list_estimates, "
            "list_sales_orders, list_purchase_orders, list_customer_payments, "
            "list_bills, list_items, list_taxes, "
            "get_invoice, get_contact, get_expense, get_estimate, "
            "get_sales_order, get_purchase_order, get_customer_payment, "
            "create/update/delete for invoice, contact, expense, estimate, "
            "sales_order, purchase_order, item, tax, customer_payment, "
            "find_customer_activity."
        ),
    }


# ---------------------------------------------------------------------------
# MCP tool definitions
# ---------------------------------------------------------------------------

ROUTER_TOOLS = [
    {
        "name": "recklabs_zoho_assistant",
        "description": (
            "Natural-language Zoho Books assistant. "
            "Ask anything about your finances — AR aging, overdue invoices, expense summary, "
            "profit & loss, cash position, GST, TDS, inventory, and more. "
            "This tool routes your query to the right pre-built report and returns a compact result. "
            "Use this as the PRIMARY entry point for all reporting and analysis queries. "
            "For write or list operations, this tool will delegate to recklabs_zoho_action."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What you want to know, in plain English. E.g. 'Show me AR aging', 'What is my cash position?'",
                },
                "period": {
                    "type": "string",
                    "description": "Optional period filter: this_month, last_month, this_quarter, last_quarter, this_year, last_year.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Optional max records for reports that support it.",
                },
            },
            "required": ["query"],
        },
        "fn": recklabs_zoho_assistant,
    },
    {
        "name": "recklabs_zoho_report",
        "description": (
            "Run a specific Zoho Books report by name. "
            "Use when you know the exact report name (e.g. 'ar_aging', 'zb_profit_loss', 'cash position'). "
            "Use recklabs_zoho_capabilities to discover available report names."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "report": {
                    "type": "string",
                    "description": "Report name or alias. E.g. 'ar_aging', 'zb_ar_aging', 'profit and loss'.",
                },
                "period": {
                    "type": "string",
                    "description": "Optional period: this_month, last_month, this_quarter, last_quarter, this_year, last_year.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Optional max records for reports that support it.",
                },
            },
            "required": ["report"],
        },
        "fn": recklabs_zoho_report,
    },
    {
        "name": "recklabs_zoho_capabilities",
        "description": (
            "Returns a full catalog of available Zoho Books reports grouped by category. "
            "Use this when the user asks what reports are available, or when a query cannot be matched. "
            "No parameters required."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "fn": recklabs_zoho_capabilities,
    },
    {
        "name": "recklabs_zoho_action",
        "description": (
            "Operational bridge tool for Zoho Books. "
            "Use for: listing records (list_invoices, list_expenses, list_contacts, etc.), "
            "fetching a single record (get_invoice, get_contact, etc.), "
            "and write operations (create/update/delete for invoice, contact, expense, estimate, "
            "sales_order, purchase_order, item, tax, customer_payment). "
            "Write operations follow a safe 3-step flow: "
            "(1) missing params → returns questions to ask the user, "
            "(2) params provided but unconfirmed → returns draft for user review, "
            "(3) confirmed=true → executes the action. "
            "Never guess IDs — always use list tools to look them up first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "description": (
                        "The action intent. E.g. 'list_invoices', 'create_invoice', "
                        "'delete_contact', 'find_customer_activity'."
                    ),
                },
                "query": {
                    "type": "string",
                    "description": "Optional NL context (e.g. customer name for find_customer_activity).",
                },
                "params": {
                    "type": "object",
                    "description": "Parameters for the action (e.g. customer_id, line_items, invoice_id).",
                },
                "confirmed": {
                    "type": "boolean",
                    "description": "Set to true to execute a write action after reviewing the draft.",
                },
            },
            "required": ["intent"],
        },
        "fn": recklabs_zoho_action,
    },
]
