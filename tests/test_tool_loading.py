"""Test Zoho Books tool loading — all 51 tools present, no CRM tools."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

REQUIRED_TOOLS = [
    "zoho_books_authenticate",
    "zoho_books_connection_status",
    "zoho_books_list_organizations",
    "zoho_books_get_organization",
    "zoho_books_list_contacts",
    "zoho_books_get_contact",
    "zoho_books_create_contact",
    "zoho_books_update_contact",
    "zoho_books_delete_contact",
    "zoho_books_list_invoices",
    "zoho_books_get_invoice",
    "zoho_books_create_invoice",
    "zoho_books_update_invoice",
    "zoho_books_delete_invoice",
    "zoho_books_list_estimates",
    "zoho_books_get_estimate",
    "zoho_books_create_estimate",
    "zoho_books_update_estimate",
    "zoho_books_delete_estimate",
    "zoho_books_list_sales_orders",
    "zoho_books_get_sales_order",
    "zoho_books_create_sales_order",
    "zoho_books_update_sales_order",
    "zoho_books_delete_sales_order",
    "zoho_books_list_purchase_orders",
    "zoho_books_get_purchase_order",
    "zoho_books_create_purchase_order",
    "zoho_books_update_purchase_order",
    "zoho_books_delete_purchase_order",
    "zoho_books_list_expenses",
    "zoho_books_get_expense",
    "zoho_books_create_expense",
    "zoho_books_update_expense",
    "zoho_books_delete_expense",
    "zoho_books_list_items",
    "zoho_books_get_item",
    "zoho_books_create_item",
    "zoho_books_update_item",
    "zoho_books_delete_item",
    "zoho_books_list_taxes",
    "zoho_books_get_tax",
    "zoho_books_create_tax",
    "zoho_books_update_tax",
    "zoho_books_delete_tax",
    "zoho_books_list_customer_payments",
    "zoho_books_get_customer_payment",
    "zoho_books_create_customer_payment",
    "zoho_books_update_customer_payment",
    "zoho_books_delete_customer_payment",
    "zoho_books_list_users",
    "zoho_books_get_user",
]

CRM_TOOLS_MUST_NOT_EXIST = [
    "zoho_crm_get_leads",
    "zoho_crm_get_contacts",
    "get_leads",
    "get_contacts",
    "get_deals",
    "create_zoho_invoice",
]


def test_all_51_zoho_books_tools_present():
    """ZOHO_BOOKS_TOOLS must contain all 51 required tools."""
    from connectors.zoho_books.tools import ZOHO_BOOKS_TOOLS
    tool_names = {t["name"] for t in ZOHO_BOOKS_TOOLS}
    missing = [t for t in REQUIRED_TOOLS if t not in tool_names]
    assert not missing, f"Missing tools: {missing}"
    assert len(ZOHO_BOOKS_TOOLS) == 51, f"Expected 51 tools, got {len(ZOHO_BOOKS_TOOLS)}"
    print(f"PASS: test_all_51_zoho_books_tools_present ({len(ZOHO_BOOKS_TOOLS)} tools)")


def test_no_crm_tools_loaded():
    """No CRM tool names should appear in ZOHO_BOOKS_TOOLS."""
    from connectors.zoho_books.tools import ZOHO_BOOKS_TOOLS
    tool_names = {t["name"] for t in ZOHO_BOOKS_TOOLS}
    found_crm = [t for t in CRM_TOOLS_MUST_NOT_EXIST if t in tool_names]
    assert not found_crm, f"CRM tools found in Zoho Books tools: {found_crm}"
    print("PASS: test_no_crm_tools_loaded")


def test_all_tools_have_required_fields():
    """Every tool must have name, description, input_schema, fn."""
    from connectors.zoho_books.tools import ZOHO_BOOKS_TOOLS
    for tool in ZOHO_BOOKS_TOOLS:
        assert "name" in tool, f"Tool missing 'name': {tool}"
        assert "description" in tool, f"Tool '{tool['name']}' missing 'description'"
        assert "input_schema" in tool, f"Tool '{tool['name']}' missing 'input_schema'"
        assert "fn" in tool, f"Tool '{tool['name']}' missing 'fn'"
        assert callable(tool["fn"]), f"Tool '{tool['name']}' fn is not callable"
    print("PASS: test_all_tools_have_required_fields")


def test_delete_tools_have_id_required():
    """Delete tools must require their entity ID field."""
    from connectors.zoho_books.tools import ZOHO_BOOKS_TOOLS
    delete_tools = [t for t in ZOHO_BOOKS_TOOLS if t["name"].startswith("zoho_books_delete_")]
    for tool in delete_tools:
        schema = tool["input_schema"]
        required = schema.get("required", [])
        props = schema.get("properties", {})
        id_fields = [k for k in props if k.endswith("_id") and k != "organization_id"]
        assert len(id_fields) >= 1, f"Delete tool {tool['name']} has no ID field in properties"
        for idf in id_fields:
            assert idf in required, \
                f"Delete tool {tool['name']}: '{idf}' must be in required"
    print(f"PASS: test_delete_tools_have_id_required ({len(delete_tools)} delete tools checked)")


def test_create_tools_have_required_fields():
    """Create tools must have at least one required field."""
    from connectors.zoho_books.tools import ZOHO_BOOKS_TOOLS
    create_tools = [t for t in ZOHO_BOOKS_TOOLS if t["name"].startswith("zoho_books_create_")]
    for tool in create_tools:
        schema = tool["input_schema"]
        required = schema.get("required", [])
        assert len(required) >= 1, \
            f"Create tool {tool['name']} has no required fields"
    print(f"PASS: test_create_tools_have_required_fields ({len(create_tools)} create tools checked)")


def test_tools_list_from_main_contains_only_books():
    """Full tool list from main build must contain 51 zoho_books_* tools and no CRM tools."""
    from config.settings import load_selected_connectors
    selected = load_selected_connectors()
    assert selected == ["zoho_books"], f"Expected ['zoho_books'], got {selected}"

    from connectors.zoho_books.tools import ZOHO_BOOKS_TOOLS
    from tools.skill_tools import SKILL_TOOLS
    from tools.health_tools import HEALTH_TOOLS
    from tools.platform_tools import PLATFORM_TOOLS

    all_tools = ZOHO_BOOKS_TOOLS + SKILL_TOOLS + HEALTH_TOOLS + PLATFORM_TOOLS
    all_names = {t["name"] for t in all_tools}

    for crm_name in CRM_TOOLS_MUST_NOT_EXIST:
        assert crm_name not in all_names, \
            f"CRM tool '{crm_name}' found in full tool list"

    books_count = sum(1 for n in all_names if n.startswith("zoho_books_"))
    assert books_count == 51, f"Expected 51 zoho_books_* tools, got {books_count}"
    print(f"PASS: test_tools_list_from_main_contains_only_books ({len(all_tools)} total tools)")


def test_zoho_mcp_not_imported():
    """zoho_mcp package must not be imported by any active module."""
    from connectors.zoho_books.tools import ZOHO_BOOKS_TOOLS
    from connectors.zoho_books.connector import ZohoBooksConnector
    assert "zoho_mcp" not in sys.modules, \
        "zoho_mcp should not be imported (dependency removed)"
    print("PASS: test_zoho_mcp_not_imported")


if __name__ == "__main__":
    test_all_51_zoho_books_tools_present()
    test_no_crm_tools_loaded()
    test_all_tools_have_required_fields()
    test_delete_tools_have_id_required()
    test_create_tools_have_required_fields()
    test_tools_list_from_main_contains_only_books()
    test_zoho_mcp_not_imported()
    print("\nAll tool loading tests passed.")
