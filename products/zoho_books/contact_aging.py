"""Contact Aging — bucket contacts by outstanding balance size."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount, top_records,
    format_inr, totals_by_currency, success_response, error_response,
    _MULTI_CURRENCY_WARNING,
)

TOOL_NAME = "zb_contact_aging"
TOOL_DESCRIPTION = (
    "Returns a Contact Aging summary for Zoho Books — contacts bucketed by outstanding balance. "
    "Use for 'Bucket my customers by balance size', 'Which contacts owe the most?'. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "contact_type": {"type": "string",
                      "description": "Filter: 'customer', 'vendor', or omit for all."},
    "limit": {"type": "integer",
               "description": "Maximum records to process. Default: 200. Hard-capped at 500."},
}

_AMOUNT_FIELDS = ["outstanding_receivable_amount", "outstanding_payable_amount",
                   "balance", "outstanding_amount"]
_NAME_FIELDS = ["contact_name", "display_name", "company_name", "name"]


def run(params: dict) -> dict:
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    contact_type = params.get("contact_type") or None
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))
    try:
        result = connector.list_contacts(contact_type=contact_type, limit=limit)
    except Exception as e:
        return error_response("fetch_failed", str(e))

    records = extract_records(result, ["contacts"])
    if not records:
        return success_response(
            report="Contact Aging", records_processed=0, records_returned=0,
            narrative_cue="No contacts found.",
            contact_count=0, buckets={}, top_contacts=[],
            totals_by_currency={}, multi_currency=False, warnings=[],
        )

    buckets = {"zero": 0, "1_to_10k": 0, "10k_to_1lakh": 0, "1lakh_plus": 0}
    for rec in records:
        amt = safe_amount(rec, _AMOUNT_FIELDS)
        if amt <= 0:
            buckets["zero"] += 1
        elif amt <= 10000:
            buckets["1_to_10k"] += 1
        elif amt <= 100000:
            buckets["10k_to_1lakh"] += 1
        else:
            buckets["1lakh_plus"] += 1

    by_currency = totals_by_currency(records, _AMOUNT_FIELDS)
    multi_currency = len(by_currency) > 1
    warnings = [_MULTI_CURRENCY_WARNING] if multi_currency else []

    top_contacts = top_records(
        [r for r in records if safe_amount(r, _AMOUNT_FIELDS) > 0],
        _AMOUNT_FIELDS, _NAME_FIELDS, n=10, extra_fields=["contact_type", "email"],
    )

    return success_response(
        report="Contact Aging", records_processed=len(records), records_returned=len(top_contacts),
        narrative_cue=(
            f"{len(records)} contacts. Zero balance: {buckets['zero']}, "
            f"Up to ₹10k: {buckets['1_to_10k']}, ₹10k–₹1L: {buckets['10k_to_1lakh']}, "
            f"₹1L+: {buckets['1lakh_plus']}. List top contacts by balance."
        ),
        contact_count=len(records), buckets=buckets, top_contacts=top_contacts,
        totals_by_currency=by_currency, multi_currency=multi_currency, warnings=warnings,
    )
