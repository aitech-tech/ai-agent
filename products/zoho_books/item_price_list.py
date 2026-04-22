"""Item Price List — catalog of items with rates (capped at 50)."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount,
    format_currency, success_response, error_response,
)

TOOL_NAME = "zb_item_price_list"
TOOL_DESCRIPTION = (
    "Returns a price list of items from Zoho Books (capped at 50 items). "
    "Use for 'Show item prices', 'What is the price of X?', 'Product catalog'. "
    "Returns name, rate, purchase rate, and product type for each item. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "limit": {"type": "integer",
               "description": "Max items to return. Default: 50. Hard-capped at 50."},
}

_RATE_FIELDS = ["rate", "selling_price", "sales_rate"]
_PURCH_FIELDS = ["purchase_rate", "purchase_price", "cost_price"]


def run(params: dict) -> dict:
    limit = cap_int(params.get("limit", 50), default=50, minimum=1, maximum=50)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    try:
        records = extract_records(connector.list_items(limit=limit), ["items"])
    except Exception as e:
        return error_response("fetch_failed", str(e))

    items = []
    for rec in records[:limit]:
        rate = safe_amount(rec, _RATE_FIELDS)
        purchase_rate = safe_amount(rec, _PURCH_FIELDS)
        code = rec.get("currency_code") or "INR"
        items.append({
            "item_id": rec.get("item_id") or rec.get("id") or "",
            "name": rec.get("name") or "Unknown",
            "sku": rec.get("sku") or "",
            "product_type": rec.get("product_type") or "goods",
            "currency_code": code,
            "rate": rate,
            "rate_formatted": format_currency(rate, code),
            "purchase_rate": purchase_rate,
            "purchase_rate_formatted": format_currency(purchase_rate, code) if purchase_rate else None,
            "unit": rec.get("unit") or "",
            "is_active": rec.get("status") != "inactive",
        })

    service_count = sum(1 for i in items if i.get("product_type") == "service")
    goods_count = len(items) - service_count

    return success_response(
        report="Item Price List",
        records_processed=len(records), records_returned=len(items),
        narrative_cue=(
            f"{len(items)} items: {goods_count} goods, {service_count} services. "
            "List each item with its rate. Note this is the catalog rate — actual invoice rates may differ."
        ),
        item_count=len(items), goods_count=goods_count, service_count=service_count,
        items=items,
        warnings=[] if len(records) <= limit else [f"Only first {limit} items shown."],
    )
