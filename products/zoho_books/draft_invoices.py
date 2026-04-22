"""Draft Invoices — count and value of invoices not yet sent."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount, safe_name,
    top_records, format_currency, totals_by_currency, currency_code,
    first_record_by_date, success_response, error_response,
)

TOOL_NAME = "zb_draft_invoices"
TOOL_DESCRIPTION = (
    "Returns a pre-processed Draft Invoices summary for Zoho Books. "
    "Use for 'How many draft invoices do I have?', 'Show invoices not yet sent'. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "limit": {"type": "integer",
               "description": "Maximum records to process. Default: 200. Hard-capped at 500."},
}

_AMOUNT_FIELDS = ["total", "balance", "amount", "bcy_total", "total_amount"]
_NAME_FIELDS = ["customer_name", "contact_name", "name", "company_name"]


def run(params: dict) -> dict:
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))
    try:
        result = connector.list_invoices(status="draft", limit=limit)
    except Exception as e:
        return error_response("fetch_failed", str(e))

    records = extract_records(result, ["invoices"])
    if not records:
        return success_response(
            report="Draft Invoices", records_processed=0, records_returned=0,
            narrative_cue="No draft invoices found.",
            draft_count=0, oldest_draft=None, top_drafts=[],
            totals_by_currency={}, multi_currency=False,
        )

    by_currency = totals_by_currency(records, _AMOUNT_FIELDS)
    multi_currency = len(by_currency) > 1
    single_total = sum(v["amount"] for v in by_currency.values()) if not multi_currency else None
    single_code = next(iter(by_currency)) if by_currency else "INR"

    oldest = first_record_by_date(records, "date")
    oldest_info = None
    if oldest:
        amt = safe_amount(oldest, _AMOUNT_FIELDS)
        oldest_info = {
            "name": safe_name(oldest, _NAME_FIELDS),
            "invoice_number": oldest.get("invoice_number"),
            "date": oldest.get("date"),
            "amount": amt,
            "amount_formatted": format_currency(amt, currency_code(oldest)),
        }

    top_drafts = top_records(records, _AMOUNT_FIELDS, _NAME_FIELDS, n=10,
                              extra_fields=["invoice_number", "date"])

    return success_response(
        report="Draft Invoices", records_processed=len(records), records_returned=len(top_drafts),
        narrative_cue=(
            f"{len(records)} draft invoices"
            + (f" totalling {format_currency(single_total, single_code)}. " if not multi_currency else " across multiple currencies. ")
            + "List top drafts and mention oldest draft."
        ),
        draft_count=len(records),
        total_value=single_total,
        oldest_draft=oldest_info, top_drafts=top_drafts,
        totals_by_currency=by_currency, multi_currency=multi_currency,
    )
