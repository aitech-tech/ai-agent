"""Sales Orders Summary — open and all orders grouped by status."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount,
    totals_by_currency, format_currency, success_response, error_response,
    _MULTI_CURRENCY_WARNING,
)

TOOL_NAME = "zb_sales_orders_summary"
TOOL_DESCRIPTION = (
    "Returns a Sales Orders Summary from Zoho Books. "
    "Use for 'Show sales orders', 'Open orders', 'Sales order pipeline'. "
    "Returns order counts and values grouped by status and currency. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "limit": {"type": "integer",
               "description": "Max records. Default: 200. Hard-capped at 500."},
}

_AMT_FIELDS = ["total", "salesorder_total", "bcy_total", "amount"]
_OPEN_STATUSES = {"draft", "open", "confirmed", "partially_invoiced"}


def run(params: dict) -> dict:
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    warnings = []
    try:
        records = extract_records(connector.list_salesorders(limit=limit), ["salesorders", "sales_orders"])
    except Exception as e:
        return error_response("fetch_failed", str(e))

    by_status: dict = {}
    for rec in records:
        status = str(rec.get("status") or "unknown").lower()
        amt = safe_amount(rec, _AMT_FIELDS)
        code = rec.get("currency_code") or "INR"
        if status not in by_status:
            by_status[status] = {"count": 0, "amount": 0.0, "currency_code": code}
        by_status[status]["count"] += 1
        by_status[status]["amount"] += amt

    open_records = [r for r in records if str(r.get("status") or "").lower() in _OPEN_STATUSES]
    open_totals = totals_by_currency(open_records, _AMT_FIELDS)
    all_totals = totals_by_currency(records, _AMT_FIELDS)

    all_codes = set(all_totals)
    multi_currency = len(all_codes) > 1
    if multi_currency:
        warnings.append(_MULTI_CURRENCY_WARNING)

    return success_response(
        report="Sales Orders Summary",
        records_processed=len(records), records_returned=len(by_status),
        narrative_cue=(
            f"{len(records)} sales orders across {len(by_status)} statuses. "
            f"{len(open_records)} open/active orders. "
            + ("Narrate each currency separately. " if multi_currency else "")
        ),
        total_orders=len(records), open_order_count=len(open_records),
        by_status=by_status,
        open_orders_totals_by_currency=open_totals,
        totals_by_currency=all_totals,
        multi_currency=multi_currency, warnings=warnings,
    )
