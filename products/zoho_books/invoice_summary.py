"""
Invoice Summary — status breakdown and collection metrics for a period.
"""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount, parse_date,
    date_range_for_period, format_inr, pct, success_response, error_response,
)

TOOL_NAME = "zb_invoice_summary"

TOOL_DESCRIPTION = (
    "Returns a pre-processed Invoice Summary for Zoho Books. "
    "Use for questions like 'How are my invoices this month?', "
    "'What is the invoice collection rate?', 'Show invoice status breakdown.' "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)

TOOL_PARAMS = {
    "period": {
        "type": "string",
        "description": (
            "Time period: this_month, last_month, this_quarter, last_quarter, "
            "this_year, last_year. Default: this_month."
        ),
    },
    "limit": {
        "type": "integer",
        "description": "Maximum records to process locally. Default: 200. Hard-capped at 500.",
    },
}

_AMOUNT_FIELDS = ["total", "invoice_total", "bcy_total", "amount", "total_amount"]
_PAID_FIELDS = ["payment_made", "paid_amount"]
_BALANCE_FIELDS = ["balance", "outstanding_receivable_amount"]
_DATE_FIELDS = ["date", "invoice_date", "created_time"]


def run(params: dict) -> dict:
    period = params.get("period", "this_month")
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)

    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    try:
        result = connector.list_invoices(limit=limit)
    except Exception as e:
        return error_response("fetch_failed", str(e))

    all_records = extract_records(result, ["invoices"])
    records_processed_raw = len(all_records)

    from_date_str, to_date_str = date_range_for_period(period)
    from_date = parse_date(from_date_str)
    to_date = parse_date(to_date_str)

    filtered: list = []
    no_date_count = 0
    warnings: list = []

    for rec in all_records:
        rec_date = None
        for field in _DATE_FIELDS:
            rec_date = parse_date(rec.get(field))
            if rec_date:
                break

        if rec_date is None:
            no_date_count += 1
            filtered.append(rec)  # Include undated records
            continue

        if from_date <= rec_date <= to_date:
            filtered.append(rec)

    if no_date_count:
        warnings.append(
            f"{no_date_count} invoice(s) had no usable date field and were included without period filtering."
        )

    records_processed = len(filtered)

    if not filtered:
        return success_response(
            report="Invoice Summary",
            records_processed=0,
            records_returned=0,
            narrative_cue=f"No invoices found for period '{period}'.",
            period=period,
            date_range={"from": from_date_str, "to": to_date_str},
            grand_total_value=0.0,
            grand_total_formatted=format_inr(0),
            paid_amount=0.0,
            paid_amount_formatted=format_inr(0),
            outstanding_amount=0.0,
            outstanding_formatted=format_inr(0),
            invoice_count=0,
            collection_rate_pct="0%",
            by_status={},
            warnings=warnings,
        )

    grand_total = 0.0
    paid_total = 0.0
    outstanding_total = 0.0
    by_status: dict = {}

    for rec in filtered:
        total_amt = safe_amount(rec, _AMOUNT_FIELDS)
        balance_amt = safe_amount(rec, _BALANCE_FIELDS)

        explicit_paid = safe_amount(rec, _PAID_FIELDS)
        if explicit_paid == 0 and total_amt > 0 and balance_amt < total_amt:
            # No explicit payment field; infer paid = total - balance
            paid_amt = max(total_amt - balance_amt, 0.0)
        else:
            paid_amt = explicit_paid

        grand_total += total_amt
        paid_total += paid_amt
        outstanding_total += balance_amt

        status = str(rec.get("status", "unknown")).lower()
        if status not in by_status:
            by_status[status] = {"count": 0, "amount": 0.0, "amount_formatted": ""}
        by_status[status]["count"] += 1
        by_status[status]["amount"] += total_amt

    for s in by_status.values():
        s["amount_formatted"] = format_inr(s["amount"])

    collection_rate = pct(paid_total, grand_total) if grand_total else "0%"

    return success_response(
        report="Invoice Summary",
        records_processed=records_processed,
        records_returned=records_processed,
        narrative_cue=(
            f"{records_processed} invoices for {period}. "
            f"Total value: {format_inr(grand_total)}, "
            f"Collected: {format_inr(paid_total)} ({collection_rate}), "
            f"Outstanding: {format_inr(outstanding_total)}. "
            "Summarise by status and highlight collection rate."
        ),
        period=period,
        date_range={"from": from_date_str, "to": to_date_str},
        grand_total_value=grand_total,
        grand_total_formatted=format_inr(grand_total),
        paid_amount=paid_total,
        paid_amount_formatted=format_inr(paid_total),
        outstanding_amount=outstanding_total,
        outstanding_formatted=format_inr(outstanding_total),
        invoice_count=records_processed,
        collection_rate_pct=collection_rate,
        by_status=by_status,
        warnings=warnings,
    )
