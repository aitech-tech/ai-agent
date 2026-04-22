"""
Shared helpers for all Zoho Books report scripts.

Import from here — do not duplicate logic in individual scripts.
"""
import calendar
import datetime
import logging
import re

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connector access
# ---------------------------------------------------------------------------

def get_connector():
    """Return the active ZohoBooksConnector from the registry."""
    from registry.connector_registry import registry
    try:
        connector = registry.get("zoho_books")
    except Exception as exc:
        raise RuntimeError(
            "Not authenticated. Authenticate with Zoho Books first."
        ) from exc
    if not connector._authenticated:
        raise RuntimeError(
            "Not authenticated. Authenticate with Zoho Books first."
        )
    return connector


# ---------------------------------------------------------------------------
# Number helpers
# ---------------------------------------------------------------------------

def to_float(value, default: float = 0.0) -> float:
    """
    Safely convert int, float, numeric string, comma-formatted string,
    or strings containing ₹ to float. Returns default on failure.
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("₹", "").replace(",", "").strip()
        if not cleaned:
            return default
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return default
    return default


def format_inr(amount: float) -> str:
    """
    Format a number in Indian Rupee style.

    Examples:
        500       -> ₹500
        100000    -> ₹1,00,000
        1234567   -> ₹12,34,567
        1234567.5 -> ₹12,34,567.50
    """
    negative = amount < 0
    abs_amount = round(abs(amount), 2)  # round first to avoid carry-over split
    integer_part = int(abs_amount)
    decimal_part = round(abs_amount - integer_part, 2)

    # Indian grouping: last 3 digits, then groups of 2
    s = str(integer_part)
    if len(s) <= 3:
        formatted = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        groups: list[str] = []
        while len(rest) > 2:
            groups.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.append(rest)
        groups.reverse()
        formatted = ",".join(groups) + "," + last3

    if decimal_part >= 0.005:
        dec_str = f"{decimal_part:.2f}"[1:]  # ".XX"
        result = f"₹{formatted}{dec_str}"
    else:
        result = f"₹{formatted}"

    return f"-{result}" if negative else result


def pct(part: float, total: float, decimals: int = 1) -> str:
    """Return percentage string. Returns '0%' when total is zero."""
    if not total:
        return "0%"
    return f"{round(part / total * 100, decimals)}%"


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def today() -> datetime.date:
    """Wrapper around datetime.date.today() — monkeypatched in tests."""
    return datetime.date.today()


def parse_date(value) -> "datetime.date | None":
    """Parse YYYY-MM-DD or ISO datetime strings. Returns None if invalid/empty."""
    if not value:
        return None
    if isinstance(value, datetime.date):
        return value
    s = str(value).strip()
    if len(s) >= 10:
        try:
            return datetime.date.fromisoformat(s[:10])
        except ValueError:
            return None
    return None


def date_range_for_period(period: str) -> tuple:
    """
    Return (from_date, to_date) as YYYY-MM-DD strings for a named period.
    Supports: this_month, last_month, this_quarter, last_quarter, this_year, last_year.
    Defaults to this_month for unknown periods.
    """
    t = today()

    if period == "last_month":
        first_of_this = t.replace(day=1)
        to_d = first_of_this - datetime.timedelta(days=1)
        from_d = to_d.replace(day=1)

    elif period == "this_quarter":
        q = (t.month - 1) // 3
        start_month = q * 3 + 1
        end_month = start_month + 2
        last_day = calendar.monthrange(t.year, end_month)[1]
        from_d = t.replace(month=start_month, day=1)
        to_d = t.replace(month=end_month, day=last_day)

    elif period == "last_quarter":
        q = (t.month - 1) // 3
        last_q = q - 1
        if last_q < 0:
            last_q = 3
            year = t.year - 1
        else:
            year = t.year
        start_month = last_q * 3 + 1
        end_month = start_month + 2
        last_day = calendar.monthrange(year, end_month)[1]
        from_d = datetime.date(year, start_month, 1)
        to_d = datetime.date(year, end_month, last_day)

    elif period == "this_year":
        from_d = t.replace(month=1, day=1)
        to_d = t.replace(month=12, day=31)

    elif period == "last_year":
        from_d = datetime.date(t.year - 1, 1, 1)
        to_d = datetime.date(t.year - 1, 12, 31)

    else:
        # this_month (default)
        from_d = t.replace(day=1)
        last_day = calendar.monthrange(t.year, t.month)[1]
        to_d = t.replace(day=last_day)

    return from_d.strftime("%Y-%m-%d"), to_d.strftime("%Y-%m-%d")


def days_past_due(due_date_value) -> "int | None":
    """
    Return number of days an invoice is past its due date.
    Positive = overdue. 0 = due today or future. None = no/invalid due date.
    """
    d = parse_date(due_date_value)
    if d is None:
        return None
    delta = (today() - d).days
    return max(0, delta)


def filter_by_period(records: list, date_fields: list, period: str) -> tuple:
    """
    Filter records to those whose date falls within the named period.
    Returns (filtered_records, no_date_count, from_date_str, to_date_str).
    Records with no usable date are included in filtered (counted separately).
    """
    from_date_str, to_date_str = date_range_for_period(period)
    from_date = parse_date(from_date_str)
    to_date = parse_date(to_date_str)
    filtered, no_date_count = [], 0
    for rec in records:
        rec_date = None
        for field in date_fields:
            rec_date = parse_date(rec.get(field))
            if rec_date:
                break
        if rec_date is None:
            no_date_count += 1
            filtered.append(rec)
        elif from_date <= rec_date <= to_date:
            filtered.append(rec)
    return filtered, no_date_count, from_date_str, to_date_str


def first_record_by_date(records: list, date_field: str) -> "dict | None":
    """Return the record with the earliest value in date_field, or None."""
    oldest_date, oldest = None, None
    for rec in records:
        d = parse_date(rec.get(date_field))
        if d is not None and (oldest_date is None or d < oldest_date):
            oldest_date, oldest = d, rec
    return oldest


# ---------------------------------------------------------------------------
# Record field helpers
# ---------------------------------------------------------------------------

def safe_amount(record: dict, field_candidates: list) -> float:
    """
    Try field names in order, returning the first non-zero numeric value found.
    Handles formatted currency strings (₹, commas).
    """
    for field in field_candidates:
        val = record.get(field)
        if val is not None and val != "" and val != 0:
            f = to_float(val)
            if f != 0.0:
                return f
    # If all are zero or missing, return 0 from first present field
    for field in field_candidates:
        val = record.get(field)
        if val is not None and val != "":
            return to_float(val)
    return 0.0


def safe_name(record: dict, field_candidates: list, fallback: str = "Unknown") -> str:
    """Return first non-empty string value from field_candidates, or fallback."""
    for field in field_candidates:
        val = record.get(field)
        if val and str(val).strip():
            return str(val).strip()
    return fallback


def extract_records(result: dict, candidate_keys: list) -> list:
    """
    Given a connector result dict, return the first list found under candidate_keys.
    Returns [] if none found.
    """
    if not isinstance(result, dict):
        return []
    for key in candidate_keys:
        val = result.get(key)
        if isinstance(val, list):
            return val
    return []


def cap_int(value, default: int, minimum: int, maximum: int) -> int:
    """Parse value as int and clamp to [minimum, maximum]. Returns default on error."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, n))


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

