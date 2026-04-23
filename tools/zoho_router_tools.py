"""
Customer-mode router tools for Zoho Books.

In customer mode these three tools replace the 40 zb_* report scripts and
51 raw zoho_books_list/get tools, keeping Claude Desktop's tool list short
and focused on natural-language interaction.

  recklabs_zoho_assistant   — NL query → run the right report tool
  recklabs_zoho_report      — Direct report runner by name or alias
  recklabs_zoho_capabilities — Catalog of available reports
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
# Internal helpers
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
    # strip zb_ prefix if present
    clean = name.strip().lower()
    if clean.startswith("zb_"):
        clean = clean[3:]
    if clean in _ALIASES:
        return clean
    # also try phrase match
    return _match_report(name)


# ---------------------------------------------------------------------------
# Tool handler functions
# ---------------------------------------------------------------------------

def recklabs_zoho_assistant(params: dict) -> dict:
    """
    Natural-language Zoho Books assistant.
    Routes the query to the right pre-built report and returns the result.
    For write operations, returns guidance to use the appropriate raw tool.
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
        return {
            "success": False,
            "error": "use_raw_tool",
            "workflow": "lookup_first",
            "guidance": (
                "Write operations require a safe lookup-first workflow. "
                "Never guess IDs or accounting fields. "
                "Follow these steps:\n"
                "1. Lookup: use zoho_books_list_contacts / zoho_books_list_items / "
                "zoho_books_list_taxes to find the exact IDs needed.\n"
                "2. Resolve: ask the user for any missing or ambiguous fields "
                "(dates, tax rate, payment mode, currency, GST details).\n"
                "3. Draft: show a short summary of the proposed action.\n"
                "4. Confirm: ask the user to confirm before executing.\n"
                "5. Execute: call zoho_books_create_* / zoho_books_update_* / zoho_books_delete_*.\n"
                "Never reuse an ID from a previous turn without looking it up again."
            ),
        }

    # Unknown — try harder with a broad phrase scan before giving up
    return {
        "success": False,
        "error": "query_not_understood",
        "message": (
            f"Could not map '{query}' to a known report. "
            "Try recklabs_zoho_capabilities to see what's available, "
            "or use recklabs_zoho_report with an explicit report name."
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
            "For write operations (create/update/delete), use the specific zoho_books_* raw tools."
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
                "description": "Optional period filter for reports that support it: this_month, last_month, this_quarter, last_quarter, this_year, last_year.",
            },
            "limit": {
                "type": "integer",
                "description": "Optional max records for reports that support it. Default varies by report.",
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
                "description": "Report name or alias. E.g. 'ar_aging', 'zb_ar_aging', 'profit and loss', 'cash position'.",
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
]
