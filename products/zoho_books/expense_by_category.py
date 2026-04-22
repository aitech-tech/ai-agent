"""
Expense by Category — expense breakdown grouped by account/category for a period.
"""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount, parse_date,
    date_range_for_period, group_amounts, format_inr, pct,
    success_response, error_response,
)

TOOL_NAME = "zb_expense_by_category"

TOOL_DESCRIPTION = (
    "Returns a pre-processed Expense by Category summary for Zoho Books. "
    "Use for questions like 'What did I spend on this month?', "
    "'Break down expenses by category', 'What is my biggest expense category?' "
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

_AMOUNT_FIELDS = ["total", "amount", "bcy_total", "total_amount"]
_CATEGORY_FIELDS = ["account_name", "category_name", "expense_category", "account_id"]
_DATE_FIELDS = ["date", "expense_date", "created_time"]


def run(params: dict) -> dict:
    period = params.get("period", "this_month")
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)

    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    try:
        result = connector.list_expenses(limit=limit)
    except Exception as e:
        return error_response("fetch_failed", str(e))

    all_records = extract_records(result, ["expenses"])

    from_date_str, to_date_str = date_range_for_period(period)
    from_date = parse_date(from_date_str)
    to_date = parse_date(to_date_str)

    filtered: list = []
    no_date_count = 0

    for rec in all_records:
        rec_date = None
        for field in _DATE_FIELDS:
            rec_date = parse_date(rec.get(field))
            if rec_date:
                break

        if rec_date is None:
            no_date_count += 1
            filtered.append(rec)
            continue

        if from_date <= rec_date <= to_date:
            filtered.append(rec)

    records_processed = len(filtered)

    warnings: list = []
    if no_date_count:
        warnings.append(
            f"{no_date_count} expense(s) had no usable date field and were included without period filtering."
        )

    if not filtered:
        return success_response(
            report="Expense by Category",
            records_processed=0,
            records_returned=0,
            narrative_cue=f"No expenses found for period '{period}'.",
            period=period,
            date_range={"from": from_date_str, "to": to_date_str},
            total_expenses=0.0,
            total_expenses_formatted=format_inr(0),
            category_count=0,
            highest_category=None,
            top_categories=[],
            warnings=warnings,
        )

    total_expenses = sum(safe_amount(rec, _AMOUNT_FIELDS) for rec in filtered)
    top_cats = group_amounts(filtered, _CATEGORY_FIELDS, _AMOUNT_FIELDS, limit=10)
    category_count = len(top_cats)

    highest = top_cats[0] if top_cats else None
    if highest:
        highest = dict(highest)
        highest["pct_of_total"] = pct(highest["amount"], total_expenses)

    return success_response(
        report="Expense by Category",
        records_processed=records_processed,
        records_returned=len(top_cats),
        narrative_cue=(
            f"{records_processed} expenses for {period}. "
            f"Total: {format_inr(total_expenses)} across {category_count} categories. "
            + (
                f"Highest: {highest['name']} at {highest['amount_formatted']} "
                f"({highest['pct_of_total']} of total). "
                if highest else ""
            )
            + "Summarise by category and highlight top spends."
        ),
        period=period,
        date_range={"from": from_date_str, "to": to_date_str},
        total_expenses=total_expenses,
        total_expenses_formatted=format_inr(total_expenses),
        category_count=category_count,
        highest_category=highest,
        top_categories=top_cats,
        warnings=warnings,
    )
