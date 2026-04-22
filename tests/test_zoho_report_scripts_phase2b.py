"""
Tests for the 35 Phase 2B Zoho Books report scripts.
No live API calls — uses an extended FakeConnector with _get support.
"""
import sys
import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Extended FakeConnector with _get support
# ---------------------------------------------------------------------------

class FakeConnector:
    _authenticated = True

    def __init__(self, invoices=None, expenses=None, contacts=None,
                 customer_payments=None, salesorders=None, estimates=None,
                 purchase_orders=None, items=None, get_data=None):
        self._invoices = invoices or []
        self._expenses = expenses or []
        self._contacts = contacts or []
        self._customer_payments = customer_payments or []
        self._salesorders = salesorders or []
        self._estimates = estimates or []
        self._purchase_orders = purchase_orders or []
        self._items = items or []
        self._get_data = get_data or {}  # path -> response dict

    def list_invoices(self, status=None, limit=200, organization_id=None):
        records = [r for r in self._invoices if not status or r.get("status") == status]
        return {"success": True, "invoices": records[:limit]}

    def list_expenses(self, status=None, limit=200, organization_id=None):
        return {"success": True, "expenses": self._expenses[:limit]}

    def list_contacts(self, contact_type=None, limit=200, organization_id=None):
        records = [r for r in self._contacts if not contact_type or r.get("contact_type") == contact_type]
        return {"success": True, "contacts": records[:limit]}

    def list_customer_payments(self, limit=200, organization_id=None):
        return {"success": True, "customer_payments": self._customer_payments[:limit]}

    def list_salesorders(self, limit=200, organization_id=None):
        return {"success": True, "salesorders": self._salesorders[:limit]}

    def list_estimates(self, limit=200, organization_id=None):
        return {"success": True, "estimates": self._estimates[:limit]}

    def list_purchase_orders(self, limit=200, organization_id=None):
        return {"success": True, "purchase_orders": self._purchase_orders[:limit]}

    def list_items(self, limit=200, organization_id=None):
        return {"success": True, "items": self._items[:limit]}

    def _get(self, path, params=None):
        if path in self._get_data:
            return self._get_data[path]
        return {"success": True}


def _patch(module, connector):
    orig = module.get_connector
    module.get_connector = lambda: connector
    return orig


def _restore(module, orig):
    module.get_connector = orig


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

TODAY = datetime.date(2026, 4, 22)
THIS_MONTH = "2026-04"

def _inv(i, status="paid", date="2026-04-10", amount=10000.0, currency="INR", customer=None):
    return {"invoice_id": f"INV-{i}", "status": status, "date": date,
            "total": amount, "bcy_total": amount, "balance": 0.0 if status == "paid" else amount,
            "customer_name": customer or f"Customer {i}", "currency_code": currency}

def _exp(i, cat="Travel", date="2026-04-10", amount=5000.0, currency="INR"):
    return {"expense_id": f"EXP-{i}", "account_name": cat, "date": date,
            "amount": amount, "total": amount, "currency_code": currency}

def _contact(i, ctype="customer", balance=10000.0, currency="INR"):
    return {"contact_id": f"CON-{i}", "contact_name": f"Contact {i}",
            "contact_type": ctype, "email": f"c{i}@test.com",
            "outstanding_receivable_amount": balance if ctype == "customer" else 0.0,
            "outstanding_payable_amount": balance if ctype == "vendor" else 0.0,
            "balance": balance, "currency_code": currency}

def _pmt(i, mode="cash", date="2026-04-10", amount=8000.0, currency="INR"):
    return {"payment_id": f"PMT-{i}", "payment_mode": mode, "date": date,
            "amount": amount, "currency_code": currency, "customer_name": f"Customer {i}"}

def _bill(i, status="open", vendor=None, date="2026-04-10", due="2026-05-01", amount=6000.0):
    return {"bill_id": f"BILL-{i}", "status": status, "vendor_name": vendor or f"Vendor {i}",
            "date": date, "due_date": due, "total": amount, "balance": amount,
            "currency_code": "INR"}

