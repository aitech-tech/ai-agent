"""
Tests for the 5 implemented Zoho Books report scripts.
No live API calls — uses a fake connector monkeypatched via get_connector.
"""
import sys
import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Fake connector and monkeypatching helpers
# ---------------------------------------------------------------------------

class FakeConnector:
    """Fake ZohoBooksConnector that returns configurable fake data."""
    _authenticated = True

    def __init__(self, invoices=None, expenses=None, contacts=None):
        self._invoices = invoices or []
        self._expenses = expenses or []
        self._contacts = contacts or []

    def list_invoices(self, status=None, limit=200, organization_id=None):
        records = self._invoices
        if status:
            records = [r for r in records if r.get("status") == status]
        return {"success": True, "invoices": records[:limit], "count": len(records)}

    def list_expenses(self, status=None, limit=200, organization_id=None):
        records = self._expenses[:limit]
        return {"success": True, "expenses": records, "count": len(records)}

    def list_contacts(self, contact_type=None, limit=200, organization_id=None):
        records = self._contacts[:limit]
        return {"success": True, "contacts": records, "count": len(records)}


def _patch_connector(connector):
    """
    Monkeypatch get_connector in each script module.
    Scripts import get_connector by name, so we patch each module's local reference.
    """
    import products.zoho_books.ar_aging as _ar
    import products.zoho_books.overdue_invoices as _oi
    import products.zoho_books.invoice_summary as _is
    import products.zoho_books.expense_by_category as _ec
    import products.zoho_books.customer_balances as _cb

    _modules = [_ar, _oi, _is, _ec, _cb]
    origs = {}
    gc = lambda c=connector: c
    for mod in _modules:
        if hasattr(mod, "get_connector"):
            origs[mod.__name__] = (mod, mod.get_connector)
            mod.get_connector = gc
    return origs


def _restore_connector(origs):
    for _name, (mod, orig) in origs.items():
        mod.get_connector = orig


def _patch_today(year, month, day):
    import products.zoho_books._base as base
    orig = base.today
    base.today = lambda: datetime.date(year, month, day)
    return orig


def _restore_today(orig):
    import products.zoho_books._base as base
    base.today = orig


# ---------------------------------------------------------------------------
# Sample data factories
# ---------------------------------------------------------------------------

def _make_invoices(n=5, overdue=True):
    """Generate n fake invoice records."""
    today = datetime.date(2024, 4, 20)
    records = []
    for i in range(1, n + 1):
        days_ago = i * 15
        due = (today - datetime.timedelta(days=days_ago)).isoformat()
        records.append({
            "invoice_id": f"INV-{i:03d}",
            "invoice_number": f"INV-{i:03d}",
            "customer_name": f"Customer {i}",
            "status": "overdue" if overdue else "unpaid",
            "due_date": due,
            "date": (today - datetime.timedelta(days=days_ago + 30)).isoformat(),
            "balance": float(i * 10000),
            "total": float(i * 10000),
        })
    return records


def _make_expenses(n=5, date_str=None):
    """Generate n fake expense records."""
    d = date_str or "2024-04-10"
    categories = ["Travel", "Software", "Marketing", "Office", "Utilities"]
    records = []
    for i in range(1, n + 1):
        records.append({
            "expense_id": f"EXP-{i:03d}",
            "account_name": categories[i % len(categories)],
            "date": d,
            "amount": float(i * 5000),
            "total": float(i * 5000),
        })
    return records


def _make_customers(n=5):
    """Generate n fake customer contact records."""
    records = []
    for i in range(1, n + 1):
        records.append({
            "contact_id": f"CON-{i:03d}",
            "contact_name": f"Customer {i}",
            "contact_type": "customer",
            "email": f"cust{i}@example.com" if i % 2 == 0 else "",
            "outstanding_receivable_amount": float(i * 20000),
        })
    return records


# ---------------------------------------------------------------------------
# ar_aging tests
# ---------------------------------------------------------------------------

