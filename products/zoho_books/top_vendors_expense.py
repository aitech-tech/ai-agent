"""Top Vendors by Expense — expenses grouped by vendor for a period."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, filter_by_period,
    totals_by_currency, group_amounts, success_response, error_response,
    _MULTI_CURRENCY_WARNING,
)

TOOL_NAME = "zb_top_vendors_expense"
TOOL_DESCRIPTION = (
    "Returns top vendors ranked by expense spend for a given period in Zoho Books. "
    "Use for 'Top vendors by spend', 'Who are we spending most with?', 'Vendor expense ranking'. "
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

_AMT_FIELDS = ["total", "amount", "bcy_total"]
_DATE_FIELDS = ["date", "expense_date", "created_time"]


def run(params: dict) -> dict:
    period = params.get("period", "this_month")
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    warnings = []
    try:
        all_exp = extract_records(connector.list_expenses(limit=limit), ["expenses"])
        exp_records, no_d, from_str, to_str = filter_by_period(all_exp, _DATE_FIELDS, period)
        if no_d:
            warnings.append(f"{no_d} expense(s) had no date and were included without period filtering.")
    except Exception as e:
        return error_response("fetch_failed", str(e))

    vendor_field = next(
        (f for f in ["vendor_name", "paid_through_account_name", "merchant_name"] if any(r.get(f) for r in exp_records)),
        "vendor_name",
    )
    top_vendors = group_amounts(exp_records, [vendor_field], _AMT_FIELDS, 10)
    totals = totals_by_currency(exp_records, _AMT_FIELDS)

    multi_currency = len(set(totals)) > 1
    if multi_currency:
        warnings.append(_MULTI_CURRENCY_WARNING)

    return success_response(
        report="Top Vendors by Expense",
        records_processed=len(exp_records), records_returned=len(top_vendors),
        narrative_cue=(
            f"Top vendors by expense for {period}: {len(exp_records)} expenses. "
            + ("Narrate each currency separately. " if multi_currency else "")
        ),
        period=period, date_range={"from": from_str, "to": to_str},
        expense_count=len(exp_records),
        top_vendors=top_vendors,
        totals_by_currency=totals,
        multi_currency=multi_currency, warnings=warnings,
    )