def _item(i, rate=1000.0, stock=10.0, product_type="goods"):
    return {"item_id": f"ITEM-{i}", "name": f"Item {i}", "rate": rate,
            "purchase_rate": rate * 0.8, "stock_on_hand": stock,
            "product_type": product_type, "currency_code": "INR",
            "reorder_level": 5.0 if stock <= 5.0 else 2.0}


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

def test_vendor_balances_success():
    import products.zoho_books.vendor_balances as mod
    connector = FakeConnector(contacts=[_contact(i, "vendor") for i in range(1, 4)])
    orig = _patch(mod, connector)
    try:
        r = mod.run({})
        assert r["success"] is True
        assert r["vendor_count"] == 3
        assert r["total_outstanding"] > 0
    finally:
        _restore(mod, orig)
    print("PASS: test_vendor_balances_success")


def test_vendor_balances_empty():
    import products.zoho_books.vendor_balances as mod
    connector = FakeConnector(contacts=[])
    orig = _patch(mod, connector)
    try:
        r = mod.run({})
        assert r["success"] is True
        assert r["vendor_count"] == 0
    finally:
        _restore(mod, orig)
    print("PASS: test_vendor_balances_empty")


def test_contact_list_counts():
    import products.zoho_books.contact_list as mod
    contacts = [_contact(i, "customer") for i in range(1, 4)] + [_contact(i, "vendor") for i in range(4, 6)]
    connector = FakeConnector(contacts=contacts)
    orig = _patch(mod, connector)
    try:
        r = mod.run({})
        assert r["success"] is True
        assert r["customer_count"] == 3
        assert r["vendor_count"] == 2
        assert r["total_count"] == 5
    finally:
        _restore(mod, orig)
    print("PASS: test_contact_list_counts")


def test_contact_aging_buckets():
    import products.zoho_books.contact_aging as mod
    contacts = [
        _contact(1, "customer", balance=0.0),
        _contact(2, "customer", balance=5000.0),
        _contact(3, "customer", balance=50000.0),
        _contact(4, "customer", balance=200000.0),
    ]
    connector = FakeConnector(contacts=contacts)
    orig = _patch(mod, connector)
    try:
        r = mod.run({})
        assert r["success"] is True
        buckets = r["buckets"]
        assert buckets["zero"] == 1
        assert buckets["1_to_10k"] == 1
        assert buckets["10k_to_1lakh"] == 1
        assert buckets["1lakh_plus"] == 1
    finally:
        _restore(mod, orig)
    print("PASS: test_contact_aging_buckets")


# ---------------------------------------------------------------------------
# Receivables
# ---------------------------------------------------------------------------

def test_outstanding_invoices_deduplication():
    import products.zoho_books.outstanding_invoices as mod
    # Same invoice_id in both unpaid and sent — should deduplicate
    records = [
        {"invoice_id": "X1", "status": "unpaid", "total": 5000.0, "balance": 5000.0,
         "customer_name": "A", "date": "2026-04-01", "currency_code": "INR"},
        {"invoice_id": "X1", "status": "sent", "total": 5000.0, "balance": 5000.0,
         "customer_name": "A", "date": "2026-04-01", "currency_code": "INR"},
    ]
    connector = FakeConnector(invoices=records)
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({})
        assert r["success"] is True
        assert r["invoice_count"] == 1
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_outstanding_invoices_deduplication")


def test_draft_invoices_count():
    import products.zoho_books.draft_invoices as mod
    drafts = [{"invoice_id": f"D{i}", "status": "draft", "total": 3000.0,
               "date": "2026-04-05", "currency_code": "INR"} for i in range(3)]
    connector = FakeConnector(invoices=drafts)
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({})
        assert r["success"] is True
        assert r["draft_count"] == 3
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_draft_invoices_count")


def test_payments_received_grouping():
    import products.zoho_books.payments_received as mod
    pmts = [_pmt(1, "cash"), _pmt(2, "cash"), _pmt(3, "bank_transfer")]
    connector = FakeConnector(customer_payments=pmts)
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({"period": "this_month"})
        assert r["success"] is True
        modes = {item["name"] for item in r["by_mode"]}
        assert "cash" in modes
        assert "bank_transfer" in modes
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_payments_received_grouping")


