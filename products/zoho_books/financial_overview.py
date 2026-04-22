"""Financial Overview — one-page summary: AR, AP, revenue, expenses, cash."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount, filter_by_period,
    totals_by_currency, format_currency, success_response, error_response,
    _MULTI_CURRENCY_WARNING, _ACCURACY_NOTE,
)

TOOL_NAME = "zb_financial_overview"
TOOL_DESCRIPTION = (
    "Returns a one-page Financial Overview for Zoho Books: AR, AP, revenue, expenses, cash. "
    "Use for 'Give me a financial overview', 'How is the business doing?'. "
    "OPERATIONAL ESTIMATE — figures from list APIs, not accounting reports. Verify before filings. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "period": {"type": "string",
                "description": "Period for revenue/expense slice. Default: this_month."},
    "limit": {"type": "integer",
               "description": "Max records per source. Default: 200. Hard-capped at 500."},
}

_INV_AMOUNT = ["total", "invoice_total", "bcy_total", "amount"]
_EXP_AMOUNT = ["total", "amount", "bcy_total"]
_REC_FIELDS = ["outstanding_receivable_amount", "outstanding_receivable", "balance"]
_PAY_FIELDS = ["outstanding_payable_amount", "outstanding_payable", "balance"]
_BANK_FIELDS = ["current_balance", "balance", "amount"]
_DATE_FIELDS = ["date", "invoice_date", "created_time"]


def run(params: dict) -> dict:
    period = params.get("period", "this_month")
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    warnings = []
    inv_records = exp_records = ar_contacts = ap_contacts = bank_records = []
    from_str = to_str = ""

    try:
        all_inv = extract_records(connector.list_invoices(limit=limit), ["invoices"])
        inv_records, _, from_str, to_str = filter_by_period(all_inv, _DATE_FIELDS, period)
    except Exception as e:
        warnings.append(f"Invoice fetch failed: {e}")
    try:
        all_exp = extract_records(connector.list_expenses(limit=limit), ["expenses"])
        exp_records, _, _, _ = filter_by_period(all_exp, _DATE_FIELDS, period)
    except Exception as e:
        warnings.append(f"Expense fetch failed: {e}")
    try:
        ar_contacts = extract_records(connector.list_contacts(contact_type="customer", limit=limit), ["contacts"])
    except Exception as e:
        warnings.append(f"AR contacts fetch failed: {e}")
    try:
        ap_contacts = extract_records(connector.list_contacts(contact_type="vendor", limit=limit), ["contacts"])
    except Exception as e:
        warnings.append(f"AP contacts fetch failed: {e}")
    try:
        bank_records = extract_records(connector._get("bankaccounts", {}), ["bank_accounts", "bankaccounts"])
    except Exception as e:
        warnings.append(f"Bank accounts fetch failed: {e}")

    revenue_by_currency = totals_by_currency(inv_records, _INV_AMOUNT)
    expense_by_currency = totals_by_currency(exp_records, _EXP_AMOUNT)
    ar_by_currency = totals_by_currency(ar_contacts, _REC_FIELDS)
    ap_by_currency = totals_by_currency(ap_contacts, _PAY_FIELDS)
    cash_by_currency = totals_by_currency(bank_records, _BANK_FIELDS)

    all_codes = set(revenue_by_currency) | set(expense_by_currency) | set(ar_by_currency) | set(ap_by_currency) | set(cash_by_currency)
    multi_currency = len(all_codes) > 1
    if multi_currency:
        warnings.append(_MULTI_CURRENCY_WARNING)

    working_capital = {}
    for code in all_codes:
        ar = ar_by_currency.get(code, {}).get("amount", 0.0)
        ap = ap_by_currency.get(code, {}).get("amount", 0.0)
        cash = cash_by_currency.get(code, {}).get("amount", 0.0)
        working_capital[code] = {
            "value": ar + cash - ap,
            "formatted": format_currency(ar + cash - ap, code),
        }

    return success_response(
        report="Financial Overview (Estimate)",
        records_processed=len(inv_records) + len(exp_records) + len(ar_contacts) + len(ap_contacts),
        records_returned=len(all_codes),
        narrative_cue=(
            f"Financial overview for {period}. "
            + ("Multiple currencies — narrate each separately. " if multi_currency else "")
            + "Summarise AR, AP, revenue, expenses, cash. State this is an operational estimate."
        ),
        period=period, date_range={"from": from_str, "to": to_str},
        revenue_by_currency=revenue_by_currency, expense_by_currency=expense_by_currency,
        ar_by_currency=ar_by_currency, ap_by_currency=ap_by_currency,
        cash_by_currency=cash_by_currency, working_capital_by_currency=working_capital,
        multi_currency=multi_currency,
        report_basis="operational_estimate_from_invoices_expenses_contacts_bankaccounts",
        accuracy_note=_ACCURACY_NOTE, warnings=warnings,
    )