_AMOUNT_FIELDS = ["balance", "balance_formatted", "total", "amount", "total_amount",
                   "invoice_total", "bcy_total"]
_NAME_FIELDS = ["customer_name", "vendor_name", "contact_name", "name", "company_name"]


def bucket_by_due_date(records: list, amount_fields: list, due_date_field: str = "due_date") -> dict:
    """
    Sort records into AR/AP aging buckets based on days past due.
    Returns dict with keys: current_or_not_due, 0_30_days, 31_60_days,
    61_90_days, 90_plus_days, unknown_due_date.
    Each bucket has count, amount, amount_formatted.
    """
    buckets: dict = {
        "current_or_not_due": {"count": 0, "amount": 0.0},
        "0_30_days": {"count": 0, "amount": 0.0},
        "31_60_days": {"count": 0, "amount": 0.0},
        "61_90_days": {"count": 0, "amount": 0.0},
        "90_plus_days": {"count": 0, "amount": 0.0},
        "unknown_due_date": {"count": 0, "amount": 0.0},
    }

    for rec in records:
        amt = safe_amount(rec, amount_fields)
        dpd = days_past_due(rec.get(due_date_field))

        if dpd is None:
            key = "unknown_due_date"
        elif dpd == 0:
            key = "current_or_not_due"
        elif dpd <= 30:
            key = "0_30_days"
        elif dpd <= 60:
            key = "31_60_days"
        elif dpd <= 90:
            key = "61_90_days"
        else:
            key = "90_plus_days"

        buckets[key]["count"] += 1
        buckets[key]["amount"] += amt

    for key, b in buckets.items():
        b["amount_formatted"] = format_inr(b["amount"])

    return buckets


def top_records(
    records: list,
    amount_fields: list,
    name_fields: list,
    n: int = 10,
    extra_fields: "list | None" = None,
) -> list:
    """
    Return the top n records sorted descending by amount.
    Each entry has name, amount, amount_formatted plus any present extra_fields.
    Capped at n.
    """
    scored = []
    for rec in records:
        amt = safe_amount(rec, amount_fields)
        name = safe_name(rec, name_fields)
        entry: dict = {
            "name": name,
            "amount": amt,
            "amount_formatted": format_inr(amt),
        }
        for field in (extra_fields or []):
            val = rec.get(field)
            if val is not None:
                entry[field] = val
        scored.append(entry)

    scored.sort(key=lambda x: x["amount"], reverse=True)
    return scored[:n]