def test_revenue_by_month_returns_monthly():
    import products.zoho_books.revenue_by_month as mod
    invoices = [
        _inv(1, date="2026-01-15", amount=10000.0),
        _inv(2, date="2026-02-10", amount=20000.0),
        _inv(3, date="2026-02-20", amount=15000.0),
    ]
    connector = FakeConnector(invoices=invoices)
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({"period": "this_year"})
        assert r["success"] is True
        months = {m["month"] for m in r["monthly"]}
        assert "2026-01" in months
        assert "2026-02" in months
        feb = next(m for m in r["monthly"] if m["month"] == "2026-02")
        assert feb["amount"] == 35000.0
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_revenue_by_month_returns_monthly")


def test_top_customers_revenue_ranking():
    import products.zoho_books.top_customers_revenue as mod
    invoices = [
        _inv(1, customer="Alpha", amount=50000.0, date="2026-04-05"),
        _inv(2, customer="Beta", amount=20000.0, date="2026-04-06"),
        _inv(3, customer="Alpha", amount=30000.0, date="2026-04-10"),
    ]
    connector = FakeConnector(invoices=invoices)
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({"period": "this_month"})
        assert r["success"] is True
        top = r["top_customers"]
        assert top[0]["name"] == "Alpha"
        assert top[0]["amount"] == 80000.0
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_top_customers_revenue_ranking")


def test_recurring_invoices_active_inactive():
    import products.zoho_books.recurring_invoices as mod
    ri = [
        {"recurring_invoice_id": "R1", "status": "active", "total": 5000.0, "currency_code": "INR",
         "next_invoice_date": "2026-05-01", "recurrence_frequency": "monthly"},
        {"recurring_invoice_id": "R2", "status": "stopped", "total": 3000.0, "currency_code": "INR"},
    ]
    connector = FakeConnector(get_data={"recurringinvoices": {"success": True, "recurring_invoices": ri}})
    orig = _patch(mod, connector)
    try:
        r = mod.run({})
        assert r["success"] is True
        assert r["active_count"] == 1
        assert r["inactive_count"] == 1
    finally:
        _restore(mod, orig)
    print("PASS: test_recurring_invoices_active_inactive")


# ---------------------------------------------------------------------------
# Payables
# ---------------------------------------------------------------------------

def test_ap_aging_buckets_present():
    import products.zoho_books.ap_aging as mod
    bills = [
        _bill(1, status="open", due="2026-04-30"),   # current
        _bill(2, status="overdue", due="2026-03-20"), # overdue
        _bill(3, status="overdue", due="2026-02-01"), # 60+ days
    ]
    connector = FakeConnector(get_data={"bills": {"success": True, "bills": bills}})
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({})
        assert r["success"] is True
        buckets = r["buckets"]
        assert isinstance(buckets, dict)
        assert "as_of_date" in r
        assert "report_basis" in r
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_ap_aging_buckets_present")


def test_outstanding_bills_filters_paid():
    import products.zoho_books.outstanding_bills as mod
    bills = [_bill(1, "open"), _bill(2, "paid"), _bill(3, "overdue")]
    connector = FakeConnector(get_data={"bills": {"success": True, "bills": bills}})
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({})
        assert r["success"] is True
        assert r["bill_count"] == 2
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_outstanding_bills_filters_paid")


def test_overdue_bills_count():
    import products.zoho_books.overdue_bills as mod
    bills = [_bill(i, "overdue", due="2026-03-01") for i in range(1, 4)]
    connector = FakeConnector(get_data={"bills": {"success": True, "bills": bills}})
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({})
        assert r["success"] is True
        assert r["bill_count"] == 3
        assert "average_days_overdue" in r
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_overdue_bills_count")


