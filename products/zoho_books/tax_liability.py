"""Tax Liability — estimated tax collected/paid from invoices and expenses."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount, filter_by_period,
    format_currency, success_response, error_response,
    _ACCURACY_NOTE,
)

TOOL_NAME = "zb_tax_liability"
TOOL_DESCRIPTION = (
    "Returns an estimated Tax Liability summary for Zoho Books. "
    "Use for 'What is our tax liability?', 'How much tax do we owe?'. "
    "OPERATIONAL ESTIMATE — derived from list API tax fields, not an official tax report. "
    "Do not use for tax filings. Verify with Zoho Books tax reports. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "period": {"type": "string",
                "description": "Period: this_month, last_month, this_quarter, this_year, last_year. Default: this_month."},
    "limit": {"type": "integer",
               "description": "Max records per source. Default: 200. Hard-capped at 500."},
}

_TAX_FIELDS = ["tax_amount", "total_tax_amount", "gst_amount"]
_DATE_FIELDS = ["date", "invoice_date", "expense_date", "created_time"]


def run(params: dict) -> dict:
    period = params.get("period", "this_month")
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    warnings = []
    inv_records = exp_records = []
    from_str = to_str = ""

    try:
        all_inv = extract_records(connector.list_invoices(limit=limit), ["invoices"])
        inv_records, no_d, from_str, to_str = filter_by_period(all_inv, _DATE_FIELDS, period)
        if no_d:
            warnings.append(f"{no_d} invoice(s) had no date — included without period filtering.")
    except Exception as e:
        warnings.append(f"Invoice fetch failed: {e}")

    try:
        all_exp = extract_records(connector.list_expenses(limit=limit), ["expenses"])
        exp_records, no_d, _, _ = filter_by_period(all_exp, _DATE_FIELDS, period)
        if no_d:
            warnings.append(f"{no_d} expense(s) had no date — included without period filtering.")
    except Exception as e:
        warnings.append(f"Expense fetch failed: {e}")

    tax_collected = sum(safe_amount(r, _TAX_FIELDS) for r in inv_records)
    input_tax = sum(safe_amount(r, _TAX_FIELDS) for r in exp_records)
    net_liability = tax_collected - input_tax

    by_tax_name: dict = {}
    for rec in inv_records:
        taxes = rec.get("taxes") or []
        for t in taxes:
            name = t.get("tax_name") or t.get("name") or "Unknown"
            amt = safe_amount(t, ["tax_amount", "amount"])
            if name not in by_tax_name:
                by_tax_name[name] = {"collected": 0.0, "input": 0.0}
            by_tax_name[name]["collected"] += amt
    for rec in exp_records:
        taxes = rec.get("taxes") or []
        for t in taxes:
            name = t.get("tax_name") or t.get("name") or "Unknown"
            amt = safe_amount(t, ["tax_amount", "amount"])
            if name not in by_tax_name:
                by_tax_name[name] = {"collected": 0.0, "input": 0.0}
            by_tax_name[name]["input"] += amt

    warnings.append("Tax values are from tax_amount fields in list-level API responses. These may be incomplete. Use Zoho Books Tax Summary report for accurate liability.")

    return success_response(
        report="Tax Liability (Estimate)",
        records_processed=len(inv_records) + len(exp_records),
        records_returned=len(by_tax_name) or 1,
        narrative_cue=(
            f"Estimated tax liability for {period}. "
            f"Tax collected: {format_currency(tax_collected, 'INR')}, "
            f"Input tax credit: {format_currency(input_tax, 'INR')}, "
            f"Net liability: {format_currency(net_liability, 'INR')}. "
            "State this is an estimate — not suitable for tax filings."
        ),
        period=period, date_range={"from": from_str, "to": to_str},
        tax_collected=tax_collected, tax_collected_formatted=format_currency(tax_collected, "INR"),
        input_tax_credit=input_tax, input_tax_formatted=format_currency(input_tax, "INR"),
        net_tax_liability=net_liability, net_tax_formatted=format_currency(net_liability, "INR"),
        by_tax_name=by_tax_name,
        report_basis="operational_estimate_from_tax_fields_in_invoices_and_expenses",
        accuracy_note=_ACCURACY_NOTE, warnings=warnings,
    )
