"""Tests for Phase 3 tool exposure policy and router tools."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    CUSTOMER_MODE_RAW_TOOL_NAMES,
    filter_connector_tools,
)
from tools.zoho_router_tools import (
    _classify_query,
    _match_report,
    _resolve_alias,
    _match_action_intent,
    _compact_records,
    recklabs_zoho_capabilities,
    recklabs_zoho_action,
    ROUTER_TOOLS,
    _ALIASES,
)


# ---------------------------------------------------------------------------
# CUSTOMER_MODE_RAW_TOOL_NAMES sanity checks
# ---------------------------------------------------------------------------

def test_customer_mode_has_43_names():
    assert len(CUSTOMER_MODE_RAW_TOOL_NAMES) == 43


def test_customer_mode_includes_auth_tools():
    assert "zoho_books_authenticate" in CUSTOMER_MODE_RAW_TOOL_NAMES
    assert "zoho_books_connection_status" in CUSTOMER_MODE_RAW_TOOL_NAMES
    assert "zoho_books_list_organizations" in CUSTOMER_MODE_RAW_TOOL_NAMES
    assert "zoho_books_get_organization" in CUSTOMER_MODE_RAW_TOOL_NAMES


def test_customer_mode_includes_cud_tools():
    # Spot-check one entity
    assert "zoho_books_create_invoice" in CUSTOMER_MODE_RAW_TOOL_NAMES
    assert "zoho_books_update_invoice" in CUSTOMER_MODE_RAW_TOOL_NAMES
    assert "zoho_books_delete_invoice" in CUSTOMER_MODE_RAW_TOOL_NAMES


def test_customer_mode_excludes_heavy_list_tools():
    # Heavy list tools (no safe-lookup counterpart) stay hidden
    assert "zoho_books_list_invoices" not in CUSTOMER_MODE_RAW_TOOL_NAMES
    assert "zoho_books_list_expenses" not in CUSTOMER_MODE_RAW_TOOL_NAMES
    assert "zoho_books_list_customer_payments" not in CUSTOMER_MODE_RAW_TOOL_NAMES


def test_customer_mode_exposes_safe_lookup_tools():
    assert "zoho_books_list_contacts" in CUSTOMER_MODE_RAW_TOOL_NAMES
    assert "zoho_books_get_contact" in CUSTOMER_MODE_RAW_TOOL_NAMES
    assert "zoho_books_list_items" in CUSTOMER_MODE_RAW_TOOL_NAMES
    assert "zoho_books_get_item" in CUSTOMER_MODE_RAW_TOOL_NAMES
    assert "zoho_books_list_taxes" in CUSTOMER_MODE_RAW_TOOL_NAMES
    assert "zoho_books_get_tax" in CUSTOMER_MODE_RAW_TOOL_NAMES
    assert "zoho_books_get_invoice" in CUSTOMER_MODE_RAW_TOOL_NAMES
    assert "zoho_books_get_estimate" in CUSTOMER_MODE_RAW_TOOL_NAMES
    assert "zoho_books_get_sales_order" in CUSTOMER_MODE_RAW_TOOL_NAMES
    assert "zoho_books_get_purchase_order" in CUSTOMER_MODE_RAW_TOOL_NAMES
    assert "zoho_books_get_expense" in CUSTOMER_MODE_RAW_TOOL_NAMES
    assert "zoho_books_get_customer_payment" in CUSTOMER_MODE_RAW_TOOL_NAMES


# ---------------------------------------------------------------------------
# filter_connector_tools
# ---------------------------------------------------------------------------

def _make_tools(names):
    return [{"name": n, "fn": lambda p: {}, "description": "", "params": {}} for n in names]


def test_filter_developer_mode_returns_all():
    tools = _make_tools(["zoho_books_list_invoices", "zoho_books_create_invoice", "zb_ar_aging"])
    result = filter_connector_tools(tools, mode="developer")
    assert len(result) == 3


def test_filter_customer_mode_keeps_cud_only():
    tools = _make_tools([
        "zoho_books_list_invoices",
        "zoho_books_create_invoice",
        "zoho_books_update_invoice",
        "zoho_books_delete_invoice",
        "zb_ar_aging",
    ])
    result = filter_connector_tools(tools, mode="customer")
    names = {t["name"] for t in result}
    assert names == {"zoho_books_create_invoice", "zoho_books_update_invoice", "zoho_books_delete_invoice"}


def test_filter_customer_mode_excludes_report_scripts():
    tools = _make_tools(["zb_ar_aging", "zb_profit_loss", "zoho_books_create_contact"])
    result = filter_connector_tools(tools, mode="customer")
    assert len(result) == 1
    assert result[0]["name"] == "zoho_books_create_contact"


def test_filter_customer_mode_small_count():
    # Build a realistic full set: 51 raw + 40 scripts
    # Extra raw tools that are NOT in CUSTOMER_MODE_RAW_TOOL_NAMES
    raw_names = list(CUSTOMER_MODE_RAW_TOOL_NAMES) + [
        "zoho_books_list_invoices", "zoho_books_list_expenses",
        "zoho_books_list_estimates", "zoho_books_list_sales_orders",
    ]
    script_names = [f"zb_script_{i}" for i in range(40)]
    all_tools = _make_tools(raw_names + script_names)
    result = filter_connector_tools(all_tools, mode="customer")
    assert len(result) == 43


def test_dedupe_tools_keeps_last_definition():
    from main import dedupe_tools
    tools = [
        {"name": "same_tool", "fn": "old", "description": "old", "input_schema": {}},
        {"name": "other_tool", "fn": "other", "description": "other", "input_schema": {}},
        {"name": "same_tool", "fn": "new", "description": "new", "input_schema": {}},
    ]
    result = dedupe_tools(tools)
    by_name = {tool["name"]: tool for tool in result}
    assert len(result) == 2
    assert by_name["same_tool"]["fn"] == "new"


# ---------------------------------------------------------------------------
# _classify_query
# ---------------------------------------------------------------------------

def test_classify_ar_aging():
    intent, script = _classify_query("Show me AR aging")
    assert intent == "report"
    assert script == "ar_aging"


def test_classify_plain_receivables():
    intent, script = _classify_query("Show me receivables this month")
    assert intent == "report"
    assert script == "ar_aging"


def test_classify_who_owes_me_money():
    intent, script = _classify_query("Who owes me money?")
    assert intent == "report"
    assert script == "ar_aging"


def test_classify_profit_loss():
    intent, script = _classify_query("What is my profit and loss?")
    assert intent == "report"
    assert script == "profit_loss"


def test_classify_cash_position():
    intent, script = _classify_query("What is our current cash position?")
    assert intent == "report"
    assert script == "cash_position"


def test_classify_overdue_invoices():
    intent, script = _classify_query("List overdue invoices")
    assert intent == "report"
    assert script == "overdue_invoices"


def test_classify_gst():
    intent, script = _classify_query("Show me GST summary")
    assert intent == "report"
    assert script == "gst_summary"


def test_classify_authenticate():
    intent, script = _classify_query("authenticate with zoho")
    assert intent == "authenticate"
    assert script is None


def test_classify_capabilities():
    intent, script = _classify_query("what reports are available?")
    assert intent == "capabilities"
    assert script is None


def test_classify_write_create():
    intent, script = _classify_query("create a new invoice for Acme")
    assert intent == "write"


def test_classify_write_update():
    intent, script = _classify_query("update the contact phone number")
    assert intent == "write"


def test_classify_write_delete():
    intent, script = _classify_query("delete expense INV-007")
    assert intent == "write"


def test_classify_unknown():
    intent, script = _classify_query("tell me a joke")
    assert intent == "unknown"


# ---------------------------------------------------------------------------
# _match_report — spot checks
# ---------------------------------------------------------------------------

def test_match_report_p_and_l():
    assert _match_report("p&l for this year") == "profit_loss"


def test_match_report_tds():
    assert _match_report("show tds report") == "tds_summary"


def test_match_report_top_customers():
    assert _match_report("who are the top customers") == "top_customers_revenue"


def test_match_report_inventory():
    assert _match_report("check inventory summary") == "inventory_summary"


def test_match_report_none():
    assert _match_report("hello world") is None


# ---------------------------------------------------------------------------
# _resolve_alias
# ---------------------------------------------------------------------------

def test_resolve_alias_zb_prefix():
    assert _resolve_alias("zb_ar_aging") == "ar_aging"


def test_resolve_alias_plain_name():
    assert _resolve_alias("ar_aging") == "ar_aging"


def test_resolve_alias_phrase():
    assert _resolve_alias("profit and loss") == "profit_loss"


def test_resolve_alias_unknown():
    assert _resolve_alias("nonexistent_report") is None


# ---------------------------------------------------------------------------
# ROUTER_TOOLS structure
# ---------------------------------------------------------------------------

def test_router_tools_has_four():
    assert len(ROUTER_TOOLS) == 4


def test_router_tool_names():
    names = {t["name"] for t in ROUTER_TOOLS}
    assert names == {
        "recklabs_zoho_assistant",
        "recklabs_zoho_report",
        "recklabs_zoho_capabilities",
        "recklabs_zoho_action",
    }


def test_router_tools_all_have_fn():
    for tool in ROUTER_TOOLS:
        assert callable(tool["fn"])


def test_router_tools_all_have_mcp_input_schema():
    for tool in ROUTER_TOOLS:
        assert "input_schema" in tool
        assert tool["input_schema"]["type"] == "object"
        assert "properties" in tool["input_schema"]
        assert "required" in tool["input_schema"]


# ---------------------------------------------------------------------------
# recklabs_zoho_capabilities (no connector needed)
# ---------------------------------------------------------------------------

def test_capabilities_returns_catalog():
    result = recklabs_zoho_capabilities({})
    assert result["success"] is True
    assert "catalog" in result
    assert result["total_reports"] > 0


def test_capabilities_catalog_has_categories():
    result = recklabs_zoho_capabilities({})
    catalog = result["catalog"]
    assert "Receivables / AR" in catalog
    assert "Financial Statements" in catalog
    assert "Tax" in catalog


def test_capabilities_catalog_total_matches_40():
    result = recklabs_zoho_capabilities({})
    assert result["total_reports"] == 40


# ---------------------------------------------------------------------------
# recklabs_zoho_assistant — no connector (auth error path)
# ---------------------------------------------------------------------------

def test_assistant_missing_query():
    from tools.zoho_router_tools import recklabs_zoho_assistant
    result = recklabs_zoho_assistant({})
    assert result["success"] is False
    assert result["error"] == "missing_query"


def test_assistant_auth_error_surfaces():
    """Report tool runs but hits auth error — success=False with authentication_required."""
    from tools.zoho_router_tools import recklabs_zoho_assistant
    result = recklabs_zoho_assistant({"query": "show ar aging"})
    assert result["success"] is False
    assert result.get("error") in ("authentication_required", "report_failed", "fetch_failed")


def test_assistant_write_guidance():
    from tools.zoho_router_tools import recklabs_zoho_assistant
    result = recklabs_zoho_assistant({"query": "create a new invoice"})
    assert result["success"] is False
    # Routes to recklabs_zoho_action → missing_parameters (no customer_id/line_items)
    assert result["error"] in ("missing_parameters", "use_raw_tool")


def test_assistant_unknown_query():
    from tools.zoho_router_tools import recklabs_zoho_assistant
    result = recklabs_zoho_assistant({"query": "what is the meaning of life"})
    assert result["success"] is False
    assert result["error"] == "query_not_understood"


# ---------------------------------------------------------------------------
# recklabs_zoho_report — alias resolution and no-connector auth error
# ---------------------------------------------------------------------------

def test_zoho_report_missing_report_param():
    from tools.zoho_router_tools import recklabs_zoho_report
    result = recklabs_zoho_report({})
    assert result["success"] is False
    assert result["error"] == "missing_report"


def test_zoho_report_unknown_name():
    from tools.zoho_router_tools import recklabs_zoho_report
    result = recklabs_zoho_report({"report": "nonexistent_xyz_report"})
    assert result["success"] is False
    assert result["error"] == "unknown_report"


def test_zoho_report_valid_name_hits_auth():
    """Providing a valid report name reaches the script which needs the connector."""
    from tools.zoho_router_tools import recklabs_zoho_report
    result = recklabs_zoho_report({"report": "ar_aging"})
    assert result["success"] is False
    assert result.get("error") in ("authentication_required", "report_failed", "fetch_failed")


# ---------------------------------------------------------------------------
# Write intent — safe workflow guidance (via recklabs_zoho_action)
# ---------------------------------------------------------------------------

def test_write_intent_guidance_mentions_lookup():
    result = recklabs_zoho_action({"intent": "create_invoice", "params": {}})
    assert result["error"] == "missing_parameters"
    safe = result.get("safe_next_step", "")
    assert "list_contacts" in safe or "lookup" in safe.lower()


def test_write_intent_guidance_mentions_confirm():
    result = recklabs_zoho_action({"intent": "delete_invoice", "params": {"invoice_id": "INV-001"}})
    assert result["error"] == "confirmation_required"
    assert "confirm" in result["message"].lower() or "delete" in result["message"].lower()


def test_write_intent_guidance_mentions_never_guess():
    result = recklabs_zoho_action({"intent": "create_invoice", "params": {}})
    assert result["error"] == "missing_parameters"
    safe = result.get("safe_next_step", "")
    assert "never" in safe.lower() or "guess" in safe.lower()


def test_write_intent_guidance_has_workflow_key():
    result = recklabs_zoho_action({"intent": "create_invoice", "params": {}})
    assert result["error"] == "missing_parameters"
    assert "missing" in result
    assert "questions" in result


# ---------------------------------------------------------------------------
# recklabs_zoho_action — unit tests (no connector needed for most)
# ---------------------------------------------------------------------------

def test_action_tool_missing_intent():
    result = recklabs_zoho_action({})
    assert result["success"] is False
    assert result["error"] == "missing_intent"


def test_action_tool_unknown_intent():
    result = recklabs_zoho_action({"intent": "do_the_hokey_pokey"})
    assert result["success"] is False
    assert result["error"] == "unknown_intent"


def test_action_create_invoice_missing_params():
    result = recklabs_zoho_action({"intent": "create_invoice", "params": {}})
    assert result["success"] is False
    assert result["error"] == "missing_parameters"
    assert "customer_id" in result["missing"]
    assert "line_items" in result["missing"]
    assert len(result["questions"]) == 2


def test_action_create_invoice_requires_confirmation():
    result = recklabs_zoho_action({
        "intent": "create_invoice",
        "params": {"customer_id": "cust_123", "line_items": [{"rate": 1000, "quantity": 1}]},
    })
    assert result["success"] is False
    assert result["error"] == "confirmation_required"
    assert result["intent"] == "create_invoice"
    assert "draft" in result


def test_action_delete_invoice_requires_confirmation():
    result = recklabs_zoho_action({"intent": "delete_invoice", "params": {"invoice_id": "INV-001"}})
    assert result["success"] is False
    assert result["error"] == "confirmation_required"
    assert "cannot be undone" in result["message"].lower()


def test_action_confirmed_delete_hits_auth():
    result = recklabs_zoho_action({
        "intent": "delete_invoice",
        "params": {"invoice_id": "INV-001"},
        "confirmed": True,
    })
    assert result["success"] is False
    assert result.get("error") in (
        "authentication_required", "connector_error",
        "tool_failed", "unexpected_error", "unknown_tool",
    )


def test_action_list_invoices_hits_auth():
    result = recklabs_zoho_action({"intent": "list_invoices"})
    assert result["success"] is False
    assert result.get("error") in (
        "authentication_required", "connector_error",
        "tool_failed", "fetch_failed", "unknown_tool",
    )


def test_action_list_expenses_hits_auth():
    result = recklabs_zoho_action({"intent": "list_expenses"})
    assert result["success"] is False
    assert result.get("error") in (
        "authentication_required", "connector_error",
        "tool_failed", "fetch_failed", "unknown_tool",
    )


def test_action_find_customer_activity_missing_name():
    result = recklabs_zoho_action({"intent": "find_customer_activity", "params": {}})
    assert result["success"] is False
    assert result["error"] == "missing_parameters"
    assert "customer_name" in result["missing"]


def test_compact_records_limits_and_strips_fields():
    records = [
        {"invoice_id": "1", "invoice_number": "INV-001", "customer_name": "Acme",
         "total": 1000, "extra_field": "should_be_removed"},
        {"invoice_id": "2", "invoice_number": "INV-002", "customer_name": "Beta", "total": 2000},
    ]
    result = _compact_records(records, "invoices", limit=1)
    assert len(result) == 1
    assert "extra_field" not in result[0]
    assert "invoice_id" in result[0]
    assert result[0]["invoice_number"] == "INV-001"


def test_compact_records_unknown_entity_returns_full():
    records = [{"foo": "bar", "baz": "qux"}]
    result = _compact_records(records, "unknown_entity", limit=10)
    assert result == records


def test_match_action_intent_create_invoice():
    assert _match_action_intent("create a new invoice for Acme") == "create_invoice"


def test_match_action_intent_delete_contact():
    assert _match_action_intent("I want to delete the contact") == "delete_contact"


def test_match_action_intent_list_invoices():
    assert _match_action_intent("please list all invoices") == "list_invoices"


def test_match_action_intent_no_match():
    assert _match_action_intent("tell me a joke") is None


def test_customer_mode_action_tool_in_router():
    names = {t["name"] for t in ROUTER_TOOLS}
    assert "recklabs_zoho_action" in names


def test_action_tool_has_mcp_schema():
    action_tool = next(t for t in ROUTER_TOOLS if t["name"] == "recklabs_zoho_action")
    schema = action_tool["input_schema"]
    assert schema["type"] == "object"
    assert "intent" in schema["properties"]
    assert "intent" in schema["required"]
    assert callable(action_tool["fn"])


# ---------------------------------------------------------------------------
# create/update/delete tool descriptions contain "Never guess"
# ---------------------------------------------------------------------------

def test_cud_descriptions_contain_never_guess():
    from connectors.zoho_books.tools import ZOHO_BOOKS_TOOLS
    cud_tools = [
        t for t in ZOHO_BOOKS_TOOLS
        if any(t["name"].startswith(f"zoho_books_{verb}_") for verb in ("create", "update", "delete"))
    ]
    missing = [t["name"] for t in cud_tools if "Never guess" not in t["description"]]
    assert not missing, f"CUD tools missing 'Never guess' in description: {missing}"


def test_cud_tool_count_is_27():
    from connectors.zoho_books.tools import ZOHO_BOOKS_TOOLS
    cud_tools = [
        t for t in ZOHO_BOOKS_TOOLS
        if any(t["name"].startswith(f"zoho_books_{verb}_") for verb in ("create", "update", "delete"))
    ]
    assert len(cud_tools) == 27


# ---------------------------------------------------------------------------
# Developer mode exposes all raw tools and all zb_* scripts
# ---------------------------------------------------------------------------

def test_developer_mode_exposes_all_raw_tools():
    from connectors.zoho_books.tools import ZOHO_BOOKS_TOOLS
    tools = [{"name": t["name"], "fn": t["fn"], "description": t["description"], "params": {}} for t in ZOHO_BOOKS_TOOLS]
    result = filter_connector_tools(tools, mode="developer")
    assert len(result) == 51


def test_developer_mode_exposes_all_zb_scripts():
    from products.script_loader import load_product_tools
    scripts = load_product_tools("zoho_books")
    result = filter_connector_tools(scripts, mode="developer")
    assert len(result) == 40


def test_customer_mode_hides_zb_scripts():
    from products.script_loader import load_product_tools
    scripts = load_product_tools("zoho_books")
    result = filter_connector_tools(scripts, mode="customer")
    assert len(result) == 0


def test_customer_mode_hides_list_invoices_and_expenses():
    from connectors.zoho_books.tools import ZOHO_BOOKS_TOOLS
    tools = [{"name": t["name"], "fn": t["fn"], "description": t["description"], "params": {}} for t in ZOHO_BOOKS_TOOLS]
    result = filter_connector_tools(tools, mode="customer")
    names = {t["name"] for t in result}
    assert "zoho_books_list_invoices" not in names
    assert "zoho_books_list_expenses" not in names
    assert "zoho_books_get_invoice" in names
    assert len(result) == 43


# ---------------------------------------------------------------------------
# _ALIASES coverage — all 40 scripts present
# ---------------------------------------------------------------------------

def test_aliases_cover_all_40_scripts():
    import os
    scripts_dir = Path(__file__).parent.parent / "products" / "zoho_books"
    script_names = {
        f.stem for f in scripts_dir.glob("*.py")
        if not f.name.startswith("_")
    }
    missing = script_names - set(_ALIASES.keys())
    assert not missing, f"Scripts missing from _ALIASES: {missing}"


if __name__ == "__main__":
    test_customer_mode_has_43_names()
    test_customer_mode_includes_auth_tools()
    test_customer_mode_includes_cud_tools()
    test_customer_mode_excludes_heavy_list_tools()
    test_customer_mode_exposes_safe_lookup_tools()
    test_filter_developer_mode_returns_all()
    test_filter_customer_mode_keeps_cud_only()
    test_filter_customer_mode_excludes_report_scripts()
    test_filter_customer_mode_small_count()
    test_dedupe_tools_keeps_last_definition()
    test_classify_ar_aging()
    test_classify_plain_receivables()
    test_classify_who_owes_me_money()
    test_classify_profit_loss()
    test_classify_cash_position()
    test_classify_overdue_invoices()
    test_classify_gst()
    test_classify_authenticate()
    test_classify_capabilities()
    test_classify_write_create()
    test_classify_write_update()
    test_classify_write_delete()
    test_classify_unknown()
    test_match_report_p_and_l()
    test_match_report_tds()
    test_match_report_top_customers()
    test_match_report_inventory()
    test_match_report_none()
    test_resolve_alias_zb_prefix()
    test_resolve_alias_plain_name()
    test_resolve_alias_phrase()
    test_resolve_alias_unknown()
    test_router_tools_has_four()
    test_router_tool_names()
    test_router_tools_all_have_fn()
    test_router_tools_all_have_mcp_input_schema()
    test_capabilities_returns_catalog()
    test_capabilities_catalog_has_categories()
    test_capabilities_catalog_total_matches_40()
    test_assistant_missing_query()
    test_assistant_auth_error_surfaces()
    test_assistant_write_guidance()
    test_assistant_unknown_query()
    test_zoho_report_missing_report_param()
    test_zoho_report_unknown_name()
    test_zoho_report_valid_name_hits_auth()
    test_write_intent_guidance_mentions_lookup()
    test_write_intent_guidance_mentions_confirm()
    test_write_intent_guidance_mentions_never_guess()
    test_write_intent_guidance_has_workflow_key()
    test_action_tool_missing_intent()
    test_action_tool_unknown_intent()
    test_action_create_invoice_missing_params()
    test_action_create_invoice_requires_confirmation()
    test_action_delete_invoice_requires_confirmation()
    test_action_confirmed_delete_hits_auth()
    test_action_list_invoices_hits_auth()
    test_action_list_expenses_hits_auth()
    test_action_find_customer_activity_missing_name()
    test_compact_records_limits_and_strips_fields()
    test_compact_records_unknown_entity_returns_full()
    test_match_action_intent_create_invoice()
    test_match_action_intent_delete_contact()
    test_match_action_intent_list_invoices()
    test_match_action_intent_no_match()
    test_customer_mode_action_tool_in_router()
    test_action_tool_has_mcp_schema()
    test_cud_descriptions_contain_never_guess()
    test_cud_tool_count_is_27()
    test_developer_mode_exposes_all_raw_tools()
    test_developer_mode_exposes_all_zb_scripts()
    test_customer_mode_hides_zb_scripts()
    test_customer_mode_hides_list_invoices_and_expenses()
    test_aliases_cover_all_40_scripts()
    print("\nAll tool mode tests passed.")