def test_ar_aging_success():
    """zb_ar_aging must return success with required fields."""
    from products.zoho_books import ar_aging
    connector = FakeConnector(invoices=_make_invoices(5, overdue=True))
    orig_c = _patch_connector(connector)
    orig_t = _patch_today(2024, 4, 20)
    try:
        result = ar_aging.run({})
        assert result["success"] is True
        assert result["report"] == "AR Aging Summary"
        assert "narrative_cue" in result
        assert result["raw_data_returned"] is False
        assert "currency" in result
        assert result["currency"] == "INR"
    finally:
        _restore_connector(orig_c)
        _restore_today(orig_t)
    print("PASS: test_ar_aging_success")


def test_ar_aging_empty_data():
    """zb_ar_aging must handle zero invoices gracefully."""
    from products.zoho_books import ar_aging
    connector = FakeConnector(invoices=[])
    orig_c = _patch_connector(connector)
    orig_t = _patch_today(2024, 4, 20)
    try:
        result = ar_aging.run({})
        assert result["success"] is True
        assert result["invoice_count"] == 0
        assert result["total_outstanding"] == 0.0
        assert result["narrative_cue"]
    finally:
        _restore_connector(orig_c)
        _restore_today(orig_t)
    print("PASS: test_ar_aging_empty_data")


def test_ar_aging_top_invoices_capped():
    """zb_ar_aging top_invoices must be capped at 10."""
    from products.zoho_books import ar_aging
    connector = FakeConnector(invoices=_make_invoices(20, overdue=True))
    orig_c = _patch_connector(connector)
    orig_t = _patch_today(2024, 4, 20)
    try:
        result = ar_aging.run({})
        assert len(result.get("top_invoices", [])) <= 10
    finally:
        _restore_connector(orig_c)
        _restore_today(orig_t)
    print("PASS: test_ar_aging_top_invoices_capped")


def test_ar_aging_missing_fields():
    """zb_ar_aging must handle records with missing balance/due_date."""
    from products.zoho_books import ar_aging
    records = [
        {"invoice_id": "1", "customer_name": "X", "status": "overdue"},
        {"invoice_id": "2", "status": "overdue", "due_date": "2024-01-01"},
    ]
    connector = FakeConnector(invoices=records)
    orig_c = _patch_connector(connector)
    orig_t = _patch_today(2024, 4, 20)
    try:
        result = ar_aging.run({})
        assert result["success"] is True
    finally:
        _restore_connector(orig_c)
        _restore_today(orig_t)
    print("PASS: test_ar_aging_missing_fields")


def test_ar_aging_computes_totals():
    """zb_ar_aging total_outstanding must equal sum of record balances."""
    from products.zoho_books import ar_aging
    records = [
        {"invoice_id": "1", "status": "overdue", "balance": 10000.0, "due_date": "2024-02-01"},
        {"invoice_id": "2", "status": "overdue", "balance": 20000.0, "due_date": "2024-01-01"},
    ]
    connector = FakeConnector(invoices=records)
    orig_c = _patch_connector(connector)
    orig_t = _patch_today(2024, 4, 20)
    try:
        result = ar_aging.run({})
        assert result["total_outstanding"] == 30000.0
        assert result["invoice_count"] == 2
    finally:
        _restore_connector(orig_c)
        _restore_today(orig_t)
    print("PASS: test_ar_aging_computes_totals")


def test_ar_aging_both_fetches_fail_returns_error():
    """zb_ar_aging must return success:False when both status fetches fail."""
    import products.zoho_books.ar_aging as ar_aging_mod

    class FailingConnector:
        _authenticated = True
        def list_invoices(self, status=None, limit=200, organization_id=None):
            raise RuntimeError(f"API error for status={status}")

    orig = ar_aging_mod.get_connector
    ar_aging_mod.get_connector = lambda: FailingConnector()
    try:
        result = ar_aging_mod.run({})
        assert result["success"] is False
        assert result["error"] == "fetch_failed"
        assert result["raw_data_returned"] is False
        assert "unpaid" in result["message"] or "overdue" in result["message"]
    finally:
        ar_aging_mod.get_connector = orig
    print("PASS: test_ar_aging_both_fetches_fail_returns_error")


