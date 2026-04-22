"""
Overdue Invoices — summary of all overdue invoices with aging stats.
"""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, top_records, group_amounts,
    safe_amount, days_past_due, format_inr, success_response, error_response,
)

TOOL_NAME = "zb_overdue_invoices"

TOOL_DESCRIPTION = (
    "Returns a pre-processed Overdue Invoices summary for Zoho Books. "
    "Use for questions like 'What invoices are overdue?', 'Show late invoices', "
    "'Which customers owe the most overdue amounts?' "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)

TOOL_PARAMS = {
    "limit": {
        "type": "integer",
        "description": "Maximum records to process locally. Default: 100. Hard-capped at 500.",
    }
}

_AMOUNT_FIELDS = ["balance", "total", "amount", "bcy_total", "total_amount"]
_NAME_FIELDS = ["customer_name", "contact_name", "name", "company_name"]


def run(params: dict) -> dict:
    limit = cap_int(params.get("limit", 100), default=100, minimum=1, maximum=500)

    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    try:
        result = connector.list_invoices(status="overdue", limit=limit)
    except Exception as e:
        return error_response("fetch_failed", str(e))

    records = extract_records(result, ["invoices"])
    records_processed = len(records)

    if not records:
        return success_response(
            report="Overdue Invoices",
            records_processed=0,
            records_returned=0,
            narrative_cue="No overdue invoices found.",
            total_overdue_amount=0.0,
            total_overdue_formatted=format_inr(0),
            invoice_count=0,
            average_days_overdue=None,
            oldest_overdue_days=None,
            oldest_overdue_invoice=None,
            top_overdue_invoices=[],
            by_customer=[],
        )

    total_overdue = 0.0
    days_list = []
    oldest_days = 0
    oldest_invoice = None

    for rec in records:
        amt = safe_amount(rec, _AMOUNT_FIELDS)
        total_overdue += amt
        dpd = days_past_due(rec.get("due_date"))
        if dpd is not None:
            days_list.append(dpd)
            if dpd > oldest_days:
                oldest_days = dpd
                oldest_invoice = {
                    "name": _safe_name(rec),
                    "invoice_number": rec.get("invoice_number"),
                    "due_date": rec.get("due_date"),
                    "days_overdue": dpd,
                    "amount": amt,
                    "amount_formatted": format_inr(amt),
                }

    avg_days = round(sum(days_list) / len(days_list), 1) if days_list else None

    top_invs = top_records(
        records, _AMOUNT_FIELDS, _NAME_FIELDS, n=10,
        extra_fields=["invoice_number", "due_date", "status"],
    )
    by_customer = group_amounts(records, _NAME_FIELDS, _AMOUNT_FIELDS, limit=10)

    return success_response(
        report="Overdue Invoices",
        records_processed=records_processed,
        records_returned=len(top_invs),
        narrative_cue=(
            f"{records_processed} overdue invoices totalling {format_inr(total_overdue)}. "
            f"Average {avg_days} days overdue. "
            "List top customers by overdue amount and flag the oldest invoice."
        ),
        total_overdue_amount=total_overdue,
        total_overdue_formatted=format_inr(total_overdue),
        invoice_count=records_processed,
        average_days_overdue=avg_days,
        oldest_overdue_days=oldest_days if days_list else None,
        oldest_overdue_invoice=oldest_invoice,
        top_overdue_invoices=top_invs,
        by_customer=by_customer,
    )


def _safe_name(rec: dict) -> str:
    for field in ("customer_name", "contact_name", "name", "company_name"):
        val = rec.get(field)
        if val and str(val).strip():
            return str(val).strip()
    return "Unknown"
