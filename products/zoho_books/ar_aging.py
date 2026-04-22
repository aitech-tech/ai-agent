"""
AR Aging Summary — receivables aging by due-date bucket.
"""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, bucket_by_due_date,
    top_records, pct, format_inr, success_response, error_response,
)

TOOL_NAME = "zb_ar_aging"

TOOL_DESCRIPTION = (
    "Returns a pre-processed AR Aging Summary for Zoho Books. "
    "Use for questions like 'How are my receivables?', 'Show AR aging', "
    "'What invoices are overdue by age?' "
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

_AMOUNT_FIELDS = ["balance", "total", "amount", "bcy_total", "total_amount"]
_NAME_FIELDS = ["customer_name", "contact_name", "name", "company_name"]


def run(params: dict) -> dict:
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)

    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    # Fetch unpaid + overdue (deduplicated by invoice_id)
    seen_ids: set = set()
    records: list = []
    fetch_errors: list = []

    for status in ("unpaid", "overdue"):
        try:
            result = connector.list_invoices(status=status, limit=limit)
            batch = extract_records(result, ["invoices"])
            for rec in batch:
                iid = rec.get("invoice_id") or rec.get("id")
                if iid and iid in seen_ids:
                    continue
                if iid:
                    seen_ids.add(iid)
                records.append(rec)
        except Exception as e:
            fetch_errors.append(f"{status}: {e}")

    # Both fetches failed — report error rather than silently returning no data
    if len(fetch_errors) == 2:
        return error_response(
            "fetch_failed",
            "Both invoice status fetches failed. " + "; ".join(fetch_errors),
        )

    records_processed = len(records)

    if not records:
        return success_response(
            report="AR Aging Summary",
            records_processed=0,
            records_returned=0,
            narrative_cue="No unpaid or overdue invoices found.",
            total_outstanding=0.0,
            total_outstanding_formatted=format_inr(0),
            invoice_count=0,
            buckets={},
            critical_overdue_60_plus={"count": 0, "amount": 0.0, "amount_formatted": format_inr(0)},
            top_invoices=[],
        )

    buckets = bucket_by_due_date(records, _AMOUNT_FIELDS)
    total_outstanding = sum(b["amount"] for b in buckets.values())
    invoice_count = sum(b["count"] for b in buckets.values())

    # Add percentage share to each bucket
    for b in buckets.values():
        b["pct_of_total"] = pct(b["amount"], total_outstanding)

    critical_amt = (
        buckets["61_90_days"]["amount"] + buckets["90_plus_days"]["amount"]
    )
    critical_count = (
        buckets["61_90_days"]["count"] + buckets["90_plus_days"]["count"]
    )

    top_invs = top_records(
        records, _AMOUNT_FIELDS, _NAME_FIELDS, n=10,
        extra_fields=["invoice_number", "due_date", "status"],
    )

    return success_response(
        report="AR Aging Summary",
        records_processed=records_processed,
        records_returned=len(top_invs),
        narrative_cue=(
            f"Total outstanding: {format_inr(total_outstanding)} across "
            f"{invoice_count} invoices. "
            f"Critical (60+ days): {format_inr(critical_amt)} "
            f"({critical_count} invoices). "
            "Summarise by bucket and highlight critical overdue amounts."
        ),
        total_outstanding=total_outstanding,
        total_outstanding_formatted=format_inr(total_outstanding),
        invoice_count=invoice_count,
        buckets=buckets,
        critical_overdue_60_plus={
            "count": critical_count,
            "amount": critical_amt,
            "amount_formatted": format_inr(critical_amt),
        },
        top_invoices=top_invs,
    )