def test_ar_aging_one_fetch_fails_other_has_records_returns_success():
    """zb_ar_aging must return success:True when one fetch fails but the other returns records."""
    import products.zoho_books.ar_aging as ar_aging_mod
    import products.zoho_books._base as base

    class PartialConnector:
        _authenticated = True
        def list_invoices(self, status=None, limit=200, organization_id=None):
            if status == "unpaid":
                raise RuntimeError("unpaid endpoint error")
            # overdue succeeds
            return {
                "success": True,
                "invoices": [
                    {"invoice_id": "1", "status": "overdue", "balance": 5000.0,
                     "due_date": "2024-02-01"},
                ],
            }

    orig_c = ar_aging_mod.get_connector
    orig_t = base.today
    ar_aging_mod.get_connector = lambda: PartialConnector()
    base.today = lambda: __import__("datetime").date(2024, 4, 20)
    try:
        result = ar_aging_mod.run({})
        assert result["success"] is True
        assert result["invoice_count"] == 1
        assert result["total_outstanding"] == 5000.0
    finally:
        ar_aging_mod.get_connector = orig_c
        base.today = orig_t
    print("PASS: test_ar_aging_one_fetch_fails_other_has_records_returns_success")


def test_ar_aging_auth_error():
    """zb_ar_aging must return error when not authenticated."""
    import products.zoho_books.ar_aging as ar_aging_mod
    orig = ar_aging_mod.get_connector

    def _raise():
        raise RuntimeError("Not authenticated. Authenticate with Zoho Books first.")

    ar_aging_mod.get_connector = _raise
    try:
        result = ar_aging_mod.run({})
        assert result["success"] is False
        assert result["error"] == "authentication_required"
        assert result["raw_data_returned"] is False
    finally:
        ar_aging_mod.get_connector = orig
    print("PASS: test_ar_aging_auth_error")


# ---------------------------------------------------------------------------
# overdue_invoices tests
# ---------------------------------------------------------------------------

def test_overdue_invoices_success():
    """zb_overdue_invoices must return success with required fields."""
    from products.zoho_books import overdue_invoices
    connector = FakeConnector(invoices=_make_invoices(5, overdue=True))
    orig_c = _patch_connector(connector)
    orig_t = _patch_today(2024, 4, 20)
    try:
        result = overdue_invoices.run({})
        assert result["success"] is True
        assert result["report"] == "Overdue Invoices"
        assert "narrative_cue" in result
        assert result["raw_data_returned"] is False
        assert result["currency"] == "INR"
    finally:
        _restore_connector(orig_c)
        _restore_today(orig_t)
    print("PASS: test_overdue_invoices_success")


def test_overdue_invoices_empty():
    """zb_overdue_invoices must handle empty data gracefully."""
    from products.zoho_books import overdue_invoices
    connector = FakeConnector(invoices=[])
    orig_c = _patch_connector(connector)
    orig_t = _patch_today(2024, 4, 20)
    try:
        result = overdue_invoices.run({})
        assert result["success"] is True
        assert result["invoice_count"] == 0
        assert "narrative_cue" in result
    finally:
        _restore_connector(orig_c)
        _restore_today(orig_t)
    print("PASS: test_overdue_invoices_empty")


def test_overdue_invoices_top_capped():
    """zb_overdue_invoices top_overdue_invoices must be capped at 10."""
    from products.zoho_books import overdue_invoices
    connector = FakeConnector(invoices=_make_invoices(15, overdue=True))
    orig_c = _patch_connector(connector)
    orig_t = _patch_today(2024, 4, 20)
    try:
        result = overdue_invoices.run({})
        assert len(result.get("top_overdue_invoices", [])) <= 10
        assert len(result.get("by_customer", [])) <= 10
    finally:
        _restore_connector(orig_c)
        _restore_today(orig_t)
    print("PASS: test_overdue_invoices_top_capped")


