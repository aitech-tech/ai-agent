# Zoho Books Report Catalog

This catalog documents all `zb_` pre-processed reporting tools for Zoho Books.
The full catalog is also machine-readable in `products/zoho_books/manifest.json`.

---

## Implemented tools (Phase 2A — 5 tools)

These tools are live and available in the current build.

| Tool name | Category | Description |
|---|---|---|
| `zb_ar_aging` | Receivables | AR aging buckets (current, 0-30, 31-60, 61-90, 90+ days), total outstanding, critical overdue, top 10 invoices |
| `zb_overdue_invoices` | Receivables | All overdue invoices: total, avg days overdue, oldest invoice, top 10 by balance, grouped by customer |
| `zb_invoice_summary` | Invoices | Invoice status breakdown for a period: total value, paid, outstanding, collection rate |
| `zb_expense_by_category` | Expenses | Expenses grouped by account/category for a period: total, top 10 categories, highest category |
| `zb_customer_balances` | Receivables | Outstanding balances per customer: total, top 10 debtors, missing email count |

---

## Planned tools (future phases)

The following tools are in the catalog and ready to be implemented. Each has a stub entry in `manifest.json`. To implement one, create the corresponding script in `products/zoho_books/` and update its `status` to `"implemented"`.

### Receivables & Contacts

| Tool name | Description |
|---|---|
| `zb_vendor_balances` | Outstanding payable balances per vendor |
| `zb_contact_list` | Summarised contact list with type, email, balance |
| `zb_contact_aging` | Combined AR/AP aging per contact |
| `zb_outstanding_invoices` | All open invoices with totals and top customers |

### Invoices & Revenue

| Tool name | Description |
|---|---|
| `zb_payments_received` | Customer payments received in a period |
| `zb_revenue_by_month` | Monthly revenue trend from invoices |
| `zb_top_customers_revenue` | Top customers by invoiced revenue |
| `zb_recurring_invoices` | Recurring invoice profiles and monthly commitment |
| `zb_draft_invoices` | Draft invoices pending dispatch |

### Payables

| Tool name | Description |
|---|---|
| `zb_ap_aging` | AP aging buckets from bills |
| `zb_outstanding_bills` | All open bills with totals and top vendors |
| `zb_overdue_bills` | Overdue bills with avg days overdue |
| `zb_bills_by_vendor` | Bills grouped by vendor |
| `zb_purchase_orders_summary` | PO status breakdown and total committed value |
| `zb_vendor_payments` | Vendor payments made in a period |
| `zb_top_vendors_spend` | Top vendors by total billed spend |

### Financial Statements ⚠️

> **Important**: These reports derive estimates from invoice and expense records.
> They are **not** a substitute for statutory financial statements.
> P&L, Balance Sheet, GST, and TDS reports **must be validated by a qualified
> accountant** before use in any filings or compliance submissions.

| Tool name | Description |
|---|---|
| `zb_profit_loss` | Estimated P&L from invoices and expenses |
| `zb_balance_sheet` | Estimated balance sheet summary |
| `zb_cash_flow` | Estimated cash flow from payments |
| `zb_trial_balance` | Trial balance by account |
| `zb_financial_overview` | One-page financial overview |

### Sales

| Tool name | Description |
|---|---|
| `zb_sales_summary` | Sales summary from invoices |
| `zb_sales_orders_summary` | Sales order status breakdown |
| `zb_estimates_summary` | Estimates by status with conversion rate |
| `zb_sales_by_item` | Revenue grouped by item/service |

### Expenses

| Tool name | Description |
|---|---|
| `zb_expense_summary` | Total expense summary with status breakdown |
| `zb_top_vendors_expense` | Top vendors by expense amount |

### Cash & Banking

| Tool name | Description |
|---|---|
| `zb_cash_position` | Current cash position across bank accounts |
| `zb_bank_accounts` | Bank accounts with current balances |

### Tax ⚠️

> **Important**: Tax reports are estimates only. GST, TDS, and tax liability
> reports **require statutory validation** before use in any filings.

| Tool name | Description |
|---|---|
| `zb_gst_summary` | GST collected and input credit summary |
| `zb_tax_liability` | Estimated tax liability |
| `zb_tds_summary` | TDS deducted and collected summary |

### Inventory

| Tool name | Description |
|---|---|
| `zb_inventory_summary` | Inventory items summary with stock value |
| `zb_top_selling_items` | Top selling items by quantity and revenue |
| `zb_item_price_list` | Item/service price list (cap: 50 items) |

---

## How to implement a planned tool

See [python-preprocessing-scripts.md](python-preprocessing-scripts.md) for the full guide.
In short: create the script, implement `run()`, update `manifest.json`, add tests.