def test_bills_by_vendor_grouping():
    import products.zoho_books.bills_by_vendor as mod
    bills = [_bill(1, vendor="SupplierA"), _bill(2, vendor="SupplierA"), _bill(3, vendor="SupplierB")]
    connector = FakeConnector(get_data={"bills": {"success": True, "bills": bills}})
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({"period": "this_month"})
        assert r["success"] is True
        vendors = {v["name"] for v in r["top_vendors"]}
        assert "SupplierA" in vendors
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_bills_by_vendor_grouping")


def test_purchase_orders_by_status():
    import products.zoho_books.purchase_orders_summary as mod
    pos = [
        {"po_id": "P1", "status": "open", "total": 15000.0, "currency_code": "INR", "vendor_name": "V1"},
        {"po_id": "P2", "status": "closed", "total": 8000.0, "currency_code": "INR", "vendor_name": "V2"},
    ]
    connector = FakeConnector(purchase_orders=pos)
    orig = _patch(mod, connector)
    try:
        r = mod.run({})
        assert r["success"] is True
        assert "open" in r["by_status"]
        assert r["by_status"]["open"]["count"] == 1
    finally:
        _restore(mod, orig)
    print("PASS: test_purchase_orders_by_status")


def test_vendor_payments_grouping():
    import products.zoho_books.vendor_payments as mod
    vp = [
        {"payment_id": "VP1", "vendor_name": "V1", "date": "2026-04-10", "amount": 5000.0,
         "payment_mode": "bank_transfer", "currency_code": "INR"},
        {"payment_id": "VP2", "vendor_name": "V2", "date": "2026-04-15", "amount": 3000.0,
         "payment_mode": "cash", "currency_code": "INR"},
    ]
    connector = FakeConnector(get_data={"vendorpayments": {"success": True, "vendor_payments": vp}})
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({"period": "this_month"})
        assert r["success"] is True
        assert r["payment_count"] == 2
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_vendor_payments_grouping")


def test_top_vendors_spend_combines_sources():
    import products.zoho_books.top_vendors_spend as mod
    bills = [_bill(1, vendor="SupplierA", amount=10000.0)]
    expenses = [_exp(1, cat="SupplierA", amount=5000.0)]
    connector = FakeConnector(
        expenses=expenses,
        get_data={"bills": {"success": True, "bills": bills}},
    )
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({"period": "this_month"})
        assert r["success"] is True
        assert "top_vendors" in r
        assert "report_basis" in r
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_top_vendors_spend_combines_sources")


# ---------------------------------------------------------------------------
# Financial estimates — accuracy_note and report_basis required
# ---------------------------------------------------------------------------

def _assert_financial_fields(r, expected_basis):
    assert r["success"] is True
    assert "accuracy_note" in r, "Missing accuracy_note"
    assert "report_basis" in r, "Missing report_basis"
    assert expected_basis in r["report_basis"]


def test_profit_loss_has_estimate_fields():
    import products.zoho_books.profit_loss as mod
    connector = FakeConnector(
        invoices=[_inv(1, date="2026-04-10", amount=20000.0)],
        expenses=[_exp(1, date="2026-04-10", amount=8000.0)],
    )
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({"period": "this_month"})
        _assert_financial_fields(r, "invoices_and_expenses")
        net = r["estimated_net_by_currency"]["INR"]
        assert net["income"] == 20000.0
        assert net["expenses"] == 8000.0
        assert net["net"] == 12000.0
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_profit_loss_has_estimate_fields")


def test_balance_sheet_has_estimate_fields():
    import products.zoho_books.balance_sheet as mod
    connector = FakeConnector(
        contacts=[_contact(1, "customer", 20000.0), _contact(2, "vendor", 10000.0)],
        get_data={"bankaccounts": {"success": True, "bank_accounts": [
            {"account_name": "Main", "current_balance": 50000.0, "currency_code": "INR"}
        ]}},
    )
    orig = _patch(mod, connector)
    try:
        r = mod.run({})
        _assert_financial_fields(r, "contacts_bankaccounts_items")
        assert "net_position_by_currency" in r
        pos = r["net_position_by_currency"]["INR"]
        assert pos["cash"] == 50000.0
        assert pos["payables"] == 10000.0
    finally:
        _restore(mod, orig)
    print("PASS: test_balance_sheet_has_estimate_fields")


