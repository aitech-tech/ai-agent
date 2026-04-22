"""Contact List — summarised count and sample of all contacts."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount, safe_name,
    success_response, error_response,
)

TOOL_NAME = "zb_contact_list"
TOOL_DESCRIPTION = (
    "Returns a summarised Contact List for Zoho Books. "
    "Use for 'How many customers do I have?', 'List my contacts', 'Show vendor count'. "
    "Returns counts by type, missing contact info, and a sample list. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "limit": {"type": "integer",
               "description": "Maximum contacts to fetch. Default: 200. Hard-capped at 500."},
}

_AMOUNT_FIELDS = ["outstanding_receivable_amount", "outstanding_payable_amount", "balance"]
_NAME_FIELDS = ["contact_name", "display_name", "company_name", "name"]


def run(params: dict) -> dict:
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))
    try:
        result = connector.list_contacts(limit=limit)
    except Exception as e:
        return error_response("fetch_failed", str(e))

    records = extract_records(result, ["contacts"])
    if not records:
        return success_response(
            report="Contact List", records_processed=0, records_returned=0,
            narrative_cue="No contacts found.",
            total_count=0, customer_count=0, vendor_count=0, other_count=0,
            missing_email_count=0, missing_phone_count=0, sample_contacts=[],
        )

    customer_count = vendor_count = other_count = 0
    missing_email = missing_phone = 0
    for rec in records:
        ctype = str(rec.get("contact_type", "")).lower()
        if ctype == "customer":
            customer_count += 1
        elif ctype == "vendor":
            vendor_count += 1
        else:
            other_count += 1
        if not str(rec.get("email") or rec.get("contact_email") or "").strip():
            missing_email += 1
        if not str(rec.get("phone") or rec.get("mobile") or "").strip():
            missing_phone += 1

    sample = [
        {
            "name": safe_name(rec, _NAME_FIELDS),
            "type": rec.get("contact_type", "unknown"),
            "email": rec.get("email") or rec.get("contact_email") or "",
            "currency_code": rec.get("currency_code", "INR"),
        }
        for rec in records[:10]
    ]

    return success_response(
        report="Contact List", records_processed=len(records), records_returned=len(sample),
        narrative_cue=(
            f"{len(records)} contacts: {customer_count} customers, {vendor_count} vendors, "
            f"{other_count} other. {missing_email} missing email, {missing_phone} missing phone."
        ),
        total_count=len(records), customer_count=customer_count,
        vendor_count=vendor_count, other_count=other_count,
        missing_email_count=missing_email, missing_phone_count=missing_phone,
        sample_contacts=sample,
    )
