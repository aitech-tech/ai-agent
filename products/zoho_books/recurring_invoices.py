"""Recurring Invoices — summary of recurring invoice profiles."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount, safe_name,
    format_currency, totals_by_currency, currency_code,
    success_response, error_response,
)

TOOL_NAME = "zb_recurring_invoices"
TOOL_DESCRIPTION = (
    "Returns a pre-processed Recurring Invoices summary for Zoho Books. "
    "Use for 'Show recurring invoices', 'What is my recurring revenue?', 'Active subscriptions'. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "limit": {"type": "integer",
               "description": "Maximum records to fetch. Default: 100. Hard-capped at 200."},
}

_AMOUNT_FIELDS = ["amount", "total", "recurring_invoice_amount", "bcy_total"]
_NAME_FIELDS = ["recurrence_name", "customer_name", "contact_name", "name"]


def run(params: dict) -> dict:
    limit = cap_int(params.get("limit", 100), default=100, minimum=1, maximum=200)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))
    try:
        result = connector._get("recurringinvoices", {"per_page": limit})
    except Exception as e:
        return error_response("fetch_failed", str(e))

    records = extract_records(result, ["recurring_invoices", "recurringinvoices"])
    if not records:
        return success_response(
            report="Recurring Invoices", records_processed=0, records_returned=0,
            narrative_cue="No recurring invoices found.",
            active_count=0, inactive_count=0, total_count=0,
            next_scheduled=[], totals_by_currency={}, multi_currency=False,
        )

    active = [r for r in records if str(r.get("status", "")).lower() == "active"]
    inactive = [r for r in records if str(r.get("status", "")).lower() != "active"]

    by_currency = totals_by_currency(active if active else records, _AMOUNT_FIELDS)
    multi_currency = len(by_currency) > 1
    single_total = sum(v["amount"] for v in by_currency.values()) if not multi_currency else None
    single_code = next(iter(by_currency)) if by_currency else "INR"

    next_scheduled = []
    for rec in sorted(records, key=lambda r: r.get("next_invoice_date", "9999"))[:5]:
        amt = safe_amount(rec, _AMOUNT_FIELDS)
        next_scheduled.append({
            "name": safe_name(rec, _NAME_FIELDS),
            "next_invoice_date": rec.get("next_invoice_date"),
            "frequency": rec.get("recurrence_frequency") or rec.get("repeat_every"),
            "amount": amt,
            "amount_formatted": format_currency(amt, currency_code(rec)),
        })

    return success_response(
        report="Recurring Invoices", records_processed=len(records), records_returned=len(next_scheduled),
        narrative_cue=(
            f"{len(active)} active recurring invoices"
            + (f" with estimated recurring value {format_currency(single_total, single_code)}. " if not multi_currency else " across multiple currencies. ")
            + f"{len(inactive)} inactive/paused. List next scheduled and highlight recurring value."
        ),
        active_count=len(active), inactive_count=len(inactive), total_count=len(records),
        estimated_recurring_value=single_total, next_scheduled=next_scheduled,
        totals_by_currency=by_currency, multi_currency=multi_currency,
    )
