# Zoho CRM and Zoho Books Connector Guide

This guide explains how to use the ReckLabs Zoho connector with Claude Desktop. It is written for business users and support teams, not only developers.

The Zoho connector currently connects Claude Desktop to:

- Zoho CRM: leads, contacts, accounts, and lead search.
- Zoho Books: organizations, invoices, bills, customers, and vendors.

The connector runs locally on the user's computer. Zoho credentials and tokens stay on the user's machine and are not sent to ReckLabs servers.

## Who This Is For

Use this connector if your team wants to ask Claude questions like:

- "Show me my recent Zoho leads."
- "Get my latest Zoho contacts."
- "Search Zoho leads for Acme."
- "Show unpaid invoices from Zoho Books."
- "List my Zoho Books customers."
- "Run a pipeline review."

This connector is best suited for:

- Sales teams using Zoho CRM.
- Account managers reviewing lead and customer records.
- Founders or managers who want quick CRM summaries.
- Finance and operations teams using Zoho Books for invoices, bills, customers, or vendors.
- CA/accounting support teams that need read-only visibility into Zoho Books data.

## Machine Requirements

### Minimum Configuration

| Requirement | Minimum |
|---|---|
| Operating system | Windows 10 or Windows 11 |
| Processor | Dual-core Intel/AMD processor |
| RAM | 4 GB |
| Free storage | 500 MB |
| Internet | Required for Zoho authentication and live data fetching |
| Python | Python 3.10 or newer |
| Claude Desktop | Installed and signed in |
| Browser | Any modern browser, such as Chrome, Edge, or Firefox |

### Recommended Configuration

| Requirement | Recommended |
|---|---|
| Operating system | Windows 11 |
| Processor | Quad-core Intel/AMD processor |
| RAM | 8 GB or more |
| Free storage | 1 GB or more |
| Internet | Stable broadband connection |
| Python | Python 3.11 or newer |
| Claude Desktop | Latest version |

### Zoho Account Requirements

You need:

- An active Zoho account.
- Access to Zoho CRM, Zoho Books, or both.
- Permission to approve OAuth access.
- Access to the modules you want Claude to read.

If the user only has Zoho CRM access, Zoho Books tools will report that Books is unavailable. If the user only has Zoho Books access, CRM tools will report that CRM is unavailable.

## What The Connector Can Do

### Authentication And Status

| Action | What It Does |
|---|---|
| Authenticate with Zoho | Opens the browser so the user can log in to Zoho and approve access. |
| Check Zoho service status | Shows whether Zoho CRM and/or Zoho Books are available for the logged-in account. |
| Get OAuth URL | Provides the Zoho authorization URL for a manual or headless setup. |
| Exchange OAuth code | Exchanges a Zoho OAuth code for local tokens. Mostly for support or advanced setup. |

### Zoho CRM Actions

| Action | What It Does |
|---|---|
| Get leads | Fetches leads from Zoho CRM. Supports limit, page, and selected fields. |
| Get contacts | Fetches contacts from Zoho CRM. Supports limit, page, and selected fields. |
| Get accounts | Fetches company accounts from Zoho CRM. Supports limit. |
| Search leads | Searches Zoho CRM leads using a criteria string. |
| Pipeline review skill | Fetches leads, contacts, and accounts, then summarizes totals for Claude to analyze. |
| Lead generation skill | Fetches recent leads and returns structured lead data and basic stats. |
| Contact enrichment skill | Fetches contacts and returns structured contact data and basic enrichment stats. |

### Zoho Books Actions

| Action | What It Does |
|---|---|
| Get organizations | Lists Zoho Books organizations connected to the account. |
| Get invoices | Fetches invoices. Supports limit, page, and status filter. |
| Get bills | Fetches bills/payables. Supports limit, page, and status filter. |
| Get customers | Fetches Zoho Books customers. Supports limit and page. |
| Get vendors | Fetches Zoho Books vendors. Supports limit and page. |

## What The Connector Cannot Do Yet

The current connector is focused on reading and reviewing data.

It does not yet:

- Create new leads.
- Update existing leads, contacts, accounts, invoices, bills, customers, or vendors.
- Delete records.
- Send emails.
- Create invoices or bills.
- Record payments.
- Upload documents or attachments.
- Sync data in the background.
- Run scheduled automations.
- Handle multi-user role-based permissions inside the connector.
- Replace Zoho's own approval workflows or audit logs.

For now, treat Claude as a smart assistant for viewing, searching, summarizing, and analyzing Zoho data.

## Installation Guide For Non-Technical Users

### Step 1: Install Claude Desktop

Install Claude Desktop on the Windows computer where the user wants to run the connector.

After installing, open Claude Desktop once and sign in.

### Step 2: Download The ReckLabs AI Agent

