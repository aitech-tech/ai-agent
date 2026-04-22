"""Vendor Payments — payments made to vendors for a period."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, group_amounts, filter_by_period,
    format_currency, totals_by_currency, success_response, error_response,
    _MULTI_CURRENCY_WARNING,
)

TOOL_NAME = "zb_vendor_payments"
TOOL_DESCRIPTION = (
    "Returns a pre-processed Vendor Payments summary for Zoho Books. "
    "Use for 'How much did I pay vendors this month?', 'Show vendor payment breakdown'. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "period": {"type": "string",
                "description": "Time period: this_month, last_month, this_quarter, this_year, last_year. Default: this_month."},
    "limit": {"type": "integer",
               "description": "Maximum records to process. Default: 200. Hard-capped at 500."},
}

_AMOUNT_FIELDS = ["amount", "payment_amount", "total"]
_DATE_FIELDS = ["date", "payment_date", "created_time"]
_NAME_FIELDS = ["vendor_name", "contact_name", "name"]
_MODE_FIELDS = ["payment_mode", "mode", "payment_type"]


def run(params: dict) -> dict:
    period = params.get("period", "this_month")
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))
    try:
        result = connector._get("vendorpayments", {"per_page": limit})
    except Exception as e:
        return error_response("fetch_failed", str(e))

    all_records = extract_records(result, ["vendor_payments", "vendorpayments"])
    filtered, no_date_count, from_str, to_str = filter_by_period(all_records, _DATE_FIELDS, period)
    warnings = []
    if no_date_count:
        warnings.append(f"{no_date_count} payment(s) had no date and were included without period filtering.")

    if not filtered:
        return success_response(
            report="Vendor Payments", records_processed=0, records_returned=0,
            narrative_cue=f"No vendor payments found for period '{period}'.",
            period=period, date_range={"from": from_str, "to": to_str},
            payment_count=0, by_mode=[], top_vendors=[],
            totals_by_currency={}, multi_currency=False, warnings=warnings,
        )

    by_currency = totals_by_currency(filtered, _AMOUNT_FIELDS)
    multi_currency = len(by_currency) > 1
    if multi_currency:
        warnings.append(_MULTI_CURRENCY_WARNING)
    single_total = sum(v["amount"] for v in by_currency.values()) if not multi_currency else None
    single_code = next(iter(by_currency)) if by_currency else "INR"

    by_mode = group_amounts(filtered, _MODE_FIELDS, _AMOUNT_FIELDS, limit=10)
    top_vendors = group_amounts(filtered, _NAME_FIELDS, _AMOUNT_FIELDS, limit=10)

    return success_response(
        report="Vendor Payments", records_processed=len(filtered), records_returned=len(top_vendors),
        narrative_cue=(
            f"{len(filtered)} vendor payments for {period}"
            + (f" totalling {format_currency(single_total, single_code)}. " if not multi_currency else " across multiple currencies. ")
            + "Summarise by vendor and payment mode."
        ),
        period=period, date_range={"from": from_str, "to": to_str},
        payment_count=len(filtered), total_paid=single_total,
        by_mode=by_mode, top_vendors=top_vendors,
        totals_by_currency=by_currency, multi_currency=multi_currency, warnings=warnings,
    )