# ---------------------------------------------------------------------------
# invoice_summary tests
# ---------------------------------------------------------------------------

def test_invoice_summary_success():
    """zb_invoice_summary must return success with required fields."""
    from products.zoho_books import invoice_summary
    # Invoices dated in April 2024
    records = [
        {
            "invoice_id": f"I{i}", "status": "paid", "date": "2024-04-10",
            "total": 10000.0, "payment_made": 10000.0, "balance": 0.0,
        }
        for i in range(3)
    ]
    connector = FakeConnector(invoices=records)
    orig_c = _patch_connector(connector)
    orig_t = _patch_today(2024, 4, 20)
    try:
        result = invoice_summary.run({"period": "this_month"})
        assert result["success"] is True
        assert result["report"] == "Invoice Summary"
        assert result["raw_data_returned"] is False
        assert "narrative_cue" in result
        assert result["currency"] == "INR"
        assert result["invoice_count"] == 3
    finally:
        _restore_connector(orig_c)
        _restore_today(orig_t)
    print("PASS: test_invoice_summary_success")


def test_invoice_summary_period_filtering():
    """zb_invoice_summary must filter by period."""
    from products.zoho_books import invoice_summary
    records = [
        {"invoice_id": "1", "date": "2024-04-10", "status": "paid",
         "total": 1000.0, "payment_made": 1000.0, "balance": 0.0},
        {"invoice_id": "2", "date": "2024-03-05", "status": "paid",
         "total": 2000.0, "payment_made": 2000.0, "balance": 0.0},
    ]
    connector = FakeConnector(invoices=records)
    orig_c = _patch_connector(connector)
    orig_t = _patch_today(2024, 4, 20)
    try:
        result = invoice_summary.run({"period": "this_month"})
        # Only April invoice should match
        assert result["invoice_count"] == 1
        assert result["grand_total_value"] == 1000.0
    finally:
        _restore_connector(orig_c)
        _restore_today(orig_t)
    print("PASS: test_invoice_summary_period_filtering")


def test_invoice_summary_empty():
    """zb_invoice_summary must handle empty data."""
    from products.zoho_books import invoice_summary
    connector = FakeConnector(invoices=[])
    orig_c = _patch_connector(connector)
    orig_t = _patch_today(2024, 4, 20)
    try:
        result = invoice_summary.run({})
        assert result["success"] is True
        assert result["invoice_count"] == 0
    finally:
        _restore_connector(orig_c)
        _restore_today(orig_t)
    print("PASS: test_invoice_summary_empty")


def test_invoice_summary_warns_undated_records():
    """zb_invoice_summary must warn when records have no date."""
    from products.zoho_books import invoice_summary
    records = [
        {"invoice_id": "1", "status": "paid", "total": 1000.0},  # no date
    ]
    connector = FakeConnector(invoices=records)
    orig_c = _patch_connector(connector)
    orig_t = _patch_today(2024, 4, 20)
    try:
        result = invoice_summary.run({"period": "this_month"})
        assert result["success"] is True
        assert len(result.get("warnings", [])) > 0
    finally:
        _restore_connector(orig_c)
        _restore_today(orig_t)
    print("PASS: test_invoice_summary_warns_undated_records")


def test_invoice_summary_paid_fallback_from_balance():
    """zb_invoice_summary must infer paid = total - balance when payment fields are absent."""
    from products.zoho_books import invoice_summary
    records = [
        {
            "invoice_id": "1",
            "date": "2024-04-10",
            "status": "partial",
            "total": 1000.0,
            "balance": 200.0,
            # no payment_made or paid_amount fields
        }
    ]
    connector = FakeConnector(invoices=records)
    orig_c = _patch_connector(connector)
    orig_t = _patch_today(2024, 4, 20)
    try:
        result = invoice_summary.run({"period": "this_month"})
        assert result["success"] is True
        assert result["paid_amount"] == 800.0, \
            f"Expected paid_amount=800.0, got {result['paid_amount']}"
        # Collection rate should be 80%
        rate = result["collection_rate_pct"]
        assert "80" in rate, f"Expected ~80% collection rate, got {rate}"
    finally:
        _restore_connector(orig_c)
        _restore_today(orig_t)
    print("PASS: test_invoice_summary_paid_fallback_from_balance")