Download the ReckLabs AI Agent package and extract it to a permanent folder, for example:

```text
C:\ReckLabs\ai-agent
```

Do not keep it inside Downloads if your organization regularly clears the Downloads folder.

### Step 3: Generate The Connector Config

On the ReckLabs website, select the connectors you want and click **Generate Config File**.

This downloads:

```text
recklabs_config.json
```

For the current release, Zoho is selectable. Other connector cards may be visible but disabled until their connector tools are ready.

Place `recklabs_config.json` next to:

```text
installer\install.bat
```

When the installer runs, it reads this file and writes the active connector selection to:

```text
config\connector_config.json
```

The runtime then loads only tools for selected connectors. If the config file is missing, the installer defaults to Zoho.

### Step 4: Run The Installer

Open the extracted folder, then double-click:

```text
installer\install.bat
```

The installer will:

- Check whether Python is installed.
- Install required Python packages.
- Create the local storage folder.
- Register the ReckLabs AI Agent with Claude Desktop.
- Prepare the local skill files.
- Ask for a license key if one is available.

### Step 5: Restart Claude Desktop

Close Claude Desktop fully, then open it again.

If Claude Desktop is running in the system tray, quit it from there too before reopening.

### Step 6: Test The Agent

In Claude Desktop, ask:

```text
Get platform status.
```

If the setup is correct, Claude should see the ReckLabs tools.

### Step 7: Authenticate With Zoho

Ask Claude:

```text
Authenticate with Zoho.
```

Your browser will open. Log in to Zoho and approve the requested access.

After approval, Zoho redirects back to the local ReckLabs agent. Tokens are saved locally in:

```text
storage\tokens.json
```

### Step 8: Check Available Zoho Services

Ask Claude:

```text
Check Zoho service status.
```

Claude will tell you whether Zoho CRM and Zoho Books are available for your account.

### Step 9: Start Asking Business Questions

Try simple questions first:

```text
Show me my latest 20 Zoho leads.
```

```text
Get my Zoho contacts.
```

```text
Show my latest Zoho Books invoices.
```

```text
List my Zoho Books customers.
```

Once those work, try workflow skills:

```text
Run pipeline review.
```

```text
Analyze my recent leads.
```

## Skill Updates

The connector includes periodically updated ReckLabs base skill files. These base skills contain platform-maintained workflows and defaults. Client customizations remain readable and editable in `skills\client\`.

Ask Claude:

```text
Check skill updates.
```

Claude will compare local skill versions in:

```text
skills\skill_versions.json
```

against the latest remote `skill_manifest.json`.

To apply available updates, ask:

```text
Apply skill updates.
```

Only encrypted base skill files in `skills\base\` are replaced. Your client customization files are not touched.

---
## Example Prompts

### Zoho CRM

```text
Show me my latest 20 leads from Zoho CRM.
```

```text
Get 50 Zoho contacts.
```

```text
Show Zoho accounts.
```

```text
Search Zoho leads where Company contains Acme.
```

```text
Run a pipeline review and summarize the number of leads, contacts, and accounts.
```

```text
Analyze recent leads and tell me which records are missing important fields.
```

### Zoho Books

```text
Show my Zoho Books organizations.
```

```text
Show latest 20 invoices from Zoho Books.
```

```text
Show overdue invoices from Zoho Books.
```

```text
Show paid invoices from Zoho Books.
```

```text
Show my latest Zoho Books bills.
```

```text
List Zoho Books customers.
```

```text
List Zoho Books vendors.
```

## Status Filters For Invoices And Bills

The invoice tool supports status filters such as:

- `draft`
- `sent`
- `overdue`
- `paid`
- `void`
- `unpaid`
- `partially_paid`
- `viewed`

Example:

```text
Show overdue invoices from Zoho Books.
```

For bills, use the status values supported by your Zoho Books account. If a status is not accepted, Zoho will return an API error and Claude will show the error message.

## Dos

- Do authenticate through the browser when Claude asks.
- Do start with small limits, such as 20 or 50 records.
- Do check service status after authentication.
- Do use clear prompts: "show invoices", "get contacts", "search leads".
- Do verify important results inside Zoho before making business decisions.
- Do keep Claude Desktop updated.
- Do keep Python installed and available on the machine.
- Do use stable internet when fetching live Zoho data.
- Do ask Claude to summarize, group, compare, or find missing fields after data is fetched.

## Don'ts

- Do not share `storage\tokens.json` with anyone.
- Do not send your Zoho client secret in chat messages.
- Do not move or delete the `ai-agent` folder after installation unless you update Claude Desktop configuration.
- Do not expect Claude to create, edit, or delete Zoho records with the current connector.
- Do not use this as the final source for compliance, accounting, tax, or legal decisions without checking Zoho directly.
- Do not fetch thousands of records in one prompt unless necessary.
- Do not close the browser during first-time authentication.
- Do not approve OAuth access from an unknown or untrusted computer.

## Data And Security Notes

- The connector runs on the user's local Windows machine.
- Zoho data is fetched directly from Zoho APIs to the local machine.
- ReckLabs servers are not required for daily Zoho data fetching.
- OAuth tokens are stored locally in `storage\tokens.json`.
- The connector uses Zoho OAuth, not the user's Zoho password.
- The current connector requests broad Zoho scopes for CRM modules, users, and Zoho Books access.
- Anyone with access to the user's Windows profile and local token file may be able to use the connected Zoho session, so the machine should be protected with a strong login password.

## Limitations

### Product Limitations

- The connector is currently read-focused.
- It does not yet perform create/update/delete actions.
- It does not yet support background sync.
- It does not yet include a visual setup wizard.
- It does not yet include a UI for choosing which Zoho modules to enable.
- It does not yet include role-based user permissions inside the connector.
- It does not yet include audit trails for every tool call.

### Zoho Account Limitations

- The user must have permission in Zoho for the requested data.
- Zoho CRM and Zoho Books access depends on the user's Zoho subscription and organization setup.
- Zoho Books calls require at least one Books organization.
- Zoho API limits may apply depending on the Zoho plan.
- Some fields may not appear if the Zoho account does not expose them through the API.

### Technical Limitations

- The local callback server uses `http://localhost:8000/callback` by default.
- Authentication can fail if another app is already using port `8000`.
- Internet is required for live Zoho API calls.
- If dependencies are missing, the installer or support team must run `pip install -r requirements.txt`.
- If the Zoho OAuth package is not installed correctly, authentication tools will not work.