def test_cash_flow_net_calculation():
    import products.zoho_books.cash_flow as mod
    pmts = [_pmt(1, amount=30000.0)]
    vp = [{"payment_id": "VP1", "vendor_name": "V1", "date": "2026-04-10",
           "amount": 12000.0, "currency_code": "INR"}]
    connector = FakeConnector(
        customer_payments=pmts,
        get_data={"vendorpayments": {"success": True, "vendor_payments": vp}},
    )
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({"period": "this_month"})
        _assert_financial_fields(r, "customer_and_vendor_payments")
        net = r["net_by_currency"]["INR"]
        assert net["inflow"] == 30000.0
        assert net["outflow"] == 12000.0
        assert net["net"] == 18000.0
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_cash_flow_net_calculation")


def test_trial_balance_groups_by_type():
    import products.zoho_books.trial_balance as mod
    accounts = [
        {"account_id": "A1", "account_type": "income", "closing_balance": 50000.0},
        {"account_id": "A2", "account_type": "income", "closing_balance": 30000.0},
        {"account_id": "A3", "account_type": "expense", "closing_balance": 20000.0},
    ]
    connector = FakeConnector(get_data={"chartofaccounts": {"success": True, "chartofaccounts": accounts}})
    orig = _patch(mod, connector)
    try:
        r = mod.run({})
        _assert_financial_fields(r, "chart_of_accounts_list_api")
        assert len(r["by_account_type"]) == 2
        assert r["by_account_type"]["Income"]["balance"] == 80000.0
    finally:
        _restore(mod, orig)
    print("PASS: test_trial_balance_groups_by_type")


def test_financial_overview_working_capital():
    import products.zoho_books.financial_overview as mod
    connector = FakeConnector(
        invoices=[_inv(1, date="2026-04-10", amount=15000.0)],
        expenses=[_exp(1, date="2026-04-10", amount=5000.0)],
        contacts=[_contact(1, "customer", 20000.0), _contact(2, "vendor", 8000.0)],
        get_data={"bankaccounts": {"success": True, "bank_accounts": [
            {"account_name": "Main", "current_balance": 40000.0, "currency_code": "INR"}
        ]}},
    )
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({"period": "this_month"})
        _assert_financial_fields(r, "invoices_expenses_contacts_bankaccounts")
        wc = r["working_capital_by_currency"]["INR"]
        # AR(20000) + cash(40000) - AP(8000) = 52000
        assert wc["value"] == 52000.0
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_financial_overview_working_capital")


# ---------------------------------------------------------------------------
# Sales
# ---------------------------------------------------------------------------

def test_sales_summary_avg_invoice():
    import products.zoho_books.sales_summary as mod
    invoices = [_inv(i, date="2026-04-10", amount=float(i * 10000)) for i in range(1, 5)]
    connector = FakeConnector(invoices=invoices)
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({"period": "this_month"})
        assert r["success"] is True
        s = r["sales_by_currency"]["INR"]
        assert s["invoice_count"] == 4
        expected_avg = (10000 + 20000 + 30000 + 40000) / 4
        assert s["avg_invoice_value"] == expected_avg
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_sales_summary_avg_invoice")


def test_sales_orders_open_count():
    import products.zoho_books.sales_orders_summary as mod
    orders = [
        {"salesorder_id": "S1", "status": "open", "total": 5000.0, "currency_code": "INR"},
        {"salesorder_id": "S2", "status": "closed", "total": 3000.0, "currency_code": "INR"},
        {"salesorder_id": "S3", "status": "confirmed", "total": 7000.0, "currency_code": "INR"},
    ]
    connector = FakeConnector(salesorders=orders)
    orig = _patch(mod, connector)
    try:
        r = mod.run({})
        assert r["success"] is True
        assert r["total_orders"] == 3
        assert r["open_order_count"] == 2
    finally:
        _restore(mod, orig)
    print("PASS: test_sales_orders_open_count")


