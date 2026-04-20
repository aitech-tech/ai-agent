# ReckLabs AI Agent

**Connect Zoho Books to Claude Desktop using the Model Context Protocol (MCP).**

ReckLabs AI Agent is a local-first MCP server that bridges the free Claude Desktop app to your Zoho Books accounting data. Non-technical users can install it with a single click and immediately start querying invoices, expenses, customers, and more through natural language.

**Current build: v1.2.0 — Zoho Books only.**

---

## What It Does

```
You (natural language)
       │
       ▼
Claude Desktop
       │  MCP Protocol (JSON-RPC 2.0 over stdio)
       ▼
ReckLabs AI Agent  ◄──── skills/*.json (workflow definitions)
       │
       └── zoho_books_tools (51 tools) ──► Zoho Books API (zohoapis.in/books/v3)
```

- Query and manage **Zoho Books** data: invoices, expenses, contacts, items, taxes, payments, orders
- Execute **multi-step workflow skills** (e.g. invoice review, expense summary, create customer)
- Full **OAuth2 authentication** with automatic token refresh
- **One-click Windows installer** that auto-registers with Claude Desktop
- Indian accounting defaults: **INR, GST 18%, TDS 10%**, `zoho.in` data center

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10 or higher | [python.org](https://python.org) |
| Claude Desktop | Latest | [claude.ai/download](https://claude.ai/download) — free plan works |
| Zoho Books account | Any plan | Free trial available |
| Windows | 10 / 11 | macOS/Linux: run `main.py` directly |

---

## Installation

### One-Click (Windows)

1. Download and extract the package to a permanent location, e.g. `C:\ReckLabs\ai-agent\`
2. Create a Zoho API app at [https://api-console.zoho.in](https://api-console.zoho.in) (see [connector guide](docs/zoho-books-connector.md))
3. Create `.env` in the `ai-agent/` folder:
   ```text
   ZOHO_CLIENT_ID=your_client_id
   ZOHO_CLIENT_SECRET=your_client_secret
   ZOHO_REDIRECT_URI=http://localhost:8000/callback
   ```
4. Double-click `installer\install.bat`
5. Fully restart Claude Desktop
6. In Claude, type: `Authenticate with Zoho`

### Manual (macOS / Linux)

```bash
cd ai-agent
pip install -r requirements.txt
mkdir -p storage && echo '{}' > storage/tokens.json
python main.py
```

Register with Claude Desktop by editing `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "recklabs-ai-agent": {
      "command": "python",
      "args": ["/path/to/ai-agent/main.py"]
    }
  }
}
```

---

## Architecture

| Layer | Files | Responsibility |
|---|---|---|
| Entry point | `main.py` | Boot, wire all layers |
| MCP Server | `agent/mcp_server.py` | JSON-RPC 2.0 stdio transport, tool dispatch |
| Tool Layer | `tools/*.py` | Thin MCP adapters over connector calls |
| Skill Engine | `agent/skill_executor.py` | Load and run JSON workflow files |
| Connector | `connectors/zoho_books/` | Zoho Books direct API calls, token management |
| Auth | `auth/zoho_oauth.py` | OAuth2 browser flow, token exchange and storage |
| Registry | `registry/connector_registry.py` | Connector instance cache |
| Config | `config/settings.py`, `config/connector_config.json` | Central config |
| Storage | `storage/tokens.json` | Persisted OAuth tokens (local only) |

---

## Available Tools (51)

All Zoho Books tools are named `zoho_books_*`. Organization ID is resolved automatically.

**Categories:** authentication (2), organizations (2), contacts/customers/vendors (5), invoices (5), estimates (5), sales orders (5), purchase orders (5), expenses (5), items (5), taxes (5), customer payments (5), users (2).

Full tool list: [docs/zoho-books-connector.md](docs/zoho-books-connector.md#supported-tools-51-total)

---

## Skills (12)

Skills are declarative JSON workflows that chain tool calls. Claude triggers them from natural language.

| Skill | Trigger Example |
|---|---|
| `zoho_books.invoice_review` | "show invoices" / "invoice review" |
| `zoho_books.expense_review` | "show expenses" / "expense review" |
| `zoho_books.customer_review` | "customer review" / "show customers" |
| `zoho_books.vendor_review` | "vendor review" / "show vendors" |
| `zoho_books.tax_review` | "tax review" / "GST rates" |
| `zoho_books.sales_order_review` | "sales orders" |
| `zoho_books.purchase_order_review` | "purchase orders" |
| `zoho_books.estimate_review` | "show estimates" |
| `zoho_books.payment_review` | "payments received" |
| `zoho_books.create_invoice` | "create invoice" / "raise invoice" |
| `zoho_books.create_customer` | "create customer" / "add customer" |
| `zoho_books.create_item_with_gst` | "create item" / "add product" |

Skills are stored in `skills/base/zoho_books/*.json`. Client overrides go in `skills/client/zoho_books/`.

### Writing a Custom Skill

```json
{
  "name": "my_skill_name",
  "description": "What this skill does",
  "version": "1.0",
  "steps": [
    {
      "step_name": "fetch",
      "tool": "zoho_books_list_invoices",
      "params": { "status": "unpaid" },
      "on_error": "stop"
    }
  ]
}
```

Save to `skills/client/zoho_books/my_skill_name.json`, then ask Claude: *"Reload skills"*.

---

## Example Queries

```
Authenticate with Zoho
Show me all unpaid invoices
Create an invoice for Acme Corp for ₹50,000
Show my recent expenses
Add a new customer: Tata Consultancy Services
Create an item called Web Design at ₹25,000 with 18% GST
Review my vendor list
What taxes do I have set up?
Check connection status
List all available skills
```

---

## Platform Tools

| Tool | Description |
|---|---|
| `list_skills` | List all available workflow skills |
| `run_skill` | Execute a skill by name |
| `run_skill_by_intent` | Match a natural language phrase to a skill |
| `reload_skills` | Reload skill files from disk |
| `get_platform_status` | Show platform version, connector, skill versions |
| `check_license` | Show license status |

---

## Configuration

`config/connector_config.json` (written by installer):

```json
{
  "version": "1.2.0",
  "selected_connectors": ["zoho_books"],
  "connectors": {
    "zoho_books": {
      "mode": "direct_api",
      "enabled": true,
      "standards": {
        "country": "IN",
        "currency": "INR",
        "tax_system": "GST",
        "default_gst_rate": 18,
        "default_tds_rate": 10
      }
    }
  }
}
```

### Environment Variables

| Variable | Description |
|---|---|
| `ZOHO_CLIENT_ID` | Zoho OAuth client ID |
| `ZOHO_CLIENT_SECRET` | Zoho OAuth client secret |
| `ZOHO_REDIRECT_URI` | OAuth callback URL (default: `http://localhost:8000/callback`) |

---

## Project Structure

```
ai-agent/
├── main.py                              # Entry point
├── agent/
│   ├── mcp_server.py                    # MCP JSON-RPC 2.0 server
│   └── skill_executor.py                # Skill loader and runner
├── connectors/
│   ├── base_connector.py                # Abstract base class
│   └── zoho_books/
│       ├── connector.py                 # Zoho Books direct API connector
│       └── tools.py                     # 51 MCP tool definitions
├── tools/
│   ├── skill_tools.py                   # Skill system MCP tools
│   ├── health_tools.py                  # Health check tools
│   └── platform_tools.py               # Platform / license tools
├── auth/
│   └── zoho_oauth.py                    # OAuth2 flow and token storage
├── registry/
│   └── connector_registry.py            # Connector registry (zoho_books only)
├── config/
│   ├── settings.py                      # Config constants and loaders
│   └── connector_config.json            # Active connector config (v1.2.0)
├── skills/
│   ├── intent_map.json                  # Natural language → skill ID mapping
│   ├── skill_versions.json              # Installed skill version tracking
│   ├── base/zoho_books/                 # 12 base skill definitions
│   └── client/zoho_books/              # Client overrides (empty by default)
├── storage/
│   └── tokens.json                      # OAuth tokens — local only, never commit
├── tests/
│   ├── test_connector_config.py
│   ├── test_registry.py
│   ├── test_tool_loading.py
│   ├── test_skill_loading.py
│   └── test_skill_failure.py
├── docs/
│   └── zoho-books-connector.md          # Full connector guide
├── installer/
│   └── install.bat                      # Windows one-click installer
├── website/
│   └── index.html                       # Distribution page
└── requirements.txt
```

---

## Security Notes

1. **`.env` contains API credentials** — never commit this file. It is in `.gitignore`.
2. **`storage/tokens.json` contains live OAuth tokens** — treat it like a password file. Local only, never transmitted.
3. **Tokens are stored unencrypted** in v1.2.0. For production, use OS keychain or a secrets manager.
4. **The agent runs locally** — MCP uses stdin/stdout with Claude Desktop. During auth, a temporary localhost server listens on port `8000`.
5. **Never share `.env`, `connector_config.json`, or `tokens.json`** with anyone, including support staff.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Tools not in Claude | Quit Claude from system tray, reopen; check `storage/agent.log` |
| "Authentication required" | Ask Claude: "Authenticate with Zoho" |
| 401 after working | Delete `storage/tokens.json` contents (`{}`), re-authenticate |
| Browser doesn't open | Ask Claude for the auth URL; open manually; exchange code |
| Port 8000 in use | Close conflicting app or change `ZOHO_REDIRECT_URI` and update Zoho API Console |
| Import error on startup | Run `pip install -r requirements.txt` in `ai-agent/` |

Logs: `storage/agent.log`

```powershell
# Windows — watch logs live
Get-Content storage\agent.log -Wait -Tail 50
```

---

## Running Tests

```bash
cd ai-agent
python tests/test_connector_config.py
python tests/test_registry.py
python tests/test_tool_loading.py
python tests/test_skill_loading.py
python tests/test_skill_failure.py
```

---

## Connector Roadmap

| Connector | Status |
|---|---|
| Zoho Books | **Available** (v1.2.0) |
| Zoho CRM | Coming soon |
| QuickBooks | Planned |
| Tally ERP | Planned |

---

## License

MIT License — free for personal and commercial use.

---

*Built on the [Model Context Protocol](https://modelcontextprotocol.io) — an open standard for connecting AI models to external tools.*
