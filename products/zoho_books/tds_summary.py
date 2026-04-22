"""TDS Summary — TDS deducted estimate from invoices and vendor payments."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount, filter_by_period,
    format_currency, success_response, error_response,
    _ACCURACY_NOTE,
)

TOOL_NAME = "zb_tds_summary"
TOOL_DESCRIPTION = (
    "Returns an estimated TDS (Tax Deducted at Source) summary for Zoho Books. "
    "Use for 'Show TDS summary', 'How much TDS was deducted?', 'TDS payable'. "
    "OPERATIONAL ESTIMATE — TDS values from list API fields. Not for tax filings. "
    "Verify with Zoho Books TDS reports. "
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

_TDS_FIELDS = ["tds_amount", "tds_tax_amount", "withholding_tax_amount"]
_DATE_FIELDS = ["date", "invoice_date", "payment_date", "created_time"]


def run(params: dict) -> dict:
    period = params.get("period", "this_month")
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    warnings = []
    inv_records = vp_records = []
    from_str = to_str = ""

    try:
        all_inv = extract_records(connector.list_invoices(limit=limit), ["invoices"])
        inv_records, no_d, from_str, to_str = filter_by_period(all_inv, _DATE_FIELDS, period)
        if no_d:
            warnings.append(f"{no_d} invoice(s) had no date — included without period filtering.")
    except Exception as e:
        warnings.append(f"Invoice fetch failed: {e}")

    try:
        raw = connector._get("vendorpayments", {"per_page": limit})
        all_vp = extract_records(raw, ["vendor_payments", "vendorpayments"])
        vp_records, no_d, _, _ = filter_by_period(all_vp, _DATE_FIELDS, period)
        if no_d:
            warnings.append(f"{no_d} vendor payment(s) had no date — included without period filtering.")
    except Exception as e:
        warnings.append(f"Vendor payment fetch failed: {e}")

    tds_on_sales = sum(safe_amount(r, _TDS_FIELDS) for r in inv_records)
    tds_on_purchases = sum(safe_amount(r, _TDS_FIELDS) for r in vp_records)

    inv_with_tds = sum(1 for r in inv_records if safe_amount(r, _TDS_FIELDS) > 0)
    vp_with_tds = sum(1 for r in vp_records if safe_amount(r, _TDS_FIELDS) > 0)

    warnings.append(
        "TDS fields (tds_amount, withholding_tax_amount) may not be present in list API responses. "
        "Use Zoho Books TDS reports for authoritative figures."
    )

    return success_response(
        report="TDS Summary (Estimate)",
        records_processed=len(inv_records) + len(vp_records),
        records_returned=1,
        narrative_cue=(
            f"TDS estimate for {period}. "
            f"TDS on sales invoices: {format_currency(tds_on_sales, 'INR')} ({inv_with_tds} of {len(inv_records)} invoices had TDS). "
            f"TDS on vendor payments: {format_currency(tds_on_purchases, 'INR')} ({vp_with_tds} of {len(vp_records)} payments had TDS). "
            "State this is an estimate — not suitable for TDS filings."
        ),
        period=period, date_range={"from": from_str, "to": to_str},
        tds_on_sales=tds_on_sales, tds_on_sales_formatted=format_currency(tds_on_sales, "INR"),
        tds_on_purchases=tds_on_purchases, tds_on_purchases_formatted=format_currency(tds_on_purchases, "INR"),
        invoices_with_tds=inv_with_tds, invoice_total=len(inv_records),
        vendor_payments_with_tds=vp_with_tds, vendor_payment_total=len(vp_records),
        report_basis="operational_estimate_from_tds_fields_in_invoices_and_vendor_payments",
        accuracy_note=_ACCURACY_NOTE, warnings=warnings,
    )