def group_amounts(
    records: list,
    key_fields: list,
    amount_fields: list,
    limit: int = 10,
) -> list:
    """
    Group records by the first available key field, sum amounts, count records.
    Returns top groups sorted descending by amount, capped at limit.
    Each entry: name, count, amount, amount_formatted.
    """
    groups: dict = {}
    for rec in records:
        key = safe_name(rec, key_fields, fallback="Unknown")
        amt = safe_amount(rec, amount_fields)
        if key not in groups:
            groups[key] = {"count": 0, "amount": 0.0}
        groups[key]["count"] += 1
        groups[key]["amount"] += amt

    result = [
        {
            "name": name,
            "count": data["count"],
            "amount": data["amount"],
            "amount_formatted": format_inr(data["amount"]),
        }
        for name, data in groups.items()
    ]
    result.sort(key=lambda x: x["amount"], reverse=True)
    return result[:limit]


def group_by_month(records: list, date_fields: list, amount_fields: list) -> list:
    """
    Group records by YYYY-MM, summing amounts.
    Returns sorted list of {month, count, amount, amount_formatted}.
    Records with no usable date are skipped.
    """
    months: dict = {}
    for rec in records:
        rec_date = None
        for field in date_fields:
            rec_date = parse_date(rec.get(field))
            if rec_date:
                break
        if rec_date is None:
            continue
        key = rec_date.strftime("%Y-%m")
        amt = safe_amount(rec, amount_fields)
        if key not in months:
            months[key] = {"count": 0, "amount": 0.0}
        months[key]["count"] += 1
        months[key]["amount"] += amt
    return [
        {"month": k, "count": v["count"], "amount": v["amount"],
         "amount_formatted": format_inr(v["amount"])}
        for k, v in sorted(months.items())
    ]


# ---------------------------------------------------------------------------
# Currency helpers
# ---------------------------------------------------------------------------

_CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "ZAR": "R",
}

_MULTI_CURRENCY_WARNING = (
    "Multiple currencies detected. Totals are grouped by currency and are not converted."
)

_ACCURACY_NOTE = (
    "Operational estimate from available API list data. "
    "Verify in Zoho Books and with your accountant before statutory use or filings."
)


def currency_code(record: dict, default: str = "INR") -> str:
    """Return the currency code from a record dict, falling back to default.

    Checks fields in order: currency_code, currency, currency_id.
    Returns an uppercase stripped value; falls back to uppercase default.
    """
    for field in ("currency_code", "currency", "currency_id"):
        val = record.get(field)
        if val and str(val).strip():
            return str(val).strip().upper()
    return default.strip().upper()


def format_currency(amount: float, currency_code: str = "INR") -> str:
    """
    Format an amount with its currency symbol/code.
    INR uses Indian grouping (format_inr); others use standard 2-decimal formatting.
    Examples: ZAR -> R1,234.56  USD -> $1,234.56  AED -> AED 1,234.56
    """
    if currency_code == "INR":
        return format_inr(amount)
    negative = amount < 0
    formatted = f"{abs(amount):,.2f}"
    sym = _CURRENCY_SYMBOLS.get(currency_code)
    result = f"{sym}{formatted}" if sym else f"{currency_code} {formatted}"
    return f"-{result}" if negative else result


def totals_by_currency(records: list, amount_fields: list) -> dict:
    """
    Group records by currency_code, sum amounts.
    Returns {code: {count, amount, amount_formatted}}.
    """
    groups: dict = {}
    for rec in records:
        code = currency_code(rec)
        amt = safe_amount(rec, amount_fields)
        if code not in groups:
            groups[code] = {"count": 0, "amount": 0.0}
        groups[code]["count"] += 1
        groups[code]["amount"] += amt
    return {
        code: {
            "count": data["count"],
            "amount": data["amount"],
            "amount_formatted": format_currency(data["amount"], code),
        }
        for code, data in groups.items()
    }


# ---------------------------------------------------------------------------
# Standard response builders
# ---------------------------------------------------------------------------

def success_response(
    report: str,
    records_processed: int,
    records_returned: int,
    narrative_cue: str,
    **extra,
) -> dict:
    """Build a standard success response dict."""
    base = {
        "success": True,
        "report": report,
        "currency": "INR",
        "records_processed": records_processed,
        "records_returned": records_returned,
        "raw_data_returned": False,
        "narrative_cue": narrative_cue,
    }
    base.update(extra)
    return base


def error_response(error: str, message: str = "") -> dict:
    """Build a standard error response dict."""
    return {
        "success": False,
        "error": error,
        "message": message,
        "raw_data_returned": False,
    }
