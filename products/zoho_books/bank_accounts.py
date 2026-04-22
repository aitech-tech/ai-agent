"""Bank Accounts — list of all bank/cash accounts with balances."""
from products.zoho_books._base import (
    get_connector, extract_records, safe_amount,
    totals_by_currency, format_currency, success_response, error_response,
    _MULTI_CURRENCY_WARNING,
)

TOOL_NAME = "zb_bank_accounts"
TOOL_DESCRIPTION = (
    "Returns a list of all bank and cash accounts from Zoho Books. "
    "Use for 'List bank accounts', 'Show all accounts', 'What accounts do we have?'. "
    "Returns each account with name, type, currency, and current balance. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {}

_BALANCE_FIELDS = ["current_balance", "balance", "amount"]


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
            "account_id": rec.get("account_id") or rec.get("id") or "",
            "account_name": rec.get("account_name") or rec.get("name") or "Unknown",
            "account_type": rec.get("account_type") or rec.get("type") or "Unknown",
            "currency_code": code,
            "balance": balance,
            "balance_formatted": format_currency(balance, code),
            "is_active": rec.get("is_active", True),
        })

    accounts.sort(key=lambda x: x["balance"], reverse=True)
    totals = totals_by_currency(records, _BALANCE_FIELDS)

    active = [a for a in accounts if a.get("is_active") is not False]
    multi_currency = len(set(totals)) > 1
    if multi_currency:
        warnings.append(_MULTI_CURRENCY_WARNING)

    by_type: dict = {}
    for acc in accounts:
        t = acc["account_type"]
        by_type[t] = by_type.get(t, 0) + 1

    return success_response(
        report="Bank Accounts",
        records_processed=len(records), records_returned=len(accounts),
        narrative_cue=(
            f"{len(accounts)} bank/cash account(s), {len(active)} active. "
            + ("Narrate each currency separately. " if multi_currency else "")
        ),
        account_count=len(accounts), active_count=len(active),
        accounts=accounts, by_type=by_type,
        totals_by_currency=totals,
        multi_currency=multi_currency, warnings=warnings,
    )
