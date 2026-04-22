# Python Pre-Processing Scripts

## Why these scripts exist

The raw Zoho Books MCP tools (`zoho_books_list_invoices`, `zoho_books_list_expenses`, etc.) return full API payloads — potentially hundreds of JSON records per call. When Claude uses these for reporting, every raw record travels through the MCP protocol into Claude's context window, consuming tokens and hitting Claude Desktop session limits fast.

**Pre-processing scripts** solve this by running locally in Python, close to the data:

1. Fetch records from the Zoho Books API using the existing connector.
2. Filter, group, and aggregate in Python — zero round-trips to Claude.
3. Return a **compact narrative-ready summary** (a few dozen fields instead of thousands).

Claude receives the summary and narrates it. It does not re-process numbers.

---

## Raw tools vs. pre-processed tools

| Aspect | `zoho_books_list_*` raw tools | `zb_*` pre-processed tools |
|---|---|---|
| Returns | Full Zoho API JSON | Compact summary dict |
| Token cost | High (all record fields) | Low (aggregated fields only) |
| Use for | Create / update / delete, auth, drilldown | Reporting and analysis |
| Filtering | Server-side only | Local Python, any field |
| Aggregation | None | Bucketing, grouping, totals |

---

## Standard script interface

Every script in `products/zoho_books/` must expose:

```python
TOOL_NAME = "zb_some_report"        # unique, must start with zb_

TOOL_DESCRIPTION = (
    "Returns a pre-processed <report name> summary for Zoho Books. "
    "Use for <business purpose>. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)

TOOL_PARAMS = {
    "period": {
        "type": "string",
        "description": "Time period: this_month, last_month, this_quarter, last_quarter, this_year, last_year. Default: this_month."
    },
    "limit": {
        "type": "integer",
        "description": "Maximum records to process locally. Default: 200. Hard-capped by the script."
    }
}

def run(params: dict) -> dict:
    ...
```

The `script_loader.py` discovers and registers every file that satisfies this interface automatically — no manual registration needed.

---

## Output contract

Every successful `run()` return value must include:

| Field | Type | Description |
|---|---|---|
| `success` | bool | Always `True` |
| `report` | str | Human-readable report name |
| `currency` | str | Always `"INR"` |
| `records_processed` | int | Records fetched and processed locally |
| `records_returned` | int | Records in the summary (capped) |
| `raw_data_returned` | bool | Always `False` |
| `narrative_cue` | str | One-sentence prompt to guide Claude's narration |

Error responses return `success: False`, `error`, `message`, `raw_data_returned: False`.

---

## Array caps

To protect Claude's context window, all arrays returned to Claude are capped:

- Top records, top customers, top invoices: **10 items max**
- Grouped results: **10 groups max**
- Item/price list: **50 items max** (documented exception in manifest)

---

## How to add a new script

1. Create `products/zoho_books/my_report.py`.
2. Define `TOOL_NAME`, `TOOL_DESCRIPTION`, `TOOL_PARAMS`, and `run(params)`.
3. Import helpers from `products.zoho_books._base` — do not duplicate logic.
4. Use `get_connector()` to access the Zoho Books API.
5. Return a dict using `success_response(...)` or `error_response(...)`.
6. Update `manifest.json`: change `status` from `"planned"` to `"implemented"`.
7. Add tests in `tests/test_zoho_report_scripts.py` with a fake connector.

The script loader picks up new scripts automatically on next server start — no changes to `main.py`, `tools.py`, or any other file.

---

## Safety rules

- **No raw payload dumps**: Never return a full Zoho API record in the output.
- **Cap all arrays**: Top records max 10, groups max 10, price lists max 50.
- **Always include `narrative_cue`**: Tells Claude how to open the narration.
- **Handle missing fields**: Use `safe_amount()`, `safe_name()`, `.get(field)` — never `record["field"]`.
- **No live API calls in tests**: Monkeypatch `get_connector` to return a fake connector.
- **`raw_data_returned: False`**: Must be explicit in every response.

---

## Example script skeleton

```python
"""My Report — short description."""
from products.zoho_books._base import (
    get_connector, cap_int, extract_records,
    success_response, error_response, format_inr,
)

TOOL_NAME = "zb_my_report"

TOOL_DESCRIPTION = (
    "Returns a pre-processed My Report summary for Zoho Books. "
    "Use for <purpose>. "
    "Returns a compact summary ready for narrative reporting. "
    "Call this tool first, then write the narrative directly from the result. "
    "Do not perform further calculations or fetch raw data unless the user asks for drilldown."
)

TOOL_PARAMS = {
    "limit": {
        "type": "integer",
        "description": "Maximum records to process locally. Default: 200. Hard-capped at 500.",
    }
}


def run(params: dict) -> dict:
    limit = cap_int(params.get("limit", 200), default=200, minimum=1, maximum=500)

    try:
        connector = get_connector()
    except RuntimeError as e:
        return error_response("authentication_required", str(e))

    try:
        result = connector.list_invoices(limit=limit)
    except Exception as e:
        return error_response("fetch_failed", str(e))

    records = extract_records(result, ["invoices"])

    if not records:
        return success_response(
            report="My Report",
            records_processed=0,
            records_returned=0,
            narrative_cue="No records found.",
        )

    # ... aggregate, compute, cap arrays ...

    return success_response(
        report="My Report",
        records_processed=len(records),
        records_returned=10,
        narrative_cue="Summarise the key findings.",
        total=1234.56,
        total_formatted=format_inr(1234.56),
    )
```
