"""Outstanding Bills — all open/unpaid bills with vendor breakdown."""
import datetime
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount, safe_name,
    group_amounts, format_currency, totals_by_currency, currency_code,
    first_record_by_date, success_response, error_response, _MULTI_CURRENCY_WARNING,
)

TOOL_NAME = "zb_outstanding_bills"
TOOL_DESCRIPTION = (
    "Returns a pre-processed Outstanding Bills summary for Zoho Books. "
    "Use for 'What bills are outstanding?', 'Show unpaid vendor bills'. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "limit": {"type": "integer",
               "description": "Maximum records to process. Default: 200. Hard-capped at 500."},
}

_AMOUNT_FIELDS = ["balance", "total", "amount", "bcy_total", "total_amount"]
_NAME_FIELDS = ["vendor_name", "contact_name", "name", "company_name"]


def run(params: dict) -> dict:
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    as_of = datetime.date.today().isoformat()
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))
    try:
        result = connector._get("bills", {"per_page": limit})
    except Exception as e:
        return error_response("fetch_failed", str(e))

    all_bills = extract_records(result, ["bills"])
    records = [r for r in all_bills
               if str(r.get("status", "")).lower() not in ("paid", "void", "draft")]

    if not records:
        return success_response(
            report="Outstanding Bills", records_processed=0, records_returned=0,
            narrative_cue="No outstanding bills found.",
            as_of_date=as_of, bill_count=0, oldest_bill=None, by_vendor=[],
            totals_by_currency={}, multi_currency=False, warnings=[],
        )

    by_currency = totals_by_currency(records, _AMOUNT_FIELDS)
    multi_currency = len(by_currency) > 1
    warnings = [_MULTI_CURRENCY_WARNING] if multi_currency else []
    single_total = sum(v["amount"] for v in by_currency.values()) if not multi_currency else None
    single_code = next(iter(by_currency)) if by_currency else "INR"

    oldest = first_record_by_date(records, "date")
    oldest_info = None
    if oldest:
        amt = safe_amount(oldest, _AMOUNT_FIELDS)
        oldest_info = {
            "name": safe_name(oldest, _NAME_FIELDS),
            "bill_number": oldest.get("bill_number"),
            "date": oldest.get("date"),
            "due_date": oldest.get("due_date"),
            "amount": amt,
            "amount_formatted": format_currency(amt, currency_code(oldest)),
        }

    by_vendor = group_amounts(records, _NAME_FIELDS, _AMOUNT_FIELDS, limit=10)

    return success_response(
        report="Outstanding Bills", records_processed=len(records), records_returned=len(by_vendor),
        narrative_cue=(
            f"{len(records)} outstanding bills as of {as_of}"
            + (f" totalling {format_currency(single_total, single_code)}. " if not multi_currency else " across multiple currencies. ")
            + "List top vendors by outstanding bill amount."
        ),
        as_of_date=as_of, bill_count=len(records), total_outstanding=single_total,
        oldest_bill=oldest_info, by_vendor=by_vendor,
        totals_by_currency=by_currency, multi_currency=multi_currency, warnings=warnings,
    )