def test_estimates_conversion_rate():
    import products.zoho_books.estimates_summary as mod
    ests = [
        {"estimate_id": "E1", "status": "sent", "total": 5000.0, "currency_code": "INR"},
        {"estimate_id": "E2", "status": "accepted", "total": 8000.0, "currency_code": "INR"},
        {"estimate_id": "E3", "status": "declined", "total": 4000.0, "currency_code": "INR"},
        {"estimate_id": "E4", "status": "accepted", "total": 6000.0, "currency_code": "INR"},
    ]
    connector = FakeConnector(estimates=ests)
    orig = _patch(mod, connector)
    try:
        r = mod.run({})
        assert r["success"] is True
        # accepted=2, sent=1, declined=1 → rate = 2/4 = 0.5
        assert r["conversion_rate"] == 0.5
    finally:
        _restore(mod, orig)
    print("PASS: test_estimates_conversion_rate")


def test_sales_by_item_no_line_items():
    import products.zoho_books.sales_by_item as mod
    invoices = [_inv(i, date="2026-04-10") for i in range(3)]
    connector = FakeConnector(invoices=invoices)
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({"period": "this_month"})
        assert r["success"] is True
        assert r["line_items_available"] is False
        assert len(r["warnings"]) > 0
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_sales_by_item_no_line_items")


def test_sales_by_item_with_line_items():
    import products.zoho_books.sales_by_item as mod
    invoices = [
        {"invoice_id": "I1", "date": "2026-04-10", "status": "paid", "currency_code": "INR",
         "total": 15000.0, "line_items": [
             {"name": "Widget", "quantity": 3.0, "rate": 3000.0, "item_total": 9000.0},
             {"name": "Gadget", "quantity": 2.0, "rate": 3000.0, "item_total": 6000.0},
         ]},
    ]
    connector = FakeConnector(invoices=invoices)
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({"period": "this_month"})
        assert r["success"] is True
        assert r["line_items_available"] is True
        names = {i["name"] for i in r["top_items"]}
        assert "Widget" in names
        assert r["unique_items"] == 2
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_sales_by_item_with_line_items")


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------

def test_expense_summary_by_category():
    import products.zoho_books.expense_summary as mod
    expenses = [_exp(i, cat=f"Cat{i % 3}", date="2026-04-10", amount=float(i * 2000)) for i in range(1, 7)]
    connector = FakeConnector(expenses=expenses)
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({"period": "this_month"})
        assert r["success"] is True
        assert r["expense_count"] == 6
        assert "by_category" in r
        assert "totals_by_currency" in r
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_expense_summary_by_category")


def test_top_vendors_expense_ranking():
    import products.zoho_books.top_vendors_expense as mod
    expenses = [
        {"expense_id": "E1", "vendor_name": "Alpha", "date": "2026-04-10",
         "amount": 30000.0, "total": 30000.0, "currency_code": "INR"},
        {"expense_id": "E2", "vendor_name": "Beta", "date": "2026-04-10",
         "amount": 10000.0, "total": 10000.0, "currency_code": "INR"},
        {"expense_id": "E3", "vendor_name": "Alpha", "date": "2026-04-12",
         "amount": 20000.0, "total": 20000.0, "currency_code": "INR"},
    ]
    connector = FakeConnector(expenses=expenses)
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({"period": "this_month"})
        assert r["success"] is True
        assert r["top_vendors"][0]["name"] == "Alpha"
        assert r["top_vendors"][0]["amount"] == 50000.0
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_top_vendors_expense_ranking")


# ---------------------------------------------------------------------------
# Banking
# ---------------------------------------------------------------------------

def test_cash_position_accounts():
    import products.zoho_books.cash_position as mod
    accounts = [
        {"account_name": "Savings", "current_balance": 100000.0, "currency_code": "INR",
         "account_type": "bank"},
        {"account_name": "Current", "current_balance": -5000.0, "currency_code": "INR",
         "account_type": "bank"},
    ]
    connector = FakeConnector(get_data={"bankaccounts": {"success": True, "bank_accounts": accounts}})
    orig = _patch(mod, connector)
    try:
        r = mod.run({})
        assert r["success"] is True
        assert r["account_count"] == 2
        assert any(w for w in r["warnings"] if "negative" in w.lower())
    finally:
        _restore(mod, orig)
    print("PASS: test_cash_position_accounts")