# ---------------------------------------------------------------------------
# expense_by_category tests
# ---------------------------------------------------------------------------

def test_expense_by_category_success():
    """zb_expense_by_category must return success with required fields."""
    from products.zoho_books import expense_by_category
    connector = FakeConnector(expenses=_make_expenses(5, date_str="2024-04-10"))
    orig_c = _patch_connector(connector)
    orig_t = _patch_today(2024, 4, 20)
    try:
        result = expense_by_category.run({"period": "this_month"})
        assert result["success"] is True
        assert result["report"] == "Expense by Category"
        assert result["raw_data_returned"] is False
        assert "narrative_cue" in result
        assert result["currency"] == "INR"
    finally:
        _restore_connector(orig_c)
        _restore_today(orig_t)
    print("PASS: test_expense_by_category_success")


def test_expense_by_category_grouping():
    """zb_expense_by_category must group by account_name."""
    from products.zoho_books import expense_by_category
    expenses = [
        {"expense_id": "1", "account_name": "Travel", "amount": 1000.0, "date": "2024-04-05"},
        {"expense_id": "2", "account_name": "Travel", "amount": 2000.0, "date": "2024-04-10"},
        {"expense_id": "3", "account_name": "Software", "amount": 5000.0, "date": "2024-04-15"},
    ]
    connector = FakeConnector(expenses=expenses)
    orig_c = _patch_connector(connector)
    orig_t = _patch_today(2024, 4, 20)
    try:
        result = expense_by_category.run({"period": "this_month"})
        assert result["success"] is True
        top_cats = result.get("top_categories", [])
        assert len(top_cats) == 2
        assert top_cats[0]["name"] == "Software"  # highest amount
        assert top_cats[0]["amount"] == 5000.0
    finally:
        _restore_connector(orig_c)
        _restore_today(orig_t)
    print("PASS: test_expense_by_category_grouping")


def test_expense_by_category_top_capped():
    """zb_expense_by_category top_categories must be capped at 10."""
    from products.zoho_books import expense_by_category
    expenses = [
        {"expense_id": str(i), "account_name": f"Cat{i}", "amount": float(i * 100),
         "date": "2024-04-10"}
        for i in range(1, 20)
    ]
    connector = FakeConnector(expenses=expenses)
    orig_c = _patch_connector(connector)
    orig_t = _patch_today(2024, 4, 20)
    try:
        result = expense_by_category.run({"period": "this_month"})
        assert len(result.get("top_categories", [])) <= 10
    finally:
        _restore_connector(orig_c)
        _restore_today(orig_t)
    print("PASS: test_expense_by_category_top_capped")


def test_expense_by_category_empty():
    """zb_expense_by_category must handle empty data."""
    from products.zoho_books import expense_by_category
    connector = FakeConnector(expenses=[])
    orig_c = _patch_connector(connector)
    orig_t = _patch_today(2024, 4, 20)
    try:
        result = expense_by_category.run({})
        assert result["success"] is True
        assert result["category_count"] == 0
    finally:
        _restore_connector(orig_c)
        _restore_today(orig_t)
    print("PASS: test_expense_by_category_empty")


# ---------------------------------------------------------------------------
# customer_balances tests
# ---------------------------------------------------------------------------

