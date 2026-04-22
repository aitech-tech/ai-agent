"""Sales Summary — invoices for period: totals, paid, outstanding."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount, filter_by_period,
    totals_by_currency, format_currency, success_response, error_response,
    _MULTI_CURRENCY_WARNING, _ACCURACY_NOTE,
)

TOOL_NAME = "zb_sales_summary"
TOOL_DESCRIPTION = (
    "Returns a Sales Summary for a given period from Zoho Books. "
    "Use for 'Show sales this month', 'How much did we sell?', 'Sales summary'. "
    "OPERATIONAL ESTIMATE — invoice totals from list API. Verify before filings. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "period": {"type": "string",
                "description": "Period: this_month, last_month, this_quarter, this_year, last_year. Default: this_month."},
    "limit": {"type": "integer",
               "description": "Max records. Default: 200. Hard-capped at 500."},
}

_INV_AMOUNT = ["total", "invoice_total", "bcy_total", "amount", "total_amount"]
_PAID_FIELDS = ["amount_applied", "paid_amount", "payment_made"]
_DUE_FIELDS = ["balance", "outstanding_amount", "due_amount"]
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

    totals = totals_by_currency(inv_records, _INV_AMOUNT)
    paid_totals = totals_by_currency(inv_records, _PAID_FIELDS)
    due_totals = totals_by_currency(inv_records, _DUE_FIELDS)

    all_codes = set(totals)
    multi_currency = len(all_codes) > 1
    if multi_currency:
        warnings.append(_MULTI_CURRENCY_WARNING)

    per_currency = {}
    for code in all_codes:
        total = totals.get(code, {}).get("amount", 0.0)
        paid = paid_totals.get(code, {}).get("amount", 0.0)
        due = due_totals.get(code, {}).get("amount", 0.0)
        count = totals.get(code, {}).get("count", 0)
        avg = total / count if count else 0.0
        per_currency[code] = {
            "invoice_count": count,
            "total": total, "total_formatted": format_currency(total, code),
            "paid": paid, "paid_formatted": format_currency(paid, code),
            "outstanding": due, "outstanding_formatted": format_currency(due, code),
            "avg_invoice_value": avg, "avg_invoice_value_formatted": format_currency(avg, code),
        }

    return success_response(
        report="Sales Summary (Estimate)",
        records_processed=len(inv_records), records_returned=len(per_currency),
        narrative_cue=(
            f"Sales summary for {period}: {len(inv_records)} invoices. "
            + ("Narrate each currency separately. " if multi_currency else "")
            + "State this is an operational estimate."
        ),
        period=period, date_range={"from": from_str, "to": to_str},
        sales_by_currency=per_currency, totals_by_currency=totals,
        multi_currency=multi_currency,
        report_basis="operational_estimate_from_invoices",
        accuracy_note=_ACCURACY_NOTE, warnings=warnings,
    )