def test_bank_accounts_list():
    import products.zoho_books.bank_accounts as mod
    accounts = [
        {"account_id": "BA1", "account_name": "HDFC", "account_type": "bank",
         "current_balance": 50000.0, "currency_code": "INR", "is_active": True},
    ]
    connector = FakeConnector(get_data={"bankaccounts": {"success": True, "bank_accounts": accounts}})
    orig = _patch(mod, connector)
    try:
        r = mod.run({})
        assert r["success"] is True
        assert r["account_count"] == 1
        assert r["accounts"][0]["account_name"] == "HDFC"
    finally:
        _restore(mod, orig)
    print("PASS: test_bank_accounts_list")


# ---------------------------------------------------------------------------
# Tax
# ---------------------------------------------------------------------------

def test_gst_summary_has_estimate_warning():
    import products.zoho_books.gst_summary as mod
    invoices = [{"invoice_id": "I1", "date": "2026-04-10", "tax_amount": 1800.0,
                 "total": 10000.0, "currency_code": "INR"}]
    connector = FakeConnector(invoices=invoices)
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({"period": "this_month"})
        assert r["success"] is True
        assert r["gst_collected"] == 1800.0
        assert "accuracy_note" in r
        assert any("GST" in w for w in r["warnings"])
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_gst_summary_has_estimate_warning")


def test_tax_liability_net_calculation():
    import products.zoho_books.tax_liability as mod
    invoices = [{"invoice_id": "I1", "date": "2026-04-10", "tax_amount": 3600.0,
                 "total": 20000.0, "currency_code": "INR"}]
    expenses = [{"expense_id": "E1", "date": "2026-04-10", "tax_amount": 900.0,
                 "total": 5000.0, "currency_code": "INR"}]
    connector = FakeConnector(invoices=invoices, expenses=expenses)
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({"period": "this_month"})
        assert r["success"] is True
        assert r["tax_collected"] == 3600.0
        assert r["input_tax_credit"] == 900.0
        assert r["net_tax_liability"] == 2700.0
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_tax_liability_net_calculation")


def test_tds_summary_has_accuracy_note():
    import products.zoho_books.tds_summary as mod
    connector = FakeConnector(
        invoices=[{"invoice_id": "I1", "date": "2026-04-10", "tds_amount": 200.0,
                   "total": 10000.0, "currency_code": "INR"}],
        get_data={"vendorpayments": {"success": True, "vendor_payments": []}},
    )
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({"period": "this_month"})
        assert r["success"] is True
        assert "accuracy_note" in r
        assert r["tds_on_sales"] == 200.0
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_tds_summary_has_accuracy_note")


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

def test_inventory_summary_value():
    import products.zoho_books.inventory_summary as mod
    items = [_item(i, rate=1000.0, stock=10.0) for i in range(1, 4)]
    connector = FakeConnector(items=items)
    orig = _patch(mod, connector)
    try:
        r = mod.run({})
        assert r["success"] is True
        assert r["inventory_item_count"] == 3
        # 3 items × rate(1000) × stock(10) = 30000
        assert r["estimated_value_by_currency"]["INR"] == 30000.0
    finally:
        _restore(mod, orig)
    print("PASS: test_inventory_summary_value")


def test_inventory_low_stock_detection():
    import products.zoho_books.inventory_summary as mod
    items = [_item(1, rate=500.0, stock=2.0)]  # stock(2) <= reorder(5)
    connector = FakeConnector(items=items)
    orig = _patch(mod, connector)
    try:
        r = mod.run({})
        assert r["low_stock_count"] == 1
        assert r["low_stock_items"][0]["stock_on_hand"] == 2.0
    finally:
        _restore(mod, orig)
    print("PASS: test_inventory_low_stock_detection")


