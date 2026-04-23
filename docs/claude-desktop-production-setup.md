# Claude Desktop — Production Setup Guide

This guide explains how to connect ReckLabs AI Agent to Claude Desktop for end-customer deployments.

## Prerequisites

- Python 3.11+ installed and on PATH
- ReckLabs AI Agent extracted (e.g. `C:\ReckLabs\ai-agent\`)
- Claude Desktop installed (Windows or macOS)
- A Zoho Books account (India region, zoho.in)

---

## 1. Configure the .env File

Copy `.env.example` to `.env` and fill in your values:

```
ZOHO_CLIENT_ID=your_zoho_client_id_here
ZOHO_CLIENT_SECRET=your_zoho_client_secret_here
ZOHO_REDIRECT_URI=http://localhost:8000/callback

# customer = router tools only (recommended for end users)
# developer = all 91 tools exposed (for testing / building)
RECKLABS_TOOL_MODE=customer
```

**Important**: Keep `RECKLABS_TOOL_MODE=customer` for end-user deployments. This limits Claude Desktop to about 49 tools (router + auth + write + platform tools) instead of 91+ direct Zoho/report tools, making the interface cleaner and preventing accidental raw data dumps.

---

## 2. Configure Claude Desktop

Open (or create) `claude_desktop_config.json`:

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

Add the following entry under `"mcpServers"`:

```json
{
  "mcpServers": {
    "recklabs-ai-agent": {
      "command": "python",
      "args": ["C:\\ReckLabs\\ai-agent\\main.py"],
      "env": {}
    }
  }
}
```

Adjust the path to match where you extracted the agent. On Windows use double backslashes or forward slashes.

**Alternative — use `pythonw` to suppress the console window**:
```json
"command": "pythonw"
```

---

## 3. Restart Claude Desktop

After saving the config, restart Claude Desktop. You should see the ReckLabs tools appear in the tools panel.

---

## 4. Authenticate with Zoho Books

In Claude Desktop, type:

> Connect to Zoho Books

Claude will call `zoho_books_authenticate`, which opens a browser for OAuth login. After approving access, tokens are saved locally to `storage/tokens.json`.

---

## 5. Verify the Connection

Ask Claude:

> What is my AR aging?

or

> Show me outstanding invoices

Claude will call `recklabs_zoho_assistant`, which routes to the right report and returns a formatted result.

---

## Tool Modes

| Mode | Tools exposed to Claude | Use case |
|------|------------------------|----------|
| `customer` | about 49 unique tools (3 router + 31 selected raw + skill/health/platform tools) | End-user deployment |
| `developer` | 91 (51 raw + 40 report scripts) + skill/health/platform | Building, testing, debugging |

Switch modes by editing `RECKLABS_TOOL_MODE` in `.env` and restarting Claude Desktop.

---

## Customer Mode Tool Summary

**Router tools** (call these for reporting):
- `recklabs_zoho_assistant` — NL query → runs the right report
- `recklabs_zoho_report` — run a specific report by name
- `recklabs_zoho_capabilities` — discover available reports

**Auth & Org tools**:
- `zoho_books_authenticate`, `zoho_books_connection_status`
- `zoho_books_list_organizations`, `zoho_books_get_organization`

**Write tools** (create/update/delete):
- Contacts, Invoices, Estimates, Sales Orders, Purchase Orders
- Expenses, Items, Taxes, Customer Payments

---

## Troubleshooting

**Claude says it can't find the tools**
- Check that `main.py` path in `claude_desktop_config.json` is correct.
- Verify Python is on PATH: `python --version` in a terminal.
- Check `storage/agent.log` for startup errors.

**Authentication fails**
- Ensure `ZOHO_CLIENT_ID` and `ZOHO_CLIENT_SECRET` are set in `.env`.
- The redirect URI must match what's registered in the Zoho API Console.
- Delete `storage/tokens.json` and re-authenticate if tokens are corrupted.

**"Not authenticated" error after restart**
- Tokens are stored in `storage/tokens.json`. If the file is missing or expired, call `zoho_books_authenticate` again.

**Wrong organization data**
- Use `zoho_books_list_organizations` to find your organization ID.
- Pass `organization_id` explicitly to tools if you have multiple organizations.
