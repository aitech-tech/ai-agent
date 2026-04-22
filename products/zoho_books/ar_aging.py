"""
AR Aging Summary — open receivables as of today, aged by due-date bucket.
"""
import datetime
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, bucket_by_due_date,
    top_records, pct, format_inr, format_currency, totals_by_currency,
    success_response, error_response, _MULTI_CURRENCY_WARNING,
)

TOOL_NAME = "zb_ar_aging"

TOOL_DESCRIPTION = (
    "Returns a pre-processed AR Aging Summary for Zoho Books. "
    "Use for questions like 'How are my receivables?', 'Show AR aging', "
    "'What invoices are overdue by age?' "
    "Reports open receivables as of today, not a monthly period. "
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
    as_of = datetime.date.today().isoformat()

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
            as_of_date=as_of,
            report_basis="open_receivables_as_of_date",
            total_outstanding=0.0,
            total_outstanding_formatted=format_inr(0),
            invoice_count=0,
            buckets={},
            critical_overdue_60_plus={"count": 0, "amount": 0.0, "amount_formatted": format_inr(0)},
            top_invoices=[],
            totals_by_currency={},
            multi_currency=False,
            warnings=[],
        )

    by_currency = totals_by_currency(records, _AMOUNT_FIELDS)
    multi_currency = len(by_currency) > 1

    buckets = bucket_by_due_date(records, _AMOUNT_FIELDS)
    invoice_count = sum(b["count"] for b in buckets.values())

    warnings: list = []
    if multi_currency:
        total_outstanding = None
        total_outstanding_formatted = None
        warnings.append(_MULTI_CURRENCY_WARNING)
        for b in buckets.values():
            b["pct_of_total"] = None
    else:
        total_outstanding = sum(b["amount"] for b in buckets.values())
        single_code = next(iter(by_currency))
        total_outstanding_formatted = format_currency(total_outstanding, single_code)
        for b in buckets.values():
            b["pct_of_total"] = pct(b["amount"], total_outstanding)

    critical_count = (
        buckets["61_90_days"]["count"] + buckets["90_plus_days"]["count"]
    )
    critical_amt = (
        buckets["61_90_days"]["amount"] + buckets["90_plus_days"]["amount"]
    )

    top_invs = top_records(
        records, _AMOUNT_FIELDS, _NAME_FIELDS, n=10,
        extra_fields=["invoice_number", "due_date", "status"],
    )

    if multi_currency:
        currency_summary = ", ".join(
            f"{code}: {data['amount_formatted']}"
            for code, data in by_currency.items()
        )
        narrative_cue = (
            f"{invoice_count} open receivables as of {as_of}. "
            f"Multiple currencies — narrate totals separately: {currency_summary}. "
            f"Critical (60+ days): {critical_count} invoices. "
            "Summarise by bucket and highlight critical overdue amounts per currency."
        )
    else:
        single_code = next(iter(by_currency))
        narrative_cue = (
            f"Total outstanding: {total_outstanding_formatted} across "
            f"{invoice_count} invoices as of {as_of}. "
            f"Critical (60+ days): {format_currency(critical_amt, single_code)} "
            f"({critical_count} invoices). "
            "Summarise by bucket and highlight critical overdue amounts."
        )

    critical_entry = {
        "count": critical_count,
        "amount": critical_amt if not multi_currency else None,
        "amount_formatted": (
            format_currency(critical_amt, next(iter(by_currency)))
            if not multi_currency else None
        ),
    }

    return success_response(
        report="AR Aging Summary",
        records_processed=records_processed,
        records_returned=len(top_invs),
        narrative_cue=narrative_cue,
        as_of_date=as_of,
        report_basis="open_receivables_as_of_date",
        total_outstanding=total_outstanding,
        total_outstanding_formatted=total_outstanding_formatted,
        invoice_count=invoice_count,
        buckets=buckets,
        critical_overdue_60_plus=critical_entry,
        top_invoices=top_invs,
        totals_by_currency=by_currency,
        multi_currency=multi_currency,
        warnings=warnings,
    )
