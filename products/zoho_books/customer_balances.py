"""
Customer Balances — outstanding receivable amounts per customer.
"""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount, safe_name,
    top_records, format_inr, success_response, error_response,
)

TOOL_NAME = "zb_customer_balances"

TOOL_DESCRIPTION = (
    "Returns a pre-processed Customer Balances summary for Zoho Books. "
    "Use for questions like 'Which customers owe me money?', "
    "'Show customer outstanding balances', 'Who are my biggest debtors?' "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)

TOOL_PARAMS = {
    "limit": {
        "type": "integer",
        "description": "Maximum records to process locally. Default: 200. Hard-capped at 500.",
    }
}

_AMOUNT_FIELDS = [
    "outstanding_receivable_amount", "outstanding_receivable",
    "balance", "outstanding_amount",
]
_NAME_FIELDS = ["contact_name", "customer_name", "display_name", "company_name", "name"]


def run(params: dict) -> dict:
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)

    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    try:
        result = connector.list_contacts(contact_type="customer", limit=limit)
    except Exception as e:
        return error_response("fetch_failed", str(e))

    records = extract_records(result, ["contacts"])
    records_processed = len(records)

    if not records:
        return success_response(
            report="Customer Balances",
            records_processed=0,
            records_returned=0,
            narrative_cue="No customers found.",
            customer_count=0,
            customers_with_balance=0,
            zero_balance_count=0,
            total_outstanding=0.0,
            total_outstanding_formatted=format_inr(0),
            top_customers=[],
            missing_email_count=0,
        )

    total_outstanding = 0.0
    with_balance = 0
    zero_balance = 0
    missing_email = 0

    for rec in records:
        amt = safe_amount(rec, _AMOUNT_FIELDS)
        total_outstanding += amt
        if amt > 0:
            with_balance += 1
        else:
            zero_balance += 1
        email = rec.get("email") or rec.get("contact_email") or ""
        if not str(email).strip():
            missing_email += 1

    top_custs = top_records(
        [r for r in records if safe_amount(r, _AMOUNT_FIELDS) > 0],
        _AMOUNT_FIELDS,
        _NAME_FIELDS,
        n=10,
        extra_fields=["email", "contact_type"],
    )

    return success_response(
        report="Customer Balances",
        records_processed=records_processed,
        records_returned=len(top_custs),
        narrative_cue=(
            f"{records_processed} customers. "
            f"{with_balance} have outstanding balances totalling {format_inr(total_outstanding)}. "
            f"{zero_balance} have zero balance. "
            "List top customers by outstanding amount."
        ),
        customer_count=records_processed,
        customers_with_balance=with_balance,
        zero_balance_count=zero_balance,
        total_outstanding=total_outstanding,
        total_outstanding_formatted=format_inr(total_outstanding),
        top_customers=top_custs,
        missing_email_count=missing_email,
    )
