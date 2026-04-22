"""Estimates Summary — proposal pipeline with conversion rate."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount,
    totals_by_currency, format_currency, success_response, error_response,
    _MULTI_CURRENCY_WARNING,
)

TOOL_NAME = "zb_estimates_summary"
TOOL_DESCRIPTION = (
    "Returns an Estimates (Quotes) Summary from Zoho Books. "
    "Use for 'Show estimates', 'Quote pipeline', 'What proposals are open?'. "
    "Includes conversion rate (accepted / (sent+accepted+declined)). "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "limit": {"type": "integer",
               "description": "Max records. Default: 200. Hard-capped at 500."},
}

_AMT_FIELDS = ["total", "estimate_total", "bcy_total", "amount"]
_OPEN_STATUSES = {"draft", "sent", "viewed"}
_CLOSED_STATUSES = {"accepted", "declined", "invoiced", "expired"}


def run(params: dict) -> dict:
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    warnings = []
    try:
        records = extract_records(connector.list_estimates(limit=limit), ["estimates"])
    except Exception as e:
        return error_response("fetch_failed", str(e))

    by_status: dict = {}
    for rec in records:
        status = str(rec.get("status") or "unknown").lower()
        amt = safe_amount(rec, _AMT_FIELDS)
        if status not in by_status:
            by_status[status] = {"count": 0, "amount": 0.0}
        by_status[status]["count"] += 1
        by_status[status]["amount"] += amt

    accepted = by_status.get("accepted", {}).get("count", 0)
    sent = by_status.get("sent", {}).get("count", 0)
    declined = by_status.get("declined", {}).get("count", 0)
    denom = sent + accepted + declined
    conversion_rate = round(accepted / denom, 4) if denom else None

    open_records = [r for r in records if str(r.get("status") or "").lower() in _OPEN_STATUSES]
    open_totals = totals_by_currency(open_records, _AMT_FIELDS)
    all_totals = totals_by_currency(records, _AMT_FIELDS)

    all_codes = set(all_totals)
    multi_currency = len(all_codes) > 1
    if multi_currency:
        warnings.append(_MULTI_CURRENCY_WARNING)

    return success_response(
        report="Estimates Summary",
        records_processed=len(records), records_returned=len(by_status),
        narrative_cue=(
            f"{len(records)} estimates across {len(by_status)} statuses. "
            f"{len(open_records)} open. "
            + (f"Conversion rate: {round(conversion_rate*100,1)}%. " if conversion_rate is not None else "")
            + ("Narrate each currency separately. " if multi_currency else "")
        ),
        total_estimates=len(records), open_estimate_count=len(open_records),
        by_status=by_status,
        conversion_rate=conversion_rate,
        open_proposals_totals_by_currency=open_totals,
        totals_by_currency=all_totals,
        multi_currency=multi_currency, warnings=warnings,
    )