def test_top_selling_items_no_line_items():
    import products.zoho_books.top_selling_items as mod
    connector = FakeConnector(invoices=[_inv(i, date="2026-04-10") for i in range(3)])
    orig = _patch(mod, connector)
    orig_t = _patch_today(2026, 4, 22)
    try:
        r = mod.run({"period": "this_month"})
        assert r["success"] is True
        assert r["line_items_available"] is False
    finally:
        _restore(mod, orig)
        _restore_today(orig_t)
    print("PASS: test_top_selling_items_no_line_items")


def test_item_price_list_capped_at_50():
    import products.zoho_books.item_price_list as mod
    items = [_item(i, rate=float(i * 100)) for i in range(1, 60)]
    connector = FakeConnector(items=items)
    orig = _patch(mod, connector)
    try:
        r = mod.run({})
        assert r["success"] is True
        assert len(r["items"]) <= 50
    finally:
        _restore(mod, orig)
    print("PASS: test_item_price_list_capped_at_50")


def test_item_price_list_fields():
    import products.zoho_books.item_price_list as mod
    items = [_item(1, rate=2500.0)]
    connector = FakeConnector(items=items)
    orig = _patch(mod, connector)
    try:
        r = mod.run({})
        assert r["success"] is True
        item = r["items"][0]
        assert item["rate"] == 2500.0
        assert "rate_formatted" in item
        assert item["name"] == "Item 1"
    finally:
        _restore(mod, orig)
    print("PASS: test_item_price_list_fields")


# ---------------------------------------------------------------------------
# Auth errors — spot check a few scripts
# ---------------------------------------------------------------------------

def _auth_error_check(module_path, run_params=None):
    import importlib
    mod = importlib.import_module(module_path)
    orig = mod.get_connector

    def _raise():
        raise RuntimeError("Not authenticated. Please authenticate with Zoho Books first.")

    mod.get_connector = _raise
    try:
        r = mod.run(run_params or {})
        assert r["success"] is False
        assert r["error"] == "authentication_required"
    finally:
        mod.get_connector = orig


def test_auth_errors_propagate():
    for mp in [
        "products.zoho_books.vendor_balances",
        "products.zoho_books.profit_loss",
        "products.zoho_books.cash_position",
        "products.zoho_books.inventory_summary",
    ]:
        _auth_error_check(mp)
    print("PASS: test_auth_errors_propagate")


if __name__ == "__main__":
    test_vendor_balances_success()
    test_vendor_balances_empty()
    test_contact_list_counts()
    test_contact_aging_buckets()
    test_outstanding_invoices_deduplication()
    test_draft_invoices_count()
    test_payments_received_grouping()
    test_revenue_by_month_returns_monthly()
    test_top_customers_revenue_ranking()
    test_recurring_invoices_active_inactive()
    test_ap_aging_buckets_present()
    test_outstanding_bills_filters_paid()
    test_overdue_bills_count()
    test_bills_by_vendor_grouping()
    test_purchase_orders_by_status()
    test_vendor_payments_grouping()
    test_top_vendors_spend_combines_sources()
    test_profit_loss_has_estimate_fields()
    test_balance_sheet_has_estimate_fields()
    test_cash_flow_net_calculation()
    test_trial_balance_groups_by_type()
    test_financial_overview_working_capital()
    test_sales_summary_avg_invoice()
    test_sales_orders_open_count()
    test_estimates_conversion_rate()
    test_sales_by_item_no_line_items()
    test_sales_by_item_with_line_items()
    test_expense_summary_by_category()
    test_top_vendors_expense_ranking()
    test_cash_position_accounts()
    test_bank_accounts_list()
    test_gst_summary_has_estimate_warning()
    test_tax_liability_net_calculation()
    test_tds_summary_has_accuracy_note()
    test_inventory_summary_value()
    test_inventory_low_stock_detection()
    test_top_selling_items_no_line_items()
    test_item_price_list_capped_at_50()
    test_item_price_list_fields()
    test_auth_errors_propagate()
    print("\nAll Phase 2B report script tests passed.")
