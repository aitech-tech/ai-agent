# Zoho Books Connector

**Version:** 1.2.0 - Direct API mode only. No Zoho MCP, no Zoho CRM.

---

## Purpose

The Zoho Books connector lets you query and manage your Zoho Books accounting data directly from Claude Desktop — invoices, expenses, customers, vendors, items, taxes, sales orders, purchase orders, estimates, and payments — using plain language.

No spreadsheets. No logging into Zoho. Just ask Claude.

---

## Machine Requirements

| Requirement | Minimum | Notes |
|---|---|---|
| Operating System | Windows 10 / 11 | macOS and Linux work — run `main.py` directly |
| Python | 3.10 or higher | [python.org](https://python.org) |
| Claude Desktop | Latest | Free plan works — [claude.ai/download](https://claude.ai/download) |
| Zoho Books account | Any plan | Free trial available |
| Internet | Required | For Zoho API calls and initial OAuth authentication |
| RAM | 256 MB | Agent is lightweight |
| Disk | 50 MB | Agent files + Python deps |

---

## Setup Guide (Non-Technical Users)

### Step 1 — Create a Zoho API App

You need a Zoho "API app" to let the agent talk to your Zoho Books account.

1. Open your browser and go to [https://api-console.zoho.in](https://api-console.zoho.in)
2. Click **Add Client** and choose **Server-based Applications**
3. Fill in:
   - **Client Name**: `ReckLabs AI Agent` (or anything you like)
   - **Homepage URL**: `http://localhost`
   - **Authorized Redirect URIs**: `http://localhost:8000/callback`
4. Click **Create**
5. Copy the **Client ID** and **Client Secret** — you will need these in the next step

> If you are outside India, use [https://api-console.zoho.com](https://api-console.zoho.com) instead.

---

### Step 2 — Set Credentials

In the `ai-agent/` folder, create a file called `.env` (if it does not exist) and add:

```text
ZOHO_CLIENT_ID=paste_your_client_id_here
ZOHO_CLIENT_SECRET=paste_your_client_secret_here
ZOHO_REDIRECT_URI=http://localhost:8000/callback
```

Save and close the file.

---

### Step 3 — Run the Installer

Double-click `installer\install.bat`. It will:
- Verify Python is installed
- Install dependencies (`pip install -r requirements.txt`)
- Write the connector config (`config\connector_config.json`)
- Register the agent with Claude Desktop

---

### Step 4 — Restart Claude Desktop

Fully quit Claude Desktop from the system tray (not just close the window), then reopen it.

---

### Step 5 — Customize Skills In Word

Client custom skills are edited in Microsoft Word, not by hand-editing JSON. Open a `.docx` template from:

```text
skills\client_docs\zoho_books\
```

After editing the template, ask Claude to import it. The agent converts the Word document into validated skill JSON internally and saves it to:

```text
skills\client\zoho_books\<skill_id>.json
```

The skill then loads as:

```text
zoho_books.<skill_id>
```

Useful tools in Claude:

| Tool | Purpose |
|---|---|
| `list_skill_templates` | Shows available Word `.docx` skill templates |
| `import_skill_from_word` | Converts a Word template into validated client JSON |
| `list_client_skills` | Shows generated client skill JSON files |
| `validate_client_skill` | Validates a generated client skill JSON file |

---

### Step 6 — Authenticate

In Claude, type:

```
Authenticate with Zoho
```

A browser window will open to the Zoho login page. Log in and click **Accept**. Your browser will redirect to `localhost:8000` — the agent captures the code automatically. Done.

You only need to authenticate once. The agent stores and refreshes tokens automatically.

---

## How Authentication Works

1. Agent starts a temporary local server on port `8000`
2. Zoho's authorization page opens in your browser
3. You log in and approve the permissions
4. Zoho sends a code to `localhost:8000/callback`
5. Agent exchanges the code for access + refresh tokens
6. Tokens are saved to `storage/tokens.json` (local only, never transmitted)
7. Future requests use the saved tokens; the agent auto-refreshes them before expiry

**Headless flow** (if browser does not open):
Ask Claude: *"Give me the Zoho OAuth URL"* — open it manually, approve, then copy the `code` parameter from the redirect URL and ask Claude: *"Exchange this Zoho code: [paste code]"*

---

## Supported Tools (51 total)

All tools are named `zoho_books_*`. Organization ID is resolved automatically if omitted.

### Authentication
| Tool | Description |
|---|---|
| `zoho_books_authenticate` | Start OAuth2 flow or check authentication status |
| `zoho_books_connection_status` | Show connection status, auth state, and organization |

### Organizations (2)
| Tool | Description |
|---|---|
| `zoho_books_list_organizations` | List all Zoho Books organizations on this account |
| `zoho_books_get_organization` | Get details of a specific organization |

### Contacts — Customers and Vendors (5)
| Tool | Description | Required Params |
|---|---|---|
| `zoho_books_list_contacts` | List contacts (filter: customer/vendor) | — |
| `zoho_books_get_contact` | Get a contact by ID | `contact_id` |
| `zoho_books_create_contact` | Create a customer or vendor | `contact_name`, `contact_type` |
| `zoho_books_update_contact` | Update a contact | `contact_id` |
| `zoho_books_delete_contact` | Delete a contact | `contact_id` |

### Invoices (5)
| Tool | Description | Required Params |
|---|---|---|
| `zoho_books_list_invoices` | List invoices (filter by status, date range, customer) | — |
| `zoho_books_get_invoice` | Get a specific invoice | `invoice_id` |
| `zoho_books_create_invoice` | Create an invoice with line items | `customer_id`, `line_items` |
| `zoho_books_update_invoice` | Update an invoice | `invoice_id` |
| `zoho_books_delete_invoice` | Delete a draft invoice | `invoice_id` |

### Estimates (5)
| Tool | Description | Required Params |
|---|---|---|
| `zoho_books_list_estimates` | List estimates | — |
| `zoho_books_get_estimate` | Get a specific estimate | `estimate_id` |
| `zoho_books_create_estimate` | Create an estimate | `customer_id`, `line_items` |
| `zoho_books_update_estimate` | Update an estimate | `estimate_id` |
| `zoho_books_delete_estimate` | Delete an estimate | `estimate_id` |

### Sales Orders (5)
| Tool | Description | Required Params |
|---|---|---|
| `zoho_books_list_sales_orders` | List sales orders | — |
| `zoho_books_get_sales_order` | Get a sales order | `salesorder_id` |
| `zoho_books_create_sales_order` | Create a sales order | `customer_id`, `line_items` |
| `zoho_books_update_sales_order` | Update a sales order | `salesorder_id` |
| `zoho_books_delete_sales_order` | Delete a sales order | `salesorder_id` |

### Purchase Orders (5)
| Tool | Description | Required Params |
|---|---|---|
| `zoho_books_list_purchase_orders` | List purchase orders | — |
| `zoho_books_get_purchase_order` | Get a purchase order | `purchaseorder_id` |
| `zoho_books_create_purchase_order` | Create a purchase order | `vendor_id`, `line_items` |
| `zoho_books_update_purchase_order` | Update a purchase order | `purchaseorder_id` |
| `zoho_books_delete_purchase_order` | Delete a purchase order | `purchaseorder_id` |

### Expenses (5)
| Tool | Description | Required Params |
|---|---|---|
| `zoho_books_list_expenses` | List expenses | — |
| `zoho_books_get_expense` | Get a specific expense | `expense_id` |
| `zoho_books_create_expense` | Record an expense | `account_id`, `amount` |
| `zoho_books_update_expense` | Update an expense | `expense_id` |
| `zoho_books_delete_expense` | Delete an expense | `expense_id` |

### Items / Products (5)
| Tool | Description | Required Params |
|---|---|---|
| `zoho_books_list_items` | List items/products | — |
| `zoho_books_get_item` | Get an item | `item_id` |
| `zoho_books_create_item` | Create an item with GST details | `name`, `rate` |
| `zoho_books_update_item` | Update an item | `item_id` |
| `zoho_books_delete_item` | Delete an item | `item_id` |

### Taxes (5)
| Tool | Description | Required Params |
|---|---|---|
| `zoho_books_list_taxes` | List all tax rates | — |
| `zoho_books_get_tax` | Get a specific tax | `tax_id` |
| `zoho_books_create_tax` | Create a tax rate | `tax_name`, `tax_percentage` |
| `zoho_books_update_tax` | Update a tax rate | `tax_id` |
| `zoho_books_delete_tax` | Delete a tax rate | `tax_id` |

### Customer Payments (5)
| Tool | Description | Required Params |
|---|---|---|
| `zoho_books_list_customer_payments` | List payments received | — |
| `zoho_books_get_customer_payment` | Get a payment | `payment_id` |
| `zoho_books_create_customer_payment` | Record a payment received | `customer_id`, `amount`, `payment_mode` |
| `zoho_books_update_customer_payment` | Update a payment | `payment_id` |
| `zoho_books_delete_customer_payment` | Delete a payment | `payment_id` |

### Users (2)
| Tool | Description |
|---|---|
| `zoho_books_list_users` | List users on the organization |
| `zoho_books_get_user` | Get a specific user |

---

## Supported Skills (12)

Skills are multi-step workflows that chain tool calls. Claude triggers them automatically based on your request.

| Skill ID | Trigger Phrases | What It Does |
|---|---|---|
| `zoho_books.invoice_review` | "show invoices", "invoice review", "unpaid invoices" | Fetches invoices and groups by status |
| `zoho_books.expense_review` | "show expenses", "expense review", "recent expenses" | Fetches expenses and groups by category |
| `zoho_books.customer_review` | "show customers", "customer review", "customer list" | Lists customers and flags incomplete records |
| `zoho_books.vendor_review` | "show vendors", "vendor review", "vendor list" | Lists vendors and flags incomplete records |
| `zoho_books.tax_review` | "tax review", "show taxes", "GST rates" | Lists all tax rates and highlights GST rates |
| `zoho_books.sales_order_review` | "sales orders", "sales order review" | Fetches sales orders and groups by status |
| `zoho_books.purchase_order_review` | "purchase orders", "purchase order review" | Fetches purchase orders and groups by status |
| `zoho_books.estimate_review` | "show estimates", "estimate review" | Fetches estimates and groups by status |
| `zoho_books.payment_review` | "payments received", "payment review" | Fetches payments and summarises totals |
| `zoho_books.create_invoice` | "create invoice", "raise invoice", "new invoice" | Creates an invoice with INR defaults |
| `zoho_books.create_customer` | "create customer", "add customer", "new customer" | Creates a customer contact |
| `zoho_books.create_item_with_gst` | "create item", "add product", "new item" | Creates a product/service with GST |

---

## Example Prompts

```
Show me all unpaid invoices
Create an invoice for Acme Corp for ₹50,000
Show my recent expenses
Add a new customer: Tata Consultancy Services
Create an item called Web Design Services at ₹25,000 with 18% GST
Show my purchase orders
What taxes do I have set up?
Show me all customers missing a GSTIN
Review my vendor list
What are my payments received this month?
```

---

## Indian Defaults

This connector is configured for Indian accounting out of the box:

| Setting | Default Value | Notes |
|---|---|---|
| Currency | INR | Indian Rupees |
| Country | IN | India |
| Tax system | GST | Goods and Services Tax |
| Default GST rate | 18% | Most services and goods |
| Default TDS rate | 10% | TDS on services |
| GST treatment | `business_gst` | Registered business default |
| API endpoint | `zohoapis.in` | India data center |

> **Warning:** These are default values for demonstration purposes. Always verify tax rates, GST applicability, and TDS percentages with your accountant before raising actual invoices. Tax regulations change. The agent does not provide tax or accounting advice.

---

## Limitations

- **Write operations are permanent.** Deleted invoices, expenses, or contacts cannot be recovered from Claude. Use Zoho Books' own UI for sensitive deletions.
- **No bulk operations.** Tools process one record at a time. For large data imports, use Zoho Books' CSV import feature directly.
- **Rate limits apply.** Zoho Books API has per-day and per-minute rate limits. Heavy use may result in temporary throttling.
- **No email sending.** The agent cannot send invoices by email on your behalf — only create/update records.
- **Organization ID is auto-detected.** If you have multiple Zoho Books organizations, the agent defaults to the first one. Pass `organization_id` explicitly to target a specific org.
- **Zoho CRM is not connected.** This build is Zoho Books only.

---

## Dos and Don'ts

**Do:**
- Authenticate before running any data tools
- Ask Claude to "list skills" to see what's available
- Use "connection status" to verify the agent is connected before a session
- Keep `.env` private — never share it or commit it to git

**Don't:**
- Delete records through Claude unless you are certain — deletions are permanent
- Share `storage/tokens.json` — it contains live API tokens
- Use this agent for bulk data migration or large imports
- Assume tax calculations are accountant-verified — always cross-check

---

## Troubleshooting

| Problem | Fix |
|---|---|
| "Authentication required" | Ask Claude: "Authenticate with Zoho" |
| "Unauthenticated" on connection status | Same as above — run OAuth flow |
| Browser doesn't open for auth | Use headless flow — ask Claude for the Zoho OAuth URL |
| 401 after working previously | Delete `storage/tokens.json` contents (replace with `{}`), re-authenticate |
| Tools not visible in Claude | Fully quit Claude from system tray and reopen; check `storage/agent.log` |
| Port 8000 already in use | Close the conflicting app, or set `ZOHO_REDIRECT_URI` to another port and update it in Zoho API Console |
| "Organization not found" | Ask Claude: "List my Zoho organizations" and pass the ID explicitly |

---

## Support

For help, open an issue at the project repository or contact the ReckLabs team. Include the contents of `storage/agent.log` (remove any access tokens before sharing).
