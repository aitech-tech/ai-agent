"""Trial Balance — account groups from chart of accounts."""
from products.zoho_books._base import (
    get_connector, extract_records, safe_amount,
    success_response, error_response, _ACCURACY_NOTE,
)

TOOL_NAME = "zb_trial_balance"
TOOL_DESCRIPTION = (
    "Returns a Trial Balance summary from the Zoho Books chart of accounts. "
    "Use for 'Show trial balance', 'List accounts by type'. "
    "OPERATIONAL ESTIMATE — account balances from the list API may be incomplete. "
    "Verify in Zoho Books before statutory use. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)
TOOL_PARAMS = {}


def run(params: dict) -> dict:
    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))
    try:
        result = connector._get("chartofaccounts", {})
    except Exception as e:
        return error_response("fetch_failed", str(e))

    records = extract_records(result, ["chartofaccounts", "chart_of_accounts"])
    if not records:
        return success_response(
            report="Trial Balance (Estimate)", records_processed=0, records_returned=0,
            narrative_cue="No chart of accounts data found.",
            account_count=0, by_account_type={},
            report_basis="chart_of_accounts_list_api", accuracy_note=_ACCURACY_NOTE, warnings=[],
        )

    by_type: dict = {}
    for acc in records:
        atype = str(acc.get("account_type") or acc.get("type") or "Unknown").title()
        balance = safe_amount(acc, ["closing_balance", "balance", "current_balance"])
        if atype not in by_type:
            by_type[atype] = {"count": 0, "balance": 0.0}
        by_type[atype]["count"] += 1
        by_type[atype]["balance"] += balance

    warnings = ["Account balances from the list API may be incomplete or reflect list-level summaries only. Use Zoho Books reports for authoritative figures."]

    return success_response(
        report="Trial Balance (Estimate)", records_processed=len(records),
        records_returned=len(by_type),
        narrative_cue=(
            f"{len(records)} accounts across {len(by_type)} types. "
            "State that this is an estimate from chart-of-accounts list data — "
            "not an authoritative trial balance."
        ),
        account_count=len(records), by_account_type=by_type,
        report_basis="chart_of_accounts_list_api",
        accuracy_note=_ACCURACY_NOTE, warnings=warnings,
    )
