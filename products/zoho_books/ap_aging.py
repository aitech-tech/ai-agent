"""AP Aging Summary — payables aging by due-date bucket from bills."""
import datetime
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, bucket_by_due_date,
    top_records, pct, format_currency, totals_by_currency,
    success_response, error_response, _MULTI_CURRENCY_WARNING,
)

TOOL_NAME = "zb_ap_aging"
TOOL_DESCRIPTION = (
    "Returns a pre-processed AP Aging Summary for Zoho Books. "
    "Use for 'Show AP aging', 'How old are my payables?', 'What bills are overdue by age?'. "
    "Reports open payables as of today, not a monthly period. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "limit": {"type": "integer",
               "description": "Maximum records to process. Default: 200. Hard-capped at 500."},
}

_AMOUNT_FIELDS = ["balance", "total", "amount", "bcy_total", "total_amount"]
_NAME_FIELDS = ["vendor_name", "contact_name", "name", "company_name"]


def run(params: dict) -> dict:
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    as_of = datetime.date.today().isoformat()
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))
    try:
        result = connector._get("bills", {"per_page": limit})
    except Exception as e:
        return error_response("fetch_failed", str(e))

    records = [r for r in extract_records(result, ["bills"])
               if str(r.get("status", "")).lower() in ("open", "overdue", "unpaid", "")]
    if not records:
        # Try without status filter in case all bills were returned already
        records = extract_records(result, ["bills"])

    if not records:
        return success_response(
            report="AP Aging Summary", records_processed=0, records_returned=0,
            narrative_cue="No open bills found.",
            as_of_date=as_of, report_basis="open_payables_as_of_date",
            total_outstanding=0.0, bill_count=0, buckets={},
            critical_overdue_60_plus={"count": 0, "amount": 0.0},
            top_bills=[], totals_by_currency={}, multi_currency=False, warnings=[],
        )

    by_currency = totals_by_currency(records, _AMOUNT_FIELDS)
    multi_currency = len(by_currency) > 1
    buckets = bucket_by_due_date(records, _AMOUNT_FIELDS)
    bill_count = sum(b["count"] for b in buckets.values())

    warnings = []
    if multi_currency:
        total_outstanding = None
        warnings.append(_MULTI_CURRENCY_WARNING)
        for b in buckets.values():
            b["pct_of_total"] = None
    else:
        total_outstanding = sum(b["amount"] for b in buckets.values())
        single_code = next(iter(by_currency))
        for b in buckets.values():
            b["pct_of_total"] = pct(b["amount"], total_outstanding)

    critical_count = buckets["61_90_days"]["count"] + buckets["90_plus_days"]["count"]
    critical_amt = buckets["61_90_days"]["amount"] + buckets["90_plus_days"]["amount"]
    single_code = next(iter(by_currency)) if by_currency else "INR"

    top_bills = top_records(records, _AMOUNT_FIELDS, _NAME_FIELDS, n=10,
                             extra_fields=["bill_number", "due_date", "status"])

    return success_response(
        report="AP Aging Summary", records_processed=len(records), records_returned=len(top_bills),
        narrative_cue=(
            f"{bill_count} open payables as of {as_of}. "
            + (f"Total: {format_currency(total_outstanding, single_code)}. " if not multi_currency else "Multiple currencies — narrate totals separately. ")
            + f"Critical (60+ days): {critical_count} bills. Summarise by bucket."
        ),
        as_of_date=as_of, report_basis="open_payables_as_of_date",
        total_outstanding=total_outstanding if not multi_currency else None,
        bill_count=bill_count, buckets=buckets,
        critical_overdue_60_plus={
            "count": critical_count,
            "amount": critical_amt if not multi_currency else None,
        },
        top_bills=top_bills, totals_by_currency=by_currency,
        multi_currency=multi_currency, warnings=warnings,
    )
