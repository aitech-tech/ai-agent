"""Overdue Bills — summary of all overdue bills with aging stats."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount, safe_name,
    top_records, group_amounts, days_past_due, format_currency, currency_code,
    totals_by_currency, success_response, error_response, _MULTI_CURRENCY_WARNING,
)

TOOL_NAME = "zb_overdue_bills"
TOOL_DESCRIPTION = (
    "Returns a pre-processed Overdue Bills summary for Zoho Books. "
    "Use for 'What bills are overdue?', 'Show late vendor payments'. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "limit": {"type": "integer",
               "description": "Maximum records to process. Default: 100. Hard-capped at 500."},
}

_AMOUNT_FIELDS = ["balance", "total", "amount", "bcy_total", "total_amount"]
_NAME_FIELDS = ["vendor_name", "contact_name", "name", "company_name"]


def run(params: dict) -> dict:
    limit = cap_int(params.get("limit", 100), default=100, minimum=1, maximum=500)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))
    try:
        result = connector._get("bills", {"status": "overdue", "per_page": limit})
    except Exception as e:
        return error_response("fetch_failed", str(e))

    all_bills = extract_records(result, ["bills"])
    records = [r for r in all_bills
               if str(r.get("status", "")).lower() in ("overdue", "open", "unpaid", "")]

    if not records:
        return success_response(
            report="Overdue Bills", records_processed=0, records_returned=0,
            narrative_cue="No overdue bills found.",
            bill_count=0, average_days_overdue=None, oldest_overdue_days=None,
            oldest_overdue_bill=None, top_overdue_bills=[], by_vendor=[],
            totals_by_currency={}, multi_currency=False, warnings=[],
        )

    by_currency = totals_by_currency(records, _AMOUNT_FIELDS)
    multi_currency = len(by_currency) > 1
    warnings = [_MULTI_CURRENCY_WARNING] if multi_currency else []
    single_total = sum(v["amount"] for v in by_currency.values()) if not multi_currency else None
    single_code = next(iter(by_currency)) if by_currency else "INR"

    days_list, oldest_days, oldest_bill = [], 0, None
    for rec in records:
        dpd = days_past_due(rec.get("due_date"))
        if dpd is not None:
            days_list.append(dpd)
            if dpd > oldest_days:
                oldest_days = dpd
                amt = safe_amount(rec, _AMOUNT_FIELDS)
                oldest_bill = {
                    "name": safe_name(rec, _NAME_FIELDS),
                    "bill_number": rec.get("bill_number"),
                    "due_date": rec.get("due_date"),
                    "days_overdue": dpd,
                    "amount": amt,
                    "amount_formatted": format_currency(amt, currency_code(rec)),
                }

    avg_days = round(sum(days_list) / len(days_list), 1) if days_list else None
    top_bills = top_records(records, _AMOUNT_FIELDS, _NAME_FIELDS, n=10,
                             extra_fields=["bill_number", "due_date"])
    by_vendor = group_amounts(records, _NAME_FIELDS, _AMOUNT_FIELDS, limit=10)

    return success_response(
        report="Overdue Bills", records_processed=len(records), records_returned=len(top_bills),
        narrative_cue=(
            f"{len(records)} overdue bills"
            + (f" totalling {format_currency(single_total, single_code)}. " if not multi_currency else " across multiple currencies. ")
            + f"Average {avg_days} days overdue. List top vendors and flag oldest bill."
        ),
        bill_count=len(records), total_overdue=single_total,
        average_days_overdue=avg_days, oldest_overdue_days=oldest_days if days_list else None,
        oldest_overdue_bill=oldest_bill, top_overdue_bills=top_bills, by_vendor=by_vendor,
        totals_by_currency=by_currency, multi_currency=multi_currency, warnings=warnings,
    )
