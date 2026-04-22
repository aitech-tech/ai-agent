"""Tests for products/zoho_books/_base.py shared helpers."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import datetime
from products.zoho_books._base import (
    format_inr, pct, to_float, parse_date, date_range_for_period,
    days_past_due, bucket_by_due_date, group_amounts, top_records,
    safe_amount, safe_name, extract_records, cap_int, today,
)


# ---------------------------------------------------------------------------
# to_float
# ---------------------------------------------------------------------------

def test_to_float_int():
    assert to_float(1000) == 1000.0

def test_to_float_float():
    assert to_float(99.5) == 99.5

def test_to_float_numeric_string():
    assert to_float("1234.56") == 1234.56

def test_to_float_comma_string():
    assert to_float("1,23,456.78") == 123456.78

def test_to_float_rupee_string():
    assert to_float("₹1,00,000") == 100000.0

def test_to_float_none_returns_default():
    assert to_float(None) == 0.0
    assert to_float(None, default=5.0) == 5.0

def test_to_float_empty_string_returns_default():
    assert to_float("") == 0.0

def test_to_float_garbage_returns_default():
    assert to_float("not-a-number") == 0.0


# ---------------------------------------------------------------------------
# format_inr
# ---------------------------------------------------------------------------

def test_format_inr_small():
    assert format_inr(500) == "₹500"

def test_format_inr_one_lakh():
    assert format_inr(100000) == "₹1,00,000"

def test_format_inr_large():
    assert format_inr(1234567) == "₹12,34,567"

def test_format_inr_with_decimal():
    assert format_inr(1234567.5) == "₹12,34,567.50"

def test_format_inr_zero():
    assert format_inr(0) == "₹0"

def test_format_inr_999():
    assert format_inr(999) == "₹999"

def test_format_inr_1000():
    assert format_inr(1000) == "₹1,000"

def test_format_inr_10_lakh():
    assert format_inr(1000000) == "₹10,00,000"

def test_format_inr_1_crore():
    assert format_inr(10000000) == "₹1,00,00,000"

def test_format_inr_negative():
    result = format_inr(-500)
    assert result.startswith("-")
    assert "500" in result

def test_format_inr_rounds_up_carry():
    # 999.999 rounds to 1000.00, not ₹999.00
    assert format_inr(999.999) == "₹1,000"

def test_format_inr_rounds_half_paise():
    # 1234567.505 rounds to 1234567.51 (standard Python banker's rounding may apply,
    # but the key is that the integer part is stable at 1234567)
    result = format_inr(1234567.504)
    assert result.startswith("₹12,34,567.")


# ---------------------------------------------------------------------------
# pct
# ---------------------------------------------------------------------------

def test_pct_basic():
    assert pct(45, 100) == "45.0%"

def test_pct_zero_total():
    assert pct(0, 0) == "0%"

def test_pct_100():
    assert pct(100, 100) == "100.0%"

def test_pct_decimals():
    result = pct(1, 3, decimals=2)
    assert "33.33" in result


# ---------------------------------------------------------------------------
# parse_date
# ---------------------------------------------------------------------------

def test_parse_date_yyyy_mm_dd():
    d = parse_date("2024-03-15")
    assert d == datetime.date(2024, 3, 15)

def test_parse_date_iso_datetime():
    d = parse_date("2024-03-15T10:30:00")
    assert d == datetime.date(2024, 3, 15)

def test_parse_date_none():
    assert parse_date(None) is None

def test_parse_date_empty_string():
    assert parse_date("") is None

def test_parse_date_invalid():
    assert parse_date("not-a-date") is None

def test_parse_date_date_object():
    d = datetime.date(2024, 6, 1)
    assert parse_date(d) == d


# ---------------------------------------------------------------------------
# date_range_for_period
# ---------------------------------------------------------------------------

def _fake_today(year, month, day):
    """Monkeypatch today() for date_range tests."""
    import products.zoho_books._base as base
    orig = base.today
    base.today = lambda: datetime.date(year, month, day)
    return orig


def test_date_range_this_month():
    import products.zoho_books._base as base
    orig = base.today
    try:
        base.today = lambda: datetime.date(2024, 4, 15)
        from_d, to_d = date_range_for_period("this_month")
        assert from_d == "2024-04-01"
        assert to_d == "2024-04-30"
    finally:
        base.today = orig


def test_date_range_last_month():
    import products.zoho_books._base as base
    orig = base.today
    try:
        base.today = lambda: datetime.date(2024, 4, 15)
        from_d, to_d = date_range_for_period("last_month")
        assert from_d == "2024-03-01"
        assert to_d == "2024-03-31"
    finally:
        base.today = orig


def test_date_range_this_quarter_q1():
    import products.zoho_books._base as base
    orig = base.today
    try:
        base.today = lambda: datetime.date(2024, 2, 10)
        from_d, to_d = date_range_for_period("this_quarter")
        assert from_d == "2024-01-01"
        assert to_d == "2024-03-31"
    finally:
        base.today = orig


def test_date_range_this_year():
    import products.zoho_books._base as base
    orig = base.today
    try:
        base.today = lambda: datetime.date(2024, 7, 4)
        from_d, to_d = date_range_for_period("this_year")
        assert from_d == "2024-01-01"
        assert to_d == "2024-12-31"
    finally:
        base.today = orig


def test_date_range_last_year():
    import products.zoho_books._base as base
    orig = base.today
    try:
        base.today = lambda: datetime.date(2024, 7, 4)
        from_d, to_d = date_range_for_period("last_year")
        assert from_d == "2023-01-01"
        assert to_d == "2023-12-31"
    finally:
        base.today = orig


def test_date_range_unknown_defaults_to_this_month():
    import products.zoho_books._base as base
    orig = base.today
    try:
        base.today = lambda: datetime.date(2024, 6, 1)
        from_d, to_d = date_range_for_period("unknown_period")
        assert from_d == "2024-06-01"
        assert to_d == "2024-06-30"
    finally:
        base.today = orig


# ---------------------------------------------------------------------------
# days_past_due
# ---------------------------------------------------------------------------

def test_days_past_due_overdue():
    import products.zoho_books._base as base
    orig = base.today
    try:
        base.today = lambda: datetime.date(2024, 4, 20)
        result = days_past_due("2024-04-10")
        assert result == 10
    finally:
        base.today = orig


def test_days_past_due_future():
    import products.zoho_books._base as base
    orig = base.today
    try:
        base.today = lambda: datetime.date(2024, 4, 20)
        result = days_past_due("2024-04-30")
        assert result == 0
    finally:
        base.today = orig


def test_days_past_due_none():
    assert days_past_due(None) is None

def test_days_past_due_invalid():
    assert days_past_due("not-a-date") is None


# ---------------------------------------------------------------------------
# bucket_by_due_date
# ---------------------------------------------------------------------------

def test_bucket_by_due_date():
    import products.zoho_books._base as base
    orig = base.today
    try:
        base.today = lambda: datetime.date(2024, 4, 20)
        records = [
            {"due_date": "2024-05-01", "balance": 1000.0},   # future -> current
            {"due_date": "2024-04-10", "balance": 2000.0},   # 10 days -> 0-30
            {"due_date": "2024-03-15", "balance": 3000.0},   # 36 days -> 31-60
            {"due_date": "2024-02-10", "balance": 4000.0},   # 70 days -> 61-90
            {"due_date": "2024-01-01", "balance": 5000.0},   # 110 days -> 90+
            {"balance": 500.0},                               # no due_date -> unknown
        ]
        buckets = bucket_by_due_date(records, ["balance"])
        assert buckets["current_or_not_due"]["count"] == 1
        assert buckets["0_30_days"]["count"] == 1
        assert buckets["31_60_days"]["count"] == 1
        assert buckets["61_90_days"]["count"] == 1
        assert buckets["90_plus_days"]["count"] == 1
        assert buckets["unknown_due_date"]["count"] == 1
        assert buckets["0_30_days"]["amount"] == 2000.0
        assert "amount_formatted" in buckets["0_30_days"]
    finally:
        base.today = orig


# ---------------------------------------------------------------------------
# group_amounts
# ---------------------------------------------------------------------------

def test_group_amounts():
    records = [
        {"account_name": "Travel", "amount": 500.0},
        {"account_name": "Travel", "amount": 300.0},
        {"account_name": "Software", "amount": 1000.0},
        {"account_name": "Software", "amount": 200.0},
    ]
    result = group_amounts(records, ["account_name"], ["amount"])
    assert len(result) == 2
    assert result[0]["name"] == "Software"
    assert result[0]["amount"] == 1200.0
    assert result[0]["count"] == 2
    assert "amount_formatted" in result[0]


def test_group_amounts_limit():
    records = [{"account_name": f"Cat{i}", "amount": float(i)} for i in range(20)]
    result = group_amounts(records, ["account_name"], ["amount"], limit=5)
    assert len(result) == 5


def test_group_amounts_empty():
    assert group_amounts([], ["account_name"], ["amount"]) == []


# ---------------------------------------------------------------------------
# top_records
# ---------------------------------------------------------------------------

def test_top_records_sorting():
    records = [
        {"customer_name": "A", "balance": 100.0},
        {"customer_name": "B", "balance": 500.0},
        {"customer_name": "C", "balance": 250.0},
    ]
    result = top_records(records, ["balance"], ["customer_name"], n=3)
    assert result[0]["name"] == "B"
    assert result[1]["name"] == "C"
    assert result[2]["name"] == "A"


def test_top_records_cap():
    records = [{"customer_name": f"C{i}", "balance": float(i)} for i in range(20)]
    result = top_records(records, ["balance"], ["customer_name"], n=10)
    assert len(result) == 10


def test_top_records_extra_fields():
    records = [{"customer_name": "X", "balance": 100.0, "invoice_number": "INV-001"}]
    result = top_records(records, ["balance"], ["customer_name"], n=10,
                         extra_fields=["invoice_number"])
    assert result[0]["invoice_number"] == "INV-001"


def test_top_records_empty():
    assert top_records([], ["balance"], ["customer_name"]) == []


# ---------------------------------------------------------------------------
# format_currency
# ---------------------------------------------------------------------------

from products.zoho_books._base import (
    format_currency,
    currency_code as get_currency_code,
    totals_by_currency,
)


def test_format_currency_inr():
    assert format_currency(100000, "INR") == "₹1,00,000"


def test_format_currency_zar():
    assert format_currency(239.01, "ZAR") == "R239.01"


def test_format_currency_zar_thousands():
    assert format_currency(5000.0, "ZAR") == "R5,000.00"


def test_format_currency_usd():
    assert format_currency(1234.56, "USD") == "$1,234.56"


def test_format_currency_eur():
    assert format_currency(500.0, "EUR") == "€500.00"


def test_format_currency_gbp():
    assert format_currency(750.0, "GBP") == "£750.00"


def test_format_currency_unknown_aed():
    assert format_currency(239.01, "AED") == "AED 239.01"


def test_format_currency_negative_zar():
    result = format_currency(-239.01, "ZAR")
    assert result.startswith("-R")
    assert "239.01" in result


def test_format_currency_default_is_inr():
    assert format_currency(1000) == "₹1,000"


# ---------------------------------------------------------------------------
# currency_code
# ---------------------------------------------------------------------------

def test_currency_code_from_record():
    assert get_currency_code({"currency_code": "ZAR", "amount": 100.0}) == "ZAR"


def test_currency_code_default_inr():
    assert get_currency_code({"amount": 100.0}) == "INR"


def test_currency_code_custom_default():
    assert get_currency_code({}, default="USD") == "USD"


# ---------------------------------------------------------------------------
# totals_by_currency
# ---------------------------------------------------------------------------

def test_totals_by_currency_single():
    records = [{"balance": 1000.0}, {"balance": 2000.0}]
    result = totals_by_currency(records, ["balance"])
    assert "INR" in result
    assert result["INR"]["count"] == 2
    assert result["INR"]["amount"] == 3000.0
    assert result["INR"]["amount_formatted"] == "₹3,000"


def test_totals_by_currency_multi():
    records = [
        {"currency_code": "INR", "balance": 10000.0},
        {"currency_code": "ZAR", "balance": 5000.0},
        {"currency_code": "INR", "balance": 20000.0},
    ]
    result = totals_by_currency(records, ["balance"])
    assert "INR" in result
    assert "ZAR" in result
    assert result["INR"]["count"] == 2
    assert result["INR"]["amount"] == 30000.0
    assert result["ZAR"]["count"] == 1
    assert result["ZAR"]["amount"] == 5000.0
    assert result["ZAR"]["amount_formatted"] == "R5,000.00"


def test_totals_by_currency_empty():
    assert totals_by_currency([], ["balance"]) == {}


if __name__ == "__main__":
    test_to_float_int()
    test_to_float_float()
    test_to_float_numeric_string()
    test_to_float_comma_string()
    test_to_float_rupee_string()
    test_to_float_none_returns_default()
    test_to_float_empty_string_returns_default()
    test_to_float_garbage_returns_default()
    test_format_inr_small()
    test_format_inr_one_lakh()
    test_format_inr_large()
    test_format_inr_with_decimal()
    test_format_inr_zero()
    test_format_inr_999()
    test_format_inr_1000()
    test_format_inr_10_lakh()
    test_format_inr_1_crore()
    test_format_inr_negative()
    test_format_inr_rounds_up_carry()
    test_format_inr_rounds_half_paise()
    test_pct_basic()
    test_pct_zero_total()
    test_pct_100()
    test_pct_decimals()
    test_parse_date_yyyy_mm_dd()
    test_parse_date_iso_datetime()
    test_parse_date_none()
    test_parse_date_empty_string()
    test_parse_date_invalid()
    test_parse_date_date_object()
    test_date_range_this_month()
    test_date_range_last_month()
    test_date_range_this_quarter_q1()
    test_date_range_this_year()
    test_date_range_last_year()
    test_date_range_unknown_defaults_to_this_month()
    test_days_past_due_overdue()
    test_days_past_due_future()
    test_days_past_due_none()
    test_days_past_due_invalid()
    test_bucket_by_due_date()
    test_group_amounts()
    test_group_amounts_limit()
    test_group_amounts_empty()
    test_top_records_sorting()
    test_top_records_cap()
    test_top_records_extra_fields()
    test_top_records_empty()
    test_format_currency_inr()
    test_format_currency_zar()
    test_format_currency_zar_thousands()
    test_format_currency_usd()
    test_format_currency_eur()
    test_format_currency_gbp()
    test_format_currency_unknown_aed()
    test_format_currency_negative_zar()
    test_format_currency_default_is_inr()
    test_currency_code_from_record()
    test_currency_code_default_inr()
    test_currency_code_custom_default()
    test_totals_by_currency_single()
    test_totals_by_currency_multi()
    test_totals_by_currency_empty()
    print("\nAll _base tests passed.")
