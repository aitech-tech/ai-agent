"""Bills by Vendor — bills grouped and totalled per vendor."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, group_amounts, filter_by_period,
    format_currency, totals_by_currency, success_response, error_response,
    _MULTI_CURRENCY_WARNING,
)

TOOL_NAME = "zb_bills_by_vendor"
TOOL_DESCRIPTION = (
    "Returns a pre-processed Bills by Vendor summary for Zoho Books. "
    "Use for 'Which vendors billed me the most?', 'Show spend by vendor from bills'. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "period": {"type": "string",
                "description": "Time period: this_month, last_month, this_quarter, this_year, last_year. Default: this_month."},
    "limit": {"type": "integer",
               "description": "Maximum bills to process. Default: 200. Hard-capped at 500."},
}

_AMOUNT_FIELDS = ["total", "balance", "amount", "bcy_total", "total_amount"]
_NAME_FIELDS = ["vendor_name", "contact_name", "name", "company_name"]
_DATE_FIELDS = ["date", "bill_date", "created_time"]


def run(params: dict) -> dict:
    period = params.get("period", "this_month")
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))
    try:
        result = connector._get("bills", {"per_page": limit})
    except Exception as e:
        return error_response("fetch_failed", str(e))

    all_bills = extract_records(result, ["bills"])
    filtered, no_date_count, from_str, to_str = filter_by_period(all_bills, _DATE_FIELDS, period)
    warnings = []
    if no_date_count:
        warnings.append(f"{no_date_count} bill(s) had no date and were included without period filtering.")

    if not filtered:
        return success_response(
            report="Bills by Vendor", records_processed=0, records_returned=0,
            narrative_cue=f"No bills found for period '{period}'.",
            period=period, date_range={"from": from_str, "to": to_str},
            vendor_count=0, top_vendors=[], totals_by_currency={},
            multi_currency=False, warnings=warnings,
        )

    by_currency = totals_by_currency(filtered, _AMOUNT_FIELDS)
    multi_currency = len(by_currency) > 1
    if multi_currency:
        warnings.append(_MULTI_CURRENCY_WARNING)
    single_total = sum(v["amount"] for v in by_currency.values()) if not multi_currency else None
    single_code = next(iter(by_currency)) if by_currency else "INR"

    top_vendors = group_amounts(filtered, _NAME_FIELDS, _AMOUNT_FIELDS, limit=10)

    return success_response(
        report="Bills by Vendor", records_processed=len(filtered), records_returned=len(top_vendors),
        narrative_cue=(
            f"{len(filtered)} bills for {period}"
            + (f" totalling {format_currency(single_total, single_code)}. " if not multi_currency else " across multiple currencies. ")
            + f"From {len(top_vendors)} vendors. List top vendors by billed amount."
        ),
        period=period, date_range={"from": from_str, "to": to_str},
        bill_count=len(filtered), total_billed=single_total, vendor_count=len(top_vendors),
        top_vendors=top_vendors, totals_by_currency=by_currency,
        multi_currency=multi_currency, warnings=warnings,
    )
