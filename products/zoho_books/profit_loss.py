"""Profit & Loss — operational estimate from invoices and expenses."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, filter_by_period,
    totals_by_currency, format_currency, success_response, error_response,
    _MULTI_CURRENCY_WARNING, _ACCURACY_NOTE,
)

TOOL_NAME = "zb_profit_loss"
TOOL_DESCRIPTION = (
    "Returns an estimated Profit & Loss summary for Zoho Books. "
    "Use for 'What is my P&L this month?', 'Estimated profit or loss', 'Revenue vs expenses'. "
    "OPERATIONAL ESTIMATE ONLY — not a statutory P&L. Verify before filings. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "period": {"type": "string",
                "description": "Time period: this_month, last_month, this_quarter, this_year, last_year. Default: this_month."},
    "limit": {"type": "integer",
               "description": "Maximum records per source. Default: 200. Hard-capped at 500."},
}

_INV_AMOUNT = ["total", "invoice_total", "bcy_total", "amount", "total_amount"]
_EXP_AMOUNT = ["total", "amount", "bcy_total"]
_DATE_FIELDS = ["date", "invoice_date", "created_time"]


def run(params: dict) -> dict:
    period = params.get("period", "this_month")
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    warnings = []
    income_records, expense_records = [], []

    try:
        inv_result = connector.list_invoices(limit=limit)
        all_inv = extract_records(inv_result, ["invoices"])
        income_records, no_d, from_str, to_str = filter_by_period(all_inv, _DATE_FIELDS, period)
        if no_d:
            warnings.append(f"{no_d} invoice(s) had no date and were included without period filtering.")
    except Exception as e:
        warnings.append(f"Could not fetch invoices: {e}")
        from_str = to_str = ""

    try:
        exp_result = connector.list_expenses(limit=limit)
        all_exp = extract_records(exp_result, ["expenses"])
        expense_records, no_d, from_str, to_str = filter_by_period(all_exp, _DATE_FIELDS, period)
        if no_d:
            warnings.append(f"{no_d} expense(s) had no date and were included without period filtering.")
    except Exception as e:
        warnings.append(f"Could not fetch expenses: {e}")

    income_by_currency = totals_by_currency(income_records, _INV_AMOUNT)
    expense_by_currency = totals_by_currency(expense_records, _EXP_AMOUNT)

    all_codes = set(income_by_currency) | set(expense_by_currency)
    multi_currency = len(all_codes) > 1
    if multi_currency:
        warnings.append(_MULTI_CURRENCY_WARNING)

    net_by_currency = {
        code: {
            "income": income_by_currency.get(code, {}).get("amount", 0.0),
            "expenses": expense_by_currency.get(code, {}).get("amount", 0.0),
            "net": income_by_currency.get(code, {}).get("amount", 0.0) - expense_by_currency.get(code, {}).get("amount", 0.0),
        }
        for code in all_codes
    }
    for code, vals in net_by_currency.items():
        vals["income_formatted"] = format_currency(vals["income"], code)
        vals["expenses_formatted"] = format_currency(vals["expenses"], code)
        vals["net_formatted"] = format_currency(vals["net"], code)

    return success_response(
        report="Profit & Loss (Estimate)", records_processed=len(income_records) + len(expense_records),
        records_returned=len(net_by_currency),
        narrative_cue=(
            f"P&L estimate for {period}: {len(income_records)} invoices, {len(expense_records)} expenses. "
            + ("Narrate net for each currency separately. " if multi_currency else "")
            + "State this is an estimate — not a statutory P&L."
        ),
        period=period, date_range={"from": from_str, "to": to_str},
        income_by_currency=income_by_currency, expense_by_currency=expense_by_currency,
        estimated_net_by_currency=net_by_currency, multi_currency=multi_currency,
        report_basis="operational_estimate_from_invoices_and_expenses",
        accuracy_note=_ACCURACY_NOTE, warnings=warnings,
    )
