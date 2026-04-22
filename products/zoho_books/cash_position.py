"""Cash Position — current bank and cash account balances."""
from products.zoho_books._base import (
    get_connector, extract_records, safe_amount,
    totals_by_currency, format_currency, success_response, error_response,
    _MULTI_CURRENCY_WARNING,
)

TOOL_NAME = "zb_cash_position"
TOOL_DESCRIPTION = (
    "Returns the current Cash Position from Zoho Books bank accounts. "
    "Use for 'What is our cash position?', 'How much cash do we have?', 'Bank balance'. "
    "Returns per-account balances and currency-grouped totals. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {}

_BALANCE_FIELDS = ["current_balance", "balance", "amount"]
_CASH_TYPES = {"cash", "bank", "credit_card", "savings"}


def run(params: dict) -> dict:
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    warnings = []
    try:
        result = connector._get("bankaccounts", {})
        records = extract_records(result, ["bank_accounts", "bankaccounts"])
    except Exception as e:
        return error_response("fetch_failed", str(e))

    accounts = []
    for rec in records:
        balance = safe_amount(rec, _BALANCE_FIELDS)
        code = rec.get("currency_code") or "INR"
        accounts.append({
            "account_name": rec.get("account_name") or rec.get("name") or "Unknown",
            "account_type": rec.get("account_type") or rec.get("type") or "Unknown",
            "currency_code": code,
            "balance": balance,
            "balance_formatted": format_currency(balance, code),
        })

    accounts.sort(key=lambda x: x["balance"], reverse=True)
    totals = totals_by_currency(records, _BALANCE_FIELDS)

    multi_currency = len(set(totals)) > 1
    if multi_currency:
        warnings.append(_MULTI_CURRENCY_WARNING)

    negative_balance_accounts = [a for a in accounts if a["balance"] < 0]
    if negative_balance_accounts:
        warnings.append(f"{len(negative_balance_accounts)} account(s) have a negative balance.")

    return success_response(
        report="Cash Position",
        records_processed=len(records), records_returned=len(accounts),
        narrative_cue=(
            f"Cash position: {len(accounts)} account(s). "
            + (f"{len(negative_balance_accounts)} negative. " if negative_balance_accounts else "")
            + ("Narrate each currency separately. " if multi_currency else "")
        ),
        account_count=len(accounts),
        accounts=accounts,
        totals_by_currency=totals,
        multi_currency=multi_currency, warnings=warnings,
    )
