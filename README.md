# ReckLabs AI Agent

**Connect your business applications to Claude Desktop using the Model Context Protocol (MCP).**

ReckLabs AI Agent is a local-first MCP server that bridges the free Claude Desktop app to your business tools — CRM systems, accounting software, lead enrichment platforms, and more. Non-technical users can install it with a single click and immediately start querying their data through natural language in Claude.

---

## Table of Contents

1. [What It Does](#what-it-does)
2. [Architecture Overview](#architecture-overview)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
   - [One-Click (Windows)](#one-click-windows)
   - [Manual Installation](#manual-installation)
5. [Configuration](#configuration)
   - [Zoho CRM Credentials](#zoho-crm-credentials)
   - [Environment Variables](#environment-variables)
6. [Claude Desktop Integration](#claude-desktop-integration)
7. [First-Time Authentication](#first-time-authentication)
8. [Available Tools](#available-tools)
9. [Skills System](#skills-system)
   - [Using Skills](#using-skills)
   - [Writing a Custom Skill](#writing-a-custom-skill)
   - [Skill Parameter Templating](#skill-parameter-templating)
10. [Example Queries for Claude](#example-queries-for-claude)
11. [Project Structure](#project-structure)
12. [Developer Guide](#developer-guide)
    - [Adding a New Connector](#adding-a-new-connector)
    - [Adding New Tools](#adding-new-tools)
    - [Connector Registry](#connector-registry)
13. [Connector Roadmap](#connector-roadmap)
14. [Packaging as a Standalone Executable](#packaging-as-a-standalone-executable)
15. [Security Notes](#security-notes)
16. [Troubleshooting](#troubleshooting)
17. [Logs](#logs)
18. [License](#license)

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
       ├── zoho_tools       ──► Zoho CRM API
       ├── quickbooks_tools ──► QuickBooks API  (coming soon)
       ├── linkedin_tools   ──► Apollo / Lusha  (coming soon)
       └── skill_tools      ──► multi-step workflow engine
```

**Phase 1 capabilities:**

- Fetch and search leads, contacts, and accounts from **Zoho CRM**
- Execute **multi-step workflow skills** (e.g. fetch leads → enrich → summarise)
- Full **OAuth2 authentication** with automatic token refresh
- **One-click Windows installer** that auto-registers with Claude Desktop
- Extensible framework ready for QuickBooks, Tally, LinkedIn, Apollo, Lusha, and email outreach

---

## Architecture Overview

| Layer | Files | Responsibility |
|---|---|---|
| **Entry point** | `main.py` | Boot, wire all layers together |
| **MCP Server** | `agent/mcp_server.py` | JSON-RPC 2.0 stdio transport, tool dispatch |
| **Tool Layer** | `tools/*.py` | Thin adapters — connector calls wrapped as MCP tools |
| **Skill Engine** | `agent/skill_executor.py` | Load + run JSON workflow files |
| **Connector Layer** | `connectors/*.py` | Business logic, API calls, token management |
| **Auth** | `auth/zoho_oauth.py` | OAuth2 browser flow, token exchange and storage |
| **Registry** | `registry/connector_registry.py` | Dynamic connector loader, instance cache |
| **Config** | `config/settings.py`, `config/connectors.json` | Central config, no hardcoded secrets |
| **Storage** | `storage/tokens.json` | Persisted OAuth tokens (local only) |
| **Skills** | `skills/*.json` | Declarative workflow definitions |

**Key design rules:**
- Tools never call external APIs directly — always go through a connector
- Connectors never know about MCP — always called through the tool layer
- All credentials come from `config/connectors.json` or environment variables
- The MCP server is protocol-only — adding connectors requires zero changes to it

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10 or higher | https://python.org |
| Claude Desktop | Latest | https://claude.ai/download — free plan works |
| Zoho CRM account | Any plan | Free developer account available |
| Windows | 10 / 11 | Linux/macOS work too — run `main.py` directly |

---

## Installation

### One-Click (Windows)

1. Download and extract the package to a permanent location, e.g. `C:\ReckLabs\ai-agent\`
2. Double-click `installer\install.bat`
3. The installer will:
   - Verify Python is installed
   - Run `pip install -r requirements.txt`
   - Create the `storage/` directory and `tokens.json`
   - Write the MCP configuration to `%APPDATA%\Claude\claude_desktop_config.json`
4. Add your credentials (see [Configuration](#configuration))
5. Restart Claude Desktop

> If Claude Desktop is not yet installed, the installer will show the config block to add manually.

---

### Manual Installation

**1. Clone or extract the project**

```bash
# Windows
cd C:\ReckLabs
# (extract ai-agent/ here)

# macOS / Linux
cd ~/ReckLabs
```

**2. Install dependencies**

```bash
cd ai-agent
pip install -r requirements.txt
```

**3. Create the storage directory**

```bash
mkdir storage
echo {} > storage/tokens.json
```

**4. Register with Claude Desktop** — see [Claude Desktop Integration](#claude-desktop-integration)

**5. Add credentials** — see [Configuration](#configuration)

---

## Configuration

### Zoho CRM Credentials

Edit `config/connectors.json` and fill in your Zoho app credentials:

```json
{
  "zoho": {
    "client_id": "YOUR_ZOHO_CLIENT_ID",
    "client_secret": "YOUR_ZOHO_CLIENT_SECRET",
    "redirect_uri": "http://localhost:8766/callback"
  }
}
```

#### How to create a Zoho API app

1. Go to [https://api-console.zoho.in](https://api-console.zoho.in)
2. Click **Add Client** → choose **Server-based Applications**
3. Fill in:
   - **Client Name**: ReckLabs AI Agent (or any name)
   - **Homepage URL**: `http://localhost`
   - **Authorized Redirect URIs**: `http://localhost:8766/callback`
4. Click **Create**
5. Copy the **Client ID** and **Client Secret** into `config/connectors.json`

> The redirect URI **must** match exactly what you put in `connectors.json`. The default `http://localhost:8766/callback` works for local use.

---

### Environment Variables

As an alternative to `connectors.json`, you can set credentials via environment variables. This is useful in CI, Docker, or when you don't want credentials in files.

| Variable | Description | Default |
|---|---|---|
| `ZOHO_CLIENT_ID` | Zoho OAuth client ID | — |
| `ZOHO_CLIENT_SECRET` | Zoho OAuth client secret | — |
| `ZOHO_REDIRECT_URI` | OAuth callback URL | `http://localhost:8766/callback` |
| `MCP_HOST` | MCP server bind host | `localhost` |
| `MCP_PORT` | MCP server port | `8765` |

Values in `connectors.json` take precedence over environment variables.

---

## Claude Desktop Integration

Claude Desktop discovers MCP servers through a JSON config file.

**Location on Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**Location on macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Add or merge the following into that file (update the path to match your installation):

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

> Use double backslashes `\\` in Windows paths inside JSON.

An example config file is provided at `installer/claude_desktop_config.example.json`.

After saving the config, **fully restart Claude Desktop** (quit from the system tray, not just close the window). The agent's tools will appear automatically.

---

## First-Time Authentication

The first time you ask Claude to use a Zoho tool:

1. The agent will open your **default browser** to the Zoho authorization page
2. Log in with your Zoho account and click **Accept**
3. Your browser redirects to `localhost:8766` — the agent captures the code automatically
4. Tokens are exchanged and saved to `storage/tokens.json`
5. All subsequent requests use the saved tokens; refresh happens automatically

**Headless / manual flow** (if browser doesn't open):

Ask Claude: *"Give me the Zoho authentication URL"* — then open the URL manually in a browser. After approving, copy the `code` parameter from the redirect URL and ask Claude: *"Exchange this Zoho code: [paste code here]"*

---

## Available Tools

These tools are registered with Claude Desktop and can be called by name or through natural language:

### Zoho CRM Tools

| Tool Name | Description | Key Parameters |
|---|---|---|
| `zoho_authenticate` | Start OAuth2 flow or check auth status | — |
| `zoho_get_auth_url` | Return the OAuth authorization URL | — |
| `zoho_exchange_code` | Exchange OAuth code for tokens | `code` (string) |
| `get_zoho_leads` | Fetch leads from CRM | `limit` (int), `page` (int), `fields` (list) |
| `get_zoho_contacts` | Fetch contacts from CRM | `limit` (int), `page` (int), `fields` (list) |
| `get_zoho_accounts` | Fetch company accounts | `limit` (int) |
| `search_zoho_leads` | Search leads by criteria | `criteria` (string) |

**Search criteria syntax:**
```
Field:operator:value

Examples:
  Email:equals:john@acme.com
  Company:contains:Acme
  Lead_Source:equals:Web
  Annual_Revenue:greater_than:100000
```

### Skill Tools

| Tool Name | Description | Key Parameters |
|---|---|---|
| `list_skills` | List all available workflow skills | — |
| `run_skill` | Execute a skill by name | `name` (string), `context` (object) |
| `reload_skills` | Reload skill files from disk | — |

---

## Skills System

Skills are **declarative JSON workflow files** stored in the `skills/` directory. They let you chain multiple tool calls into a single named operation that Claude can trigger in one request.

### Using Skills

```
"Run the lead_generation skill"
"Execute the contact_enrichment skill"
"List all available skills"
```

### Built-in Skills

**`lead_generation`** — Fetches the latest 20 leads from Zoho CRM.

**`contact_enrichment`** — Fetches 50 contacts with key fields for enrichment workflows.

### Writing a Custom Skill

Create a new `.json` file in the `skills/` directory. The format is:

```json
{
  "name": "my_skill_name",
  "description": "What this skill does — shown in list_skills output",
  "version": "1.0",
  "steps": [
    {
      "step_name": "descriptive_step_name",
      "tool": "tool_name_to_call",
      "params": {
        "param_key": "param_value"
      },
      "on_error": "stop"
    }
  ]
}
```

**Field reference:**

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Unique skill identifier |
| `description` | No | Human-readable description |
| `version` | No | Version string |
| `steps[].step_name` | No | Label for this step (used in output and templating) |
| `steps[].tool` | Yes | Name of the MCP tool to call |
| `steps[].params` | No | Parameters passed to the tool |
| `steps[].on_error` | No | `"stop"` (default) or `"continue"` |

### Skill Parameter Templating

Later steps can reference the output of earlier steps using `{{step_name.field}}` syntax:

```json
{
  "name": "leads_then_search",
  "description": "Fetch leads, then search for a specific one",
  "steps": [
    {
      "step_name": "fetch_batch",
      "tool": "get_zoho_leads",
      "params": { "limit": 10 }
    },
    {
      "step_name": "targeted_search",
      "tool": "search_zoho_leads",
      "params": {
        "criteria": "{{context.search_criteria}}"
      }
    }
  ]
}
```

Context values can be passed when running: `run_skill(name="leads_then_search", context={"search_criteria": "Company:contains:Acme"})`

After adding or editing skill files, ask Claude: *"Reload skills"* — no restart required.

---

## Example Queries for Claude

These are natural language prompts you can type in Claude Desktop after installation:

**Authentication**
```
Authenticate with Zoho
Give me the Zoho OAuth URL
```

**Leads**
```
Fetch my latest 20 Zoho leads
Get 50 leads from Zoho CRM
Show me leads from page 2
Search Zoho leads where company contains Acme
Find leads with email john@example.com
Get Zoho leads and only return First_Name, Email, and Company fields
```

**Contacts**
```
Get my Zoho contacts
Fetch 100 Zoho contacts
Get contacts with fields First_Name, Last_Name, Email, Phone, Lead_Source
```

**Accounts**
```
Show me Zoho accounts
Get the top 50 accounts from Zoho
```

**Skills and Workflows**
```
List all available skills
Run the lead_generation skill
Execute the contact_enrichment skill
Reload skills from disk
```

**Combined (Claude reasons across multiple tool calls)**
```
Fetch my top 50 Zoho leads and tell me which industries appear most
Search for leads from technology companies and summarise their details
Get my Zoho contacts and identify which ones are missing email addresses
```

---

## Project Structure

```
ai-agent/
│
├── main.py                          # Entry point — boots agent, wires all layers
│
├── agent/
│   ├── __init__.py
│   ├── mcp_server.py                # MCP JSON-RPC 2.0 server over stdio
│   └── skill_executor.py            # JSON skill loader and step runner
│
├── connectors/
│   ├── __init__.py
│   ├── base_connector.py            # Abstract base class with retry logic
│   └── zoho_connector.py            # Zoho CRM — OAuth2, leads, contacts, accounts
│
├── tools/
│   ├── __init__.py
│   ├── zoho_tools.py                # MCP tool definitions for Zoho
│   └── skill_tools.py               # MCP tool definitions for skill system
│
├── auth/
│   ├── __init__.py
│   └── zoho_oauth.py                # Browser OAuth flow, token exchange, storage
│
├── registry/
│   ├── __init__.py
│   └── connector_registry.py        # Connector class registry + instance cache
│
├── config/
│   ├── __init__.py
│   ├── settings.py                  # All config constants and loader functions
│   └── connectors.json              # Credentials file (fill this in, never commit)
│
├── skills/
│   ├── lead_generation.json         # Built-in skill: fetch recent leads
│   └── contact_enrichment.json      # Built-in skill: fetch contacts for enrichment
│
├── storage/
│   └── tokens.json                  # OAuth tokens — auto-managed, never commit
│
├── website/
│   └── index.html                   # Static distribution page
│
├── installer/
│   ├── install.bat                  # Windows one-click installer
│   ├── setup_instructions.md        # Full manual setup guide
│   └── claude_desktop_config.example.json
│
└── requirements.txt                 # Python dependencies (requests only)
```

---

## Developer Guide

### Adding a New Connector

Follow this pattern to add any new connector (e.g. QuickBooks):

**1. Create the connector class** in `connectors/quickbooks_connector.py`:

```python
from connectors.base_connector import BaseConnector, ConnectorError

class QuickBooksConnector(BaseConnector):
    name = "quickbooks"

    def __init__(self):
        config = load_connector_config("quickbooks")
        super().__init__(config)

    def authenticate(self) -> dict:
        # implement OAuth or API key flow
        ...

    def execute(self, action: str, params: dict):
        actions = {
            "get_invoices": lambda p: self.get_invoices(**p),
        }
        if action not in actions:
            raise ConnectorError(self.name, f"Unknown action: {action}")
        return actions[action](params)

    def get_invoices(self, limit=20) -> list:
        return self._execute_with_retry(self._api_get, "invoices", {"limit": limit})
```

**2. Register it** in `registry/connector_registry.py` — add two lines inside `_register_defaults()`:

```python
from connectors.quickbooks_connector import QuickBooksConnector
registry.register("quickbooks", QuickBooksConnector)
```

**3. Create tool definitions** in `tools/quickbooks_tools.py`:

```python
from registry.connector_registry import registry

def get_quickbooks_invoices(params: dict) -> dict:
    connector = registry.get("quickbooks")
    return {"success": True, "data": connector.get_invoices(limit=params.get("limit", 20))}

QUICKBOOKS_TOOLS = [
    {
        "name": "get_quickbooks_invoices",
        "description": "Fetch invoices from QuickBooks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 20}
            },
            "required": []
        },
        "fn": get_quickbooks_invoices,
    }
]
```

**4. Import tools in `main.py`** — add one line to the `all_tools` list:

```python
from tools.quickbooks_tools import QUICKBOOKS_TOOLS
all_tools = ZOHO_TOOLS + QUICKBOOKS_TOOLS + SKILL_TOOLS
```

**That's it.** No changes to the MCP server, skill engine, or registry infrastructure.

---

### Adding New Tools

Tools are just Python functions with a specific signature:

```python
def my_tool(params: dict) -> dict:
    """Always return a dict with 'success' bool and 'data' or 'error' key."""
    try:
        result = do_something(params.get("my_param"))
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

Register them by adding to a `*_TOOLS` list and including it in `main.py`.

---

### Connector Registry

The `ConnectorRegistry` is a singleton that manages connector instances:

```python
from registry.connector_registry import registry

# Get a connector instance (created on first access, cached after)
zoho = registry.get("zoho")

# List registered connectors
print(registry.list_connectors())  # ['zoho', ...]

# Health check all connectors
print(registry.health_check_all())
```

---

### BaseConnector Retry Logic

The `_execute_with_retry()` method retries up to 3 times with exponential backoff for server errors (5xx). It will **not** retry:
- `AuthenticationError` — requires user action
- 4xx HTTP errors — client errors (bad request, not found)

```python
# Usage inside a connector method:
def get_leads(self):
    return self._execute_with_retry(self._api_get, "Leads", {"per_page": 20})
```

---

## Connector Roadmap

| Connector | Category | Status |
|---|---|---|
| Zoho CRM | CRM | Available |
| QuickBooks | Accounting | Planned |
| Tally ERP | Accounting | Planned |
| Apollo.io | Lead Enrichment | Planned |
| Lusha | Lead Enrichment | Planned |
| LinkedIn Sales Nav | Prospecting | Planned |
| Email (SMTP/SendGrid) | Outreach | Planned |
| HubSpot | CRM | Planned |
| Salesforce | CRM | Planned |

---

## Packaging as a Standalone Executable

To distribute to users who don't have Python installed:

```bash
pip install pyinstaller
cd ai-agent
pyinstaller --onefile --name recklabs-agent --add-data "skills;skills" --add-data "config;config" main.py
```

The output `dist/recklabs-agent.exe` is a single file that includes Python and all dependencies.

Update `claude_desktop_config.json` to use the executable path:

```json
{
  "mcpServers": {
    "recklabs-ai-agent": {
      "command": "C:\\ReckLabs\\ai-agent\\dist\\recklabs-agent.exe",
      "args": []
    }
  }
}
```

> The `--add-data` flags bundle the `skills/` and `config/` directories into the executable so workflow files and connector config are included.

---

## Security Notes

1. **`config/connectors.json` contains API credentials** — never commit this file to version control. It is listed in `.gitignore` by convention.

2. **`storage/tokens.json` contains OAuth access tokens** — treat it like a password file. It is stored locally only and never transmitted.

3. **Tokens are stored unencrypted** in Phase 1. For production, encrypt this file using the OS keychain (Windows Credential Manager, macOS Keychain) or a secrets manager.

4. **The agent runs only on localhost** — it does not open any network ports and communicates with Claude Desktop exclusively through stdin/stdout. There is no external attack surface.

5. **OAuth scopes are minimal** — the Zoho connector requests only read-only scopes: `ZohoCRM.modules.leads.READ` and `ZohoCRM.modules.contacts.READ`. Expand scopes in `config/settings.py` only if write operations are needed.

6. **Never share your `connectors.json`** or `tokens.json` with anyone, including support staff.

---

## Troubleshooting

### Tools don't appear in Claude Desktop

- Verify the path in `claude_desktop_config.json` is correct and uses double backslashes
- Ensure Python is on your system `PATH` — open a terminal and run `python --version`
- Fully quit Claude Desktop from the system tray (not just close the window) and reopen it
- Check `storage/agent.log` for startup errors

### "Authentication required" error when fetching data

- Confirm `client_id` and `client_secret` are filled in `config/connectors.json`
- Verify the `redirect_uri` in `connectors.json` matches **exactly** what is set in the Zoho API Console
- Delete `storage/tokens.json` contents (replace with `{}`) and re-authenticate
- Check that port `8766` is not blocked by a firewall or already in use

### "Import error" or module not found on startup

- Run `pip install -r requirements.txt` again in the `ai-agent/` directory
- Confirm you are using Python 3.10 or higher: `python --version`
- If you have multiple Python versions, ensure the one in `PATH` matches the one used to install dependencies

### OAuth browser doesn't open

- Run the agent from a terminal manually: `python main.py` and watch for errors
- Use the headless flow: ask Claude for the auth URL, open it manually in a browser, and exchange the code

### Zoho API returns 401 after working previously

- The access token has expired and the refresh also failed
- Delete `storage/tokens.json` (replace with `{}`) and re-run authentication

### Claude doesn't understand my query

- Be explicit: *"Use the get_zoho_leads tool to fetch 20 leads"*
- Check `list_skills` to see what skills are available
- Confirm the agent is connected: ask *"What tools do you have available?"*

---

## Logs

The agent writes logs to `storage/agent.log`. Stdout is reserved for the MCP protocol and must not be written to directly.

To watch logs in real time (Windows PowerShell):
```powershell
Get-Content storage\agent.log -Wait -Tail 50
```

To watch logs in real time (bash/macOS/Linux):
```bash
tail -f storage/agent.log
```

Log level can be changed in `main.py` — change `logging.INFO` to `logging.DEBUG` for verbose output.

---

## License

MIT License — free for personal and commercial use.

---

*Built on the [Model Context Protocol](https://modelcontextprotocol.io) — an open standard for connecting AI models to external tools.*
