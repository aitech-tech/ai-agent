"""Sales by Item — line-item breakdown from invoice list response."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount, filter_by_period,
    totals_by_currency, success_response, error_response,
    _MULTI_CURRENCY_WARNING,
)

TOOL_NAME = "zb_sales_by_item"
TOOL_DESCRIPTION = (
    "Returns a Sales by Item breakdown from Zoho Books invoices. "
    "Use for 'What items sold most?', 'Sales by product', 'Top items this month'. "
    "Note: line-item detail requires invoice detail calls — this tool only uses list-level data. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "period": {"type": "string",
                "description": "Period: this_month, last_month, this_quarter, this_year, last_year. Default: this_month."},
    "limit": {"type": "integer",
               "description": "Max invoice records. Default: 200. Hard-capped at 500."},
}

_AMT_FIELDS = ["total", "item_total", "rate", "amount"]
_INV_AMOUNT = ["total", "invoice_total", "bcy_total", "amount"]
_DATE_FIELDS = ["date", "invoice_date", "created_time"]


def run(params: dict) -> dict:
    period = params.get("period", "this_month")
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    warnings = []
    try:
        all_inv = extract_records(connector.list_invoices(limit=limit), ["invoices"])
        inv_records, no_d, from_str, to_str = filter_by_period(all_inv, _DATE_FIELDS, period)
        if no_d:
            warnings.append(f"{no_d} invoice(s) had no date and were included without period filtering.")
    except Exception as e:
        return error_response("fetch_failed", str(e))

    item_totals: dict = {}
    has_line_items = False
    for inv in inv_records:
        line_items = inv.get("line_items") or []
        if line_items:
            has_line_items = True
        for item in line_items:
            name = item.get("name") or item.get("item_name") or item.get("description") or "Unknown"
            qty = safe_amount(item, ["quantity", "qty"])
            rate = safe_amount(item, ["rate", "unit_price"])
            amt = safe_amount(item, _AMT_FIELDS) or rate * qty
            code = item.get("currency_code") or inv.get("currency_code") or "INR"
            key = name
            if key not in item_totals:
                item_totals[key] = {"count": 0, "amount": 0.0, "currency_code": code}
            item_totals[key]["count"] += 1
            item_totals[key]["amount"] += amt

    if not has_line_items:
        warnings.append("Line-item data not present in list API response. Invoice totals used instead of per-item breakdown.")
        totals = totals_by_currency(inv_records, _INV_AMOUNT)
        return success_response(
            report="Sales by Item (No Line-Item Data)",
            records_processed=len(inv_records), records_returned=0,
            narrative_cue=(
                f"No line-item data in the invoice list response for {period}. "
                "Report only invoice-level totals. "
                "To get item-level breakdown, the user must fetch each invoice individually."
            ),
            period=period, date_range={"from": from_str, "to": to_str},
            line_items_available=False, invoice_count=len(inv_records),
            invoice_totals_by_currency=totals,
            multi_currency=len(set(totals)) > 1, warnings=warnings,
        )

    top_items = sorted(item_totals.items(), key=lambda x: x[1]["amount"], reverse=True)[:10]
    top_items_list = [{"name": k, **v} for k, v in top_items]

    inv_totals = totals_by_currency(inv_records, _INV_AMOUNT)
    multi_currency = len(set(inv_totals)) > 1
    if multi_currency:
        warnings.append(_MULTI_CURRENCY_WARNING)

    return success_response(
        report="Sales by Item",
        records_processed=len(inv_records), records_returned=len(item_totals),
        narrative_cue=(
            f"Sales by item for {period}: {len(item_totals)} distinct items across {len(inv_records)} invoices. "
            + ("Narrate each currency separately. " if multi_currency else "")
        ),
        period=period, date_range={"from": from_str, "to": to_str},
        line_items_available=True,
        unique_items=len(item_totals), top_items=top_items_list,
        invoice_totals_by_currency=inv_totals,
        multi_currency=multi_currency, warnings=warnings,
    )
