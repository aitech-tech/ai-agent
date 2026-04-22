"""Top Vendors by Spend — vendor spend from bills and expenses combined."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, group_amounts, filter_by_period,
    format_currency, totals_by_currency, success_response, error_response,
    _MULTI_CURRENCY_WARNING,
)

TOOL_NAME = "zb_top_vendors_spend"
TOOL_DESCRIPTION = (
    "Returns a pre-processed Top Vendors by Spend summary for Zoho Books. "
    "Use for 'Who are my top vendors by spend?', 'Largest vendor expenses'. "
    "Combines bills and expenses. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "period": {"type": "string",
                "description": "Time period: this_month, last_month, this_quarter, this_year, last_year. Default: this_month."},
    "limit": {"type": "integer",
               "description": "Max records per source. Default: 200. Hard-capped at 500."},
}

_BILL_AMOUNT = ["total", "balance", "amount", "bcy_total"]
_EXP_AMOUNT = ["total", "amount", "bcy_total"]
_VENDOR_FIELDS = ["vendor_name", "contact_name", "name", "company_name"]
_DATE_FIELDS = ["date", "bill_date", "created_time"]


def run(params: dict) -> dict:
    period = params.get("period", "this_month")
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    records, sources = [], []
    try:
        bills = extract_records(connector._get("bills", {"per_page": limit}), ["bills"])
        filtered_bills, _, from_str, to_str = filter_by_period(bills, _DATE_FIELDS, period)
        records.extend(filtered_bills)
        sources.append(f"bills({len(filtered_bills)})")
    except Exception:
        from_str = to_str = ""

    try:
        exps = extract_records(connector.list_expenses(limit=limit), ["expenses"])
        filtered_exps, _, from_str, to_str = filter_by_period(exps, _DATE_FIELDS, period)
        records.extend(filtered_exps)
        sources.append(f"expenses({len(filtered_exps)})")
    except Exception:
        pass

    if not records:
        return success_response(
            report="Top Vendors by Spend", records_processed=0, records_returned=0,
            narrative_cue=f"No vendor spend found for period '{period}'.",
            period=period, report_basis=f"combined: {', '.join(sources) or 'none'}",
            top_vendors=[], totals_by_currency={}, multi_currency=False, warnings=[],
        )

    by_currency = totals_by_currency(records, _BILL_AMOUNT)
    multi_currency = len(by_currency) > 1
    warnings = [_MULTI_CURRENCY_WARNING] if multi_currency else []
    single_total = sum(v["amount"] for v in by_currency.values()) if not multi_currency else None
    single_code = next(iter(by_currency)) if by_currency else "INR"

    top_vendors = group_amounts(records, _VENDOR_FIELDS, _BILL_AMOUNT, limit=10)

    return success_response(
        report="Top Vendors by Spend", records_processed=len(records), records_returned=len(top_vendors),
        narrative_cue=(
            f"{len(records)} records ({', '.join(sources)}) for {period}"
            + (f". Total spend: {format_currency(single_total, single_code)}. " if not multi_currency else " across multiple currencies. ")
            + "List top vendors by total spend."
        ),
        period=period, date_range={"from": from_str, "to": to_str},
        report_basis=f"combined: {', '.join(sources)}",
        total_spend=single_total, top_vendors=top_vendors,
        totals_by_currency=by_currency, multi_currency=multi_currency, warnings=warnings,
    )
