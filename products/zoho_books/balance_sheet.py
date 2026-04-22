"""Balance Sheet — operational estimate: AR, AP, cash, inventory."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records, safe_amount,
    totals_by_currency, format_currency, success_response, error_response,
    _MULTI_CURRENCY_WARNING, _ACCURACY_NOTE,
)

TOOL_NAME = "zb_balance_sheet"
TOOL_DESCRIPTION = (
    "Returns an estimated Balance Sheet summary for Zoho Books. "
    "Use for 'Show balance sheet', 'What are my assets and liabilities?'. "
    "OPERATIONAL ESTIMATE ONLY — not a statutory balance sheet. Verify before filings. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {
    "limit": {"type": "integer",
               "description": "Max contacts/items per source. Default: 200. Hard-capped at 500."},
}

_REC_FIELDS = ["outstanding_receivable_amount", "outstanding_receivable", "balance"]
_PAY_FIELDS = ["outstanding_payable_amount", "outstanding_payable", "balance"]
_BANK_FIELDS = ["current_balance", "balance", "amount"]


def run(params: dict) -> dict:
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    warnings = []
    ar_records = ap_records = bank_records = inv_records = []

    try:
        ar_records = extract_records(connector.list_contacts(contact_type="customer", limit=limit), ["contacts"])
    except Exception as e:
        warnings.append(f"AR fetch failed: {e}")
    try:
        ap_records = extract_records(connector.list_contacts(contact_type="vendor", limit=limit), ["contacts"])
    except Exception as e:
        warnings.append(f"AP fetch failed: {e}")
    try:
        bank_records = extract_records(connector._get("bankaccounts", {}), ["bank_accounts", "bankaccounts"])
    except Exception as e:
        warnings.append(f"Bank accounts fetch failed: {e}")
    try:
        inv_records = extract_records(connector.list_items(limit=limit), ["items"])
    except Exception as e:
        warnings.append(f"Inventory fetch failed: {e}")

    ar_by_currency = totals_by_currency(ar_records, _REC_FIELDS)
    ap_by_currency = totals_by_currency(ap_records, _PAY_FIELDS)
    bank_by_currency = totals_by_currency(bank_records, _BANK_FIELDS)

    # Inventory value: rate * stock_on_hand where available
    inv_value: dict = {}
    for item in inv_records:
        rate = safe_amount(item, ["rate", "purchase_rate", "selling_price"])
        stock = safe_amount(item, ["stock_on_hand", "available_stock", "quantity"])
        val = rate * stock
        code = item.get("currency_code") or "INR"
        inv_value[code] = inv_value.get(code, 0.0) + val

    all_codes = set(ar_by_currency) | set(ap_by_currency) | set(bank_by_currency) | set(inv_value)
    multi_currency = len(all_codes) > 1
    if multi_currency:
        warnings.append(_MULTI_CURRENCY_WARNING)

    net_position = {}
    for code in all_codes:
        ar = ar_by_currency.get(code, {}).get("amount", 0.0)
        ap = ap_by_currency.get(code, {}).get("amount", 0.0)
        cash = bank_by_currency.get(code, {}).get("amount", 0.0)
        inv = inv_value.get(code, 0.0)
        net = ar + cash + inv - ap
        net_position[code] = {
            "receivables": ar, "receivables_formatted": format_currency(ar, code),
            "payables": ap, "payables_formatted": format_currency(ap, code),
            "cash": cash, "cash_formatted": format_currency(cash, code),
            "inventory_value": inv, "inventory_formatted": format_currency(inv, code),
            "net": net, "net_formatted": format_currency(net, code),
        }

    return success_response(
        report="Balance Sheet (Estimate)",
        records_processed=len(ar_records) + len(ap_records) + len(bank_records) + len(inv_records),
        records_returned=len(net_position),
        narrative_cue=(
            "Estimated balance sheet from AR, AP, bank accounts, inventory. "
            + ("Narrate each currency separately. " if multi_currency else "")
            + "State this is an operational estimate — not a statutory balance sheet."
        ),
        assets_by_currency={c: {"receivables": v["receivables"], "cash": v["cash"], "inventory_value": v["inventory_value"]} for c, v in net_position.items()},
        liabilities_by_currency={c: {"payables": v["payables"]} for c, v in net_position.items()},
        net_position_by_currency=net_position,
        multi_currency=multi_currency,
        report_basis="operational_estimate_from_contacts_bankaccounts_items",
        accuracy_note=_ACCURACY_NOTE, warnings=warnings,
    )
