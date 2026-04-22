"""Expense Summary — expenses for period grouped by category."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount, filter_by_period,
    totals_by_currency, format_currency, group_amounts, success_response, error_response,
    _MULTI_CURRENCY_WARNING, _ACCURACY_NOTE,
)

TOOL_NAME = "zb_expense_summary"
TOOL_DESCRIPTION = (
    "Returns an Expense Summary for a given period from Zoho Books. "
    "Use for 'Show expenses this month', 'What did we spend on?', 'Expense breakdown'. "
    "OPERATIONAL ESTIMATE — expense totals from list API. Verify before filings. "
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

    totals = totals_by_currency(exp_records, _AMT_FIELDS)
    by_category = group_amounts(exp_records, ["account_name"], _AMT_FIELDS, 10)

    all_codes = set(totals)
    multi_currency = len(all_codes) > 1
    if multi_currency:
        warnings.append(_MULTI_CURRENCY_WARNING)

    reimbursable = [r for r in exp_records if r.get("is_billable") or r.get("reimbursable")]
    reimbursable_totals = totals_by_currency(reimbursable, _AMT_FIELDS)

    return success_response(
        report="Expense Summary (Estimate)",
        records_processed=len(exp_records), records_returned=len(totals),
        narrative_cue=(
            f"Expense summary for {period}: {len(exp_records)} expenses. "
            + ("Narrate each currency separately. " if multi_currency else "")
            + "State this is an operational estimate."
        ),
        period=period, date_range={"from": from_str, "to": to_str},
        expense_count=len(exp_records),
        totals_by_currency=totals,
        by_category=by_category,
        reimbursable_count=len(reimbursable),
        reimbursable_totals_by_currency=reimbursable_totals,
        multi_currency=multi_currency,
        report_basis="operational_estimate_from_expenses",
        accuracy_note=_ACCURACY_NOTE, warnings=warnings,
    )
