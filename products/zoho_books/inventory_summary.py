"""Inventory Summary — stock levels and estimated inventory value."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount,
    totals_by_currency, format_currency, success_response, error_response,
    _MULTI_CURRENCY_WARNING, _ACCURACY_NOTE,
)

TOOL_NAME = "zb_inventory_summary"
TOOL_DESCRIPTION = (
    "Returns an Inventory Summary from Zoho Books. "
    "Use for 'Show inventory', 'What stock do we have?', 'Inventory value'. "
    "Returns stock levels, estimated value (rate × stock_on_hand), and low-stock alerts. "
    "OPERATIONAL ESTIMATE — value from list API fields. Verify in Zoho Books. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "limit": {"type": "integer",
               "description": "Max item records. Default: 200. Hard-capped at 500."},
}

_RATE_FIELDS = ["rate", "purchase_rate", "selling_price"]
_STOCK_FIELDS = ["stock_on_hand", "available_stock", "quantity"]


def run(params: dict) -> dict:
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    warnings = []
    try:
        records = extract_records(connector.list_items(limit=limit), ["items"])
    except Exception as e:
        return error_response("fetch_failed", str(e))

    inventory_items = [r for r in records if r.get("product_type") != "service"]
    value_by_currency: dict = {}
    low_stock = []

    for item in inventory_items:
        rate = safe_amount(item, _RATE_FIELDS)
        stock = safe_amount(item, _STOCK_FIELDS)
        val = rate * stock
        code = item.get("currency_code") or "INR"
        value_by_currency[code] = value_by_currency.get(code, 0.0) + val

        reorder = safe_amount(item, ["reorder_level", "minimum_stock"])
        if reorder and stock <= reorder:
            low_stock.append({
                "name": item.get("name") or "Unknown",
                "stock_on_hand": stock,
                "reorder_level": reorder,
            })

    multi_currency = len(value_by_currency) > 1
    if multi_currency:
        warnings.append(_MULTI_CURRENCY_WARNING)

    value_formatted = {code: format_currency(v, code) for code, v in value_by_currency.items()}

    out_of_stock = [r for r in inventory_items if safe_amount(r, _STOCK_FIELDS) == 0]
    low_stock.sort(key=lambda x: x["stock_on_hand"])

    return success_response(
        report="Inventory Summary",
        records_processed=len(records), records_returned=len(inventory_items),
        narrative_cue=(
            f"{len(inventory_items)} inventory items (from {len(records)} total). "
            f"{len(out_of_stock)} out of stock, {len(low_stock)} at or below reorder level. "
            + ("Narrate each currency separately. " if multi_currency else "")
            + "State inventory value is an estimate from rate × stock_on_hand."
        ),
        item_count=len(records), inventory_item_count=len(inventory_items),
        out_of_stock_count=len(out_of_stock),
        low_stock_count=len(low_stock),
        low_stock_items=low_stock[:10],
        estimated_value_by_currency=value_by_currency,
        estimated_value_formatted=value_formatted,
        multi_currency=multi_currency,
        report_basis="operational_estimate_from_items_list",
        accuracy_note=_ACCURACY_NOTE, warnings=warnings,
    )
