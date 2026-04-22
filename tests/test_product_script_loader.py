"""Tests for products/script_loader.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from products.script_loader import load_product_tools, make_safe_fn


EXPECTED_TOOL_NAMES = {
    "zb_ar_aging",
    "zb_overdue_invoices",
    "zb_invoice_summary",
    "zb_expense_by_category",
    "zb_customer_balances",
}


def test_loads_5_zoho_books_tools():
    """load_product_tools('zoho_books') must return exactly 5 tools."""
    tools = load_product_tools("zoho_books")
    assert len(tools) == 5, f"Expected 5 tools, got {len(tools)}: {[t['name'] for t in tools]}"
    print(f"PASS: test_loads_5_zoho_books_tools ({len(tools)} tools)")


def test_all_tool_names_start_with_zb():
    """All loaded tool names must start with zb_."""
    tools = load_product_tools("zoho_books")
    bad = [t["name"] for t in tools if not t["name"].startswith("zb_")]
    assert not bad, f"Tools with non-zb_ names: {bad}"
    print("PASS: test_all_tool_names_start_with_zb")


def test_tool_names_are_expected():
    """Loaded tool names must exactly match the 5 implemented scripts."""
    tools = load_product_tools("zoho_books")
    names = {t["name"] for t in tools}
    missing = EXPECTED_TOOL_NAMES - names
    extra = names - EXPECTED_TOOL_NAMES
    assert not missing, f"Missing tools: {missing}"
    assert not extra, f"Unexpected tools: {extra}"
    print(f"PASS: test_tool_names_are_expected ({names})")


def test_tool_names_are_unique():
    """Tool names must be unique."""
    tools = load_product_tools("zoho_books")
    names = [t["name"] for t in tools]
    duplicates = [n for n in names if names.count(n) > 1]
    assert not duplicates, f"Duplicate tool names: {set(duplicates)}"
    print("PASS: test_tool_names_are_unique")


def test_tools_sorted_by_name():
    """load_product_tools must return tools sorted by name."""
    tools = load_product_tools("zoho_books")
    names = [t["name"] for t in tools]
    assert names == sorted(names), f"Tools not sorted: {names}"
    print("PASS: test_tools_sorted_by_name")


def test_each_tool_has_required_fields():
    """Every tool dict must have name, description, input_schema, fn."""
    tools = load_product_tools("zoho_books")
    for tool in tools:
        assert "name" in tool, f"Tool missing 'name': {tool}"
        assert "description" in tool, f"Tool '{tool['name']}' missing 'description'"
        assert "input_schema" in tool, f"Tool '{tool['name']}' missing 'input_schema'"
        assert "fn" in tool, f"Tool '{tool['name']}' missing 'fn'"
        assert callable(tool["fn"]), f"Tool '{tool['name']}' fn is not callable"
    print(f"PASS: test_each_tool_has_required_fields ({len(tools)} tools checked)")


def test_input_schema_structure():
    """input_schema must have type=object, properties dict, required list."""
    tools = load_product_tools("zoho_books")
    for tool in tools:
        schema = tool["input_schema"]
        assert schema.get("type") == "object", \
            f"Tool '{tool['name']}' schema type must be 'object'"
        assert isinstance(schema.get("properties"), dict), \
            f"Tool '{tool['name']}' schema properties must be a dict"
        assert isinstance(schema.get("required"), list), \
            f"Tool '{tool['name']}' schema required must be a list"
    print(f"PASS: test_input_schema_structure ({len(tools)} tools)")


# ---------------------------------------------------------------------------
# make_safe_fn tests
# ---------------------------------------------------------------------------

def test_make_safe_fn_handles_exception():
    """make_safe_fn must catch exceptions and return error dict."""
    def bad_run(params):
        raise ValueError("test explosion")

    fn = make_safe_fn("zb_test", bad_run)
    result = fn({})
    assert result["success"] is False
    assert result["error"] == "script_exception"
    assert "test explosion" in result["message"]
    assert result["raw_data_returned"] is False
    print("PASS: test_make_safe_fn_handles_exception")


def test_make_safe_fn_handles_non_dict_return():
    """make_safe_fn must handle scripts that return non-dict."""
    def bad_run(params):
        return ["not", "a", "dict"]

    fn = make_safe_fn("zb_test", bad_run)
    result = fn({})
    assert result["success"] is False
    assert result["error"] == "invalid_script_result"
    assert result["raw_data_returned"] is False
    print("PASS: test_make_safe_fn_handles_non_dict_return")


def test_make_safe_fn_sets_defaults():
    """make_safe_fn must set success=True and tool=tool_name if missing."""
    def minimal_run(params):
        return {"report": "Test"}

    fn = make_safe_fn("zb_test_tool", minimal_run)
    result = fn({})
    assert result["success"] is True
    assert result["tool"] == "zb_test_tool"
    assert result["report"] == "Test"
    print("PASS: test_make_safe_fn_sets_defaults")


def test_make_safe_fn_passes_params():
    """make_safe_fn must pass params through to run()."""
    received = {}

    def capture_run(params):
        received.update(params)
        return {"report": "OK"}

    fn = make_safe_fn("zb_test", capture_run)
    fn({"limit": 50, "period": "this_month"})
    assert received.get("limit") == 50
    assert received.get("period") == "this_month"
    print("PASS: test_make_safe_fn_passes_params")


def test_make_safe_fn_none_params_becomes_empty_dict():
    """make_safe_fn must convert None params to {}."""
    received = {}

    def capture_run(params):
        received["params"] = params
        return {"report": "OK"}

    fn = make_safe_fn("zb_test", capture_run)
    fn(None)
    assert received["params"] == {}
    print("PASS: test_make_safe_fn_none_params_becomes_empty_dict")


if __name__ == "__main__":
    test_loads_5_zoho_books_tools()
    test_all_tool_names_start_with_zb()
    test_tool_names_are_expected()
    test_tool_names_are_unique()
    test_tools_sorted_by_name()
    test_each_tool_has_required_fields()
    test_input_schema_structure()
    test_make_safe_fn_handles_exception()
    test_make_safe_fn_handles_non_dict_return()
    test_make_safe_fn_sets_defaults()
    test_make_safe_fn_passes_params()
    test_make_safe_fn_none_params_becomes_empty_dict()
    print("\nAll script loader tests passed.")