def test_customer_balances_success():
    """zb_customer_balances must return success with required fields."""
    from products.zoho_books import customer_balances
    connector = FakeConnector(contacts=_make_customers(5))
    orig_c = _patch_connector(connector)
    try:
        result = customer_balances.run({})
        assert result["success"] is True
        assert result["report"] == "Customer Balances"
        assert result["raw_data_returned"] is False
        assert "narrative_cue" in result
        assert result["currency"] == "INR"
    finally:
        _restore_connector(orig_c)
    print("PASS: test_customer_balances_success")


def test_customer_balances_top_capped():
    """zb_customer_balances top_customers must be capped at 10."""
    from products.zoho_books import customer_balances
    connector = FakeConnector(contacts=_make_customers(20))
    orig_c = _patch_connector(connector)
    try:
        result = customer_balances.run({})
        assert len(result.get("top_customers", [])) <= 10
    finally:
        _restore_connector(orig_c)
    print("PASS: test_customer_balances_top_capped")


def test_customer_balances_totals():
    """zb_customer_balances total_outstanding must be sum of balances."""
    from products.zoho_books import customer_balances
    contacts = [
        {"contact_id": "1", "contact_name": "A", "outstanding_receivable_amount": 10000.0, "email": "a@x.com"},
        {"contact_id": "2", "contact_name": "B", "outstanding_receivable_amount": 20000.0, "email": ""},
        {"contact_id": "3", "contact_name": "C", "outstanding_receivable_amount": 0.0, "email": "c@x.com"},
    ]
    connector = FakeConnector(contacts=contacts)
    orig_c = _patch_connector(connector)
    try:
        result = customer_balances.run({})
        assert result["total_outstanding"] == 30000.0
        assert result["customers_with_balance"] == 2
        assert result["zero_balance_count"] == 1
        assert result["missing_email_count"] == 1
    finally:
        _restore_connector(orig_c)
    print("PASS: test_customer_balances_totals")


def test_customer_balances_empty():
    """zb_customer_balances must handle empty contact list."""
    from products.zoho_books import customer_balances
    connector = FakeConnector(contacts=[])
    orig_c = _patch_connector(connector)
    try:
        result = customer_balances.run({})
        assert result["success"] is True
        assert result["customer_count"] == 0
        assert "narrative_cue" in result
    finally:
        _restore_connector(orig_c)
    print("PASS: test_customer_balances_empty")


def test_customer_balances_missing_amount_fields():
    """zb_customer_balances must handle contacts with no balance field."""
    from products.zoho_books import customer_balances
    contacts = [
        {"contact_id": "1", "contact_name": "NoBalance"},  # no balance field
    ]
    connector = FakeConnector(contacts=contacts)
    orig_c = _patch_connector(connector)
    try:
        result = customer_balances.run({})
        assert result["success"] is True
        assert result["total_outstanding"] == 0.0
    finally:
        _restore_connector(orig_c)
    print("PASS: test_customer_balances_missing_amount_fields")


if __name__ == "__main__":
    # ar_aging
    test_ar_aging_success()
    test_ar_aging_empty_data()
    test_ar_aging_top_invoices_capped()
    test_ar_aging_missing_fields()
    test_ar_aging_computes_totals()
    test_ar_aging_both_fetches_fail_returns_error()
    test_ar_aging_one_fetch_fails_other_has_records_returns_success()
    test_ar_aging_auth_error()
    # overdue_invoices
    test_overdue_invoices_success()
    test_overdue_invoices_empty()
    test_overdue_invoices_top_capped()
    # invoice_summary
    test_invoice_summary_success()
    test_invoice_summary_period_filtering()
    test_invoice_summary_empty()
    test_invoice_summary_warns_undated_records()
    test_invoice_summary_paid_fallback_from_balance()
    # expense_by_category
    test_expense_by_category_success()
    test_expense_by_category_grouping()
    test_expense_by_category_top_capped()
    test_expense_by_category_empty()
    # customer_balances
    test_customer_balances_success()
    test_customer_balances_top_capped()
    test_customer_balances_totals()
    test_customer_balances_empty()
    test_customer_balances_missing_amount_fields()
    print("\nAll Zoho Books report script tests passed.")
