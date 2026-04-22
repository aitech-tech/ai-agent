"""Cash Flow — operational estimate from customer and vendor payments."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, filter_by_period,
    totals_by_currency, format_currency, success_response, error_response,
    _MULTI_CURRENCY_WARNING, _ACCURACY_NOTE,
)

TOOL_NAME = "zb_cash_flow"
TOOL_DESCRIPTION = (
    "Returns an estimated Cash Flow summary for Zoho Books. "
    "Use for 'Show cash flow', 'How much cash came in vs went out?'. "
    "OPERATIONAL ESTIMATE ONLY — not a statutory cash flow statement. Verify before filings. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "period": {"type": "string",
                "description": "Time period: this_month, last_month, this_quarter, this_year, last_year. Default: this_month."},
    "limit": {"type": "integer",
               "description": "Max records per source. Default: 200. Hard-capped at 500."},
}

_PMT_FIELDS = ["amount", "payment_amount", "total"]
_DATE_FIELDS = ["date", "payment_date", "created_time"]


def run(params: dict) -> dict:
    period = params.get("period", "this_month")
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    warnings = []
    inflow_records = outflow_records = []
    from_str = to_str = ""

    try:
        cp = extract_records(connector.list_customer_payments(limit=limit), ["customer_payments"])
        inflow_records, no_d, from_str, to_str = filter_by_period(cp, _DATE_FIELDS, period)
        if no_d:
            warnings.append(f"{no_d} customer payment(s) had no date and were included without period filtering.")
    except Exception as e:
        warnings.append(f"Inflows fetch failed: {e}")

    try:
        vp = extract_records(connector._get("vendorpayments", {"per_page": limit}), ["vendor_payments", "vendorpayments"])
        outflow_records, no_d, from_str, to_str = filter_by_period(vp, _DATE_FIELDS, period)
        if no_d:
            warnings.append(f"{no_d} vendor payment(s) had no date and were included without period filtering.")
    except Exception as e:
        warnings.append(f"Outflows fetch failed: {e}")

    inflows_by_currency = totals_by_currency(inflow_records, _PMT_FIELDS)
    outflows_by_currency = totals_by_currency(outflow_records, _PMT_FIELDS)

    all_codes = set(inflows_by_currency) | set(outflows_by_currency)
    multi_currency = len(all_codes) > 1
    if multi_currency:
        warnings.append(_MULTI_CURRENCY_WARNING)

    net_by_currency = {}
    for code in all_codes:
        inflow = inflows_by_currency.get(code, {}).get("amount", 0.0)
        outflow = outflows_by_currency.get(code, {}).get("amount", 0.0)
        net = inflow - outflow
        net_by_currency[code] = {
            "inflow": inflow, "inflow_formatted": format_currency(inflow, code),
            "outflow": outflow, "outflow_formatted": format_currency(outflow, code),
            "net": net, "net_formatted": format_currency(net, code),
        }

    return success_response(
        report="Cash Flow (Estimate)",
        records_processed=len(inflow_records) + len(outflow_records),
        records_returned=len(net_by_currency),
        narrative_cue=(
            f"Cash flow estimate for {period}: {len(inflow_records)} inflows, {len(outflow_records)} outflows. "
            + ("Narrate each currency separately. " if multi_currency else "")
            + "State this is an operational estimate — not a statutory cash flow statement."
        ),
        period=period, date_range={"from": from_str, "to": to_str},
        inflows_by_currency=inflows_by_currency, outflows_by_currency=outflows_by_currency,
        net_by_currency=net_by_currency, multi_currency=multi_currency,
        report_basis="operational_estimate_from_customer_and_vendor_payments",
        accuracy_note=_ACCURACY_NOTE, warnings=warnings,
    )
