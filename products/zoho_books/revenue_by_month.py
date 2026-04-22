"""Revenue by Month — monthly invoice revenue trend."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, filter_by_period, group_by_month,
    totals_by_currency, format_currency, success_response, error_response,
    _MULTI_CURRENCY_WARNING,
)

TOOL_NAME = "zb_revenue_by_month"
TOOL_DESCRIPTION = (
    "Returns a pre-processed Revenue by Month trend for Zoho Books. "
    "Use for 'Show monthly revenue', 'Revenue trend this year', 'Best month for sales'. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "period": {"type": "string",
                "description": "Time period: this_year, last_year, this_quarter, last_quarter. Default: this_year."},
    "limit": {"type": "integer",
               "description": "Maximum invoices to process. Default: 500. Hard-capped at 500."},
}

_AMOUNT_FIELDS = ["total", "invoice_total", "bcy_total", "amount", "total_amount"]
_DATE_FIELDS = ["date", "invoice_date", "created_time"]


def run(params: dict) -> dict:
    period = params.get("period", "this_year")
    limit = cap_int(params.get("limit", 500), default=500, minimum=1, maximum=500)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))
    try:
        result = connector.list_invoices(limit=limit)
    except Exception as e:
        return error_response("fetch_failed", str(e))

    all_records = extract_records(result, ["invoices"])
    filtered, no_date_count, from_str, to_str = filter_by_period(all_records, _DATE_FIELDS, period)

    warnings = []
    if no_date_count:
        warnings.append(f"{no_date_count} invoice(s) had no date and were excluded from monthly grouping.")

    if not filtered:
        return success_response(
            report="Revenue by Month", records_processed=0, records_returned=0,
            narrative_cue=f"No invoices found for period '{period}'.",
            period=period, date_range={"from": from_str, "to": to_str},
            monthly=[], best_month=None, totals_by_currency={},
            multi_currency=False, warnings=warnings,
        )

    by_currency = totals_by_currency(filtered, _AMOUNT_FIELDS)
    multi_currency = len(by_currency) > 1
    if multi_currency:
        warnings.append(_MULTI_CURRENCY_WARNING)

    monthly = group_by_month(filtered, _DATE_FIELDS, _AMOUNT_FIELDS)
    best_month = max(monthly, key=lambda m: m["amount"]) if monthly else None

    single_total = sum(v["amount"] for v in by_currency.values()) if not multi_currency else None
    single_code = next(iter(by_currency)) if by_currency else "INR"

    return success_response(
        report="Revenue by Month", records_processed=len(filtered), records_returned=len(monthly),
        narrative_cue=(
            f"{len(filtered)} invoices for {period} across {len(monthly)} months"
            + (f". Total: {format_currency(single_total, single_code)}. " if not multi_currency else " (multiple currencies). ")
            + (f"Best month: {best_month['month']} ({best_month['amount_formatted']}). " if best_month else "")
            + "Narrate monthly trend and highlight best/worst months."
        ),
        period=period, date_range={"from": from_str, "to": to_str},
        total_revenue=single_total, monthly=monthly, best_month=best_month,
        totals_by_currency=by_currency, multi_currency=multi_currency, warnings=warnings,
    )
