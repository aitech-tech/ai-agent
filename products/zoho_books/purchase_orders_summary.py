"""Purchase Orders Summary — PO status breakdown and committed value."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount, group_amounts,
    format_currency, totals_by_currency, success_response, error_response,
    _MULTI_CURRENCY_WARNING,
)

TOOL_NAME = "zb_purchase_orders_summary"
TOOL_DESCRIPTION = (
    "Returns a pre-processed Purchase Orders Summary for Zoho Books. "
    "Use for 'Show purchase orders', 'What is my open PO value?', 'PO status breakdown'. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "limit": {"type": "integer",
               "description": "Maximum records to process. Default: 200. Hard-capped at 500."},
}

_AMOUNT_FIELDS = ["total", "amount", "bcy_total", "total_amount"]
_NAME_FIELDS = ["vendor_name", "contact_name", "name", "company_name"]


def run(params: dict) -> dict:
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))
    try:
        result = connector.list_purchase_orders(limit=limit)
    except Exception as e:
        return error_response("fetch_failed", str(e))

    records = extract_records(result, ["purchase_orders", "purchaseorders"])
    if not records:
        return success_response(
            report="Purchase Orders Summary", records_processed=0, records_returned=0,
            narrative_cue="No purchase orders found.",
            po_count=0, by_status={}, top_vendors=[], totals_by_currency={},
            multi_currency=False, warnings=[],
        )

    by_status: dict = {}
    for rec in records:
        status = str(rec.get("status", "unknown")).lower()
        amt = safe_amount(rec, _AMOUNT_FIELDS)
        if status not in by_status:
            by_status[status] = {"count": 0, "amount": 0.0}
        by_status[status]["count"] += 1
        by_status[status]["amount"] += amt

    by_currency = totals_by_currency(records, _AMOUNT_FIELDS)
    multi_currency = len(by_currency) > 1
    warnings = [_MULTI_CURRENCY_WARNING] if multi_currency else []
    single_total = sum(v["amount"] for v in by_currency.values()) if not multi_currency else None
    single_code = next(iter(by_currency)) if by_currency else "INR"

    # Open POs
    open_records = [r for r in records if str(r.get("status", "")).lower() in ("open", "draft", "issued", "pending_approval")]
    open_by_currency = totals_by_currency(open_records, _AMOUNT_FIELDS)

    top_vendors = group_amounts(records, _NAME_FIELDS, _AMOUNT_FIELDS, limit=10)
    status_summary = {k: v for k, v in sorted(by_status.items(), key=lambda x: -x[1]["count"])}

    return success_response(
        report="Purchase Orders Summary", records_processed=len(records), records_returned=len(top_vendors),
        narrative_cue=(
            f"{len(records)} purchase orders"
            + (f" totalling {format_currency(single_total, single_code)}. " if not multi_currency else " across multiple currencies. ")
            + "Status breakdown: " + ", ".join(f"{k}:{v['count']}" for k, v in list(status_summary.items())[:4]) + ". "
            + "Highlight open/uncommitted value."
        ),
        po_count=len(records), total_value=single_total,
        by_status=status_summary, open_po_totals_by_currency=open_by_currency,
        top_vendors=top_vendors, totals_by_currency=by_currency,
        multi_currency=multi_currency, warnings=warnings,
    )