## Troubleshooting

### Claude Does Not Show ReckLabs Tools

Try these steps:

1. Fully close Claude Desktop.
2. Run `installer\install.bat` again.
3. Reopen Claude Desktop.
4. Ask: `Get platform status.`

If it still fails, ask support to check:

```text
storage\agent.log
```

### Browser Does Not Open During Authentication

Ask Claude:

```text
Get Zoho auth URL.
```

Open the URL manually in a browser.

### Authentication Times Out

Possible causes:

- Browser was closed before approval.
- Another program is using port `8000`.
- Zoho redirect URI does not match the app configuration.
- Internet connection dropped.

Try authenticating again after closing other local web apps.

### Zoho CRM Is Not Available

Possible causes:

- The Zoho account does not have CRM access.
- The user lacks permission for CRM modules.
- OAuth access did not include CRM scopes.
- Zoho returned an API error.

Ask Claude:

```text
Check Zoho service status.
```

### Zoho Books Is Not Available

Possible causes:

- The Zoho account does not have Zoho Books access.
- There is no Zoho Books organization.
- The user lacks permission for Books data.
- OAuth access did not include Books access.

Ask Claude:

```text
Check Zoho service status.
```

### Results Are Empty

Possible causes:

- There are no records in that Zoho module.
- The user does not have permission to view records.
- The filter is too narrow.
- The selected Zoho organization/account is not the one expected.

Try a broader request:

```text
Show my latest 20 Zoho leads.
```

or:

```text
Show my latest 20 Zoho Books invoices.
```

## Support Checklist

Before escalating a support issue, collect:

- Windows version.
- Python version.
- Claude Desktop version.
- Whether Zoho CRM, Zoho Books, or both are used.
- Whether browser OAuth completed successfully.
- The exact prompt used in Claude.
- The exact error shown by Claude.
- Recent lines from `storage\agent.log`.

Do not send token files, passwords, client secrets, or full `.env` files in support tickets.

## Current Tool Reference

| Tool Name | User-Friendly Meaning |
|---|---|
| `zoho_authenticate` | Connect Zoho through browser login. |
| `zoho_service_status` | Check whether CRM and Books are available. |
| `zoho_get_auth_url` | Get manual Zoho login URL. |
| `zoho_exchange_code` | Exchange OAuth code for local tokens. |
| `get_zoho_leads` | Fetch Zoho CRM leads. |
| `get_zoho_contacts` | Fetch Zoho CRM contacts. |
| `get_zoho_accounts` | Fetch Zoho CRM accounts. |
| `search_zoho_leads` | Search Zoho CRM leads by criteria. |
| `get_zoho_invoices` | Fetch Zoho Books invoices. |
| `get_zoho_bills` | Fetch Zoho Books bills. |
| `get_zoho_organizations` | List Zoho Books organizations. |
| `get_zoho_customers` | Fetch Zoho Books customers. |
| `get_zoho_vendors` | Fetch Zoho Books vendors. |
| `check_skill_updates` | Check for newer ReckLabs encrypted base skill files. |
| `apply_skill_updates` | Download and apply newer encrypted base skill files. |