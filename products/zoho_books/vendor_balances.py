"""Vendor Balances — outstanding payable amounts per vendor."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount, top_records,
    format_inr, totals_by_currency, success_response, error_response,
    _MULTI_CURRENCY_WARNING,
)

TOOL_NAME = "zb_vendor_balances"
TOOL_DESCRIPTION = (
    "Returns a pre-processed Vendor Balances summary for Zoho Books. "
    "Use for 'Which vendors do I owe money to?', 'Show vendor outstanding payables'. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "limit": {"type": "integer",
               "description": "Maximum records to process. Default: 200. Hard-capped at 500."},
}

_AMOUNT_FIELDS = ["outstanding_payable_amount", "outstanding_payable", "balance", "outstanding_amount"]
_NAME_FIELDS = ["contact_name", "vendor_name", "display_name", "company_name", "name"]


def run(params: dict) -> dict:
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))
    try:
        result = connector.list_contacts(contact_type="vendor", limit=limit)
    except Exception as e:
        return error_response("fetch_failed", str(e))

    records = extract_records(result, ["contacts"])
    if not records:
        return success_response(
            report="Vendor Balances", records_processed=0, records_returned=0,
            narrative_cue="No vendors found.",
            vendor_count=0, vendors_with_balance=0, zero_balance_count=0,
            total_outstanding=0.0, total_outstanding_formatted=format_inr(0),
            top_vendors=[], totals_by_currency={}, multi_currency=False, warnings=[],
        )

    by_currency = totals_by_currency(records, _AMOUNT_FIELDS)
    multi_currency = len(by_currency) > 1
    with_balance = sum(1 for r in records if safe_amount(r, _AMOUNT_FIELDS) > 0)
    zero_balance = len(records) - with_balance
    warnings = [_MULTI_CURRENCY_WARNING] if multi_currency else []
    single_total = sum(v["amount"] for v in by_currency.values()) if not multi_currency else None
    single_fmt = format_inr(single_total) if not multi_currency else None

    top_vendors = top_records(
        [r for r in records if safe_amount(r, _AMOUNT_FIELDS) > 0],
        _AMOUNT_FIELDS, _NAME_FIELDS, n=10, extra_fields=["email"],
    )
    return success_response(
        report="Vendor Balances", records_processed=len(records), records_returned=len(top_vendors),
        narrative_cue=(
            f"{len(records)} vendors. {with_balance} have outstanding payables"
            + (f" totalling {single_fmt}. " if not multi_currency else " across multiple currencies. ")
            + f"{zero_balance} have zero balance. List top vendors by outstanding payable."
        ),
        vendor_count=len(records), vendors_with_balance=with_balance, zero_balance_count=zero_balance,
        total_outstanding=single_total, total_outstanding_formatted=single_fmt,
        top_vendors=top_vendors, totals_by_currency=by_currency,
        multi_currency=multi_currency, warnings=warnings,
    )
