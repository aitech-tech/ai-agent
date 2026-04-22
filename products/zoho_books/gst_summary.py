"""GST Summary — GST collected and paid estimates from invoices and expenses."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount, filter_by_period,
    totals_by_currency, format_currency, success_response, error_response,
    _ACCURACY_NOTE,
)

TOOL_NAME = "zb_gst_summary"
TOOL_DESCRIPTION = (
    "Returns an estimated GST Summary for Zoho Books. "
    "Use for 'Show GST summary', 'How much GST did we collect?', 'GST collected vs paid'. "
    "OPERATIONAL ESTIMATE — GST values derived from invoice and expense list data. "
    "Do not use for GST filings. Verify with Zoho Books GST reports. "
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

_GST_FIELDS = ["tax_amount", "gst_amount", "total_tax_amount"]
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

    gst_collected = sum(safe_amount(r, _GST_FIELDS) for r in inv_records)
    gst_paid = sum(safe_amount(r, _GST_FIELDS) for r in exp_records)
    net_gst = gst_collected - gst_paid

    inv_count_with_gst = sum(1 for r in inv_records if safe_amount(r, _GST_FIELDS) > 0)
    exp_count_with_gst = sum(1 for r in exp_records if safe_amount(r, _GST_FIELDS) > 0)

    warnings.append("GST values are summed from tax_amount fields in list API — may be incomplete or absent. Use Zoho Books GST reports for accurate figures.")

    return success_response(
        report="GST Summary (Estimate)",
        records_processed=len(inv_records) + len(exp_records),
        records_returned=1,
        narrative_cue=(
            f"GST estimate for {period}. "
            f"{inv_count_with_gst} of {len(inv_records)} invoices had tax fields; "
            f"{exp_count_with_gst} of {len(exp_records)} expenses had tax fields. "
            "State clearly this is an estimate and not suitable for GST filings."
        ),
        period=period, date_range={"from": from_str, "to": to_str},
        gst_collected=gst_collected, gst_collected_formatted=format_currency(gst_collected, "INR"),
        gst_paid=gst_paid, gst_paid_formatted=format_currency(gst_paid, "INR"),
        net_gst_liability=net_gst, net_gst_formatted=format_currency(net_gst, "INR"),
        invoice_count=len(inv_records), expense_count=len(exp_records),
        report_basis="operational_estimate_from_tax_fields_in_invoices_and_expenses",
        accuracy_note=_ACCURACY_NOTE, warnings=warnings,
    )
