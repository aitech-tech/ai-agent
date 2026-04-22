"""Outstanding Invoices — all open (unpaid/sent) invoices."""
import datetime
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount, safe_name,
    top_records, group_amounts, format_currency, totals_by_currency,
    currency_code, first_record_by_date, success_response, error_response,
    _MULTI_CURRENCY_WARNING,
)

TOOL_NAME = "zb_outstanding_invoices"
TOOL_DESCRIPTION = (
    "Returns a pre-processed Outstanding Invoices summary for Zoho Books. "
    "Use for 'What invoices are still open?', 'Show unpaid invoices by customer'. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "limit": {"type": "integer",
               "description": "Maximum records to process. Default: 200. Hard-capped at 500."},
}

_AMOUNT_FIELDS = ["balance", "total", "amount", "bcy_total", "total_amount"]
_NAME_FIELDS = ["customer_name", "contact_name", "name", "company_name"]


def run(params: dict) -> dict:
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    as_of = datetime.date.today().isoformat()
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    seen: set = set()
    records: list = []
    fetch_errors: list = []
    for status in ("unpaid", "sent"):
        try:
            batch = extract_records(connector.list_invoices(status=status, limit=limit), ["invoices"])
            for rec in batch:
                iid = rec.get("invoice_id") or rec.get("id")
                if iid and iid in seen:
                    continue
                if iid:
                    seen.add(iid)
                records.append(rec)
        except Exception as e:
            fetch_errors.append(str(e))

    if len(fetch_errors) == 2:
        return error_response("fetch_failed", "; ".join(fetch_errors))

    if not records:
        return success_response(
            report="Outstanding Invoices", records_processed=0, records_returned=0,
            narrative_cue="No outstanding invoices found.",
            as_of_date=as_of, invoice_count=0, oldest_invoice=None,
            top_customers=[], totals_by_currency={}, multi_currency=False, warnings=[],
        )

    by_currency = totals_by_currency(records, _AMOUNT_FIELDS)
    multi_currency = len(by_currency) > 1
    warnings = [_MULTI_CURRENCY_WARNING] if multi_currency else []

    oldest = first_record_by_date(records, "date")
    oldest_info = None
    if oldest:
        amt = safe_amount(oldest, _AMOUNT_FIELDS)
        oldest_info = {
            "name": safe_name(oldest, _NAME_FIELDS),
            "invoice_number": oldest.get("invoice_number"),
            "date": oldest.get("date"),
            "due_date": oldest.get("due_date"),
            "amount": amt,
            "amount_formatted": format_currency(amt, currency_code(oldest)),
        }

    top_customers = group_amounts(records, _NAME_FIELDS, _AMOUNT_FIELDS, limit=10)

    single_total = sum(v["amount"] for v in by_currency.values()) if not multi_currency else None
    single_code = next(iter(by_currency)) if by_currency else "INR"

    return success_response(
        report="Outstanding Invoices", records_processed=len(records),
        records_returned=len(top_customers),
        narrative_cue=(
            f"{len(records)} outstanding invoices as of {as_of}"
            + (f" totalling {format_currency(single_total, single_code)}. " if not multi_currency else " across multiple currencies. ")
            + "List top customers by outstanding amount."
        ),
        as_of_date=as_of, invoice_count=len(records),
        total_outstanding=single_total,
        oldest_invoice=oldest_info, top_customers=top_customers,
        totals_by_currency=by_currency, multi_currency=multi_currency, warnings=warnings,
    )
