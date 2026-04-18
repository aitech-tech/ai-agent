# ReckLabs AI Agent — Setup Instructions

## Quick Start (Windows)

1. **Download** the package and extract to any folder (e.g. `C:\ReckLabs\ai-agent\`)
2. **Run** `installer\install.bat` — double-click it
3. **Add credentials** to `config\connectors.json`
4. **Restart** Claude Desktop
5. **Test** by asking Claude: *"Fetch my Zoho leads"*

---

## Manual Installation

### Prerequisites
- Python 3.10 or higher — https://python.org
- Claude Desktop for Windows — https://claude.ai/download

### Step 1: Install dependencies
```bash
cd path\to\ai-agent
pip install -r requirements.txt
```

### Step 2: Configure credentials

Edit `config\connectors.json`:
```json
{
  "zoho": {
    "client_id": "YOUR_ZOHO_CLIENT_ID",
    "client_secret": "YOUR_ZOHO_CLIENT_SECRET",
    "redirect_uri": "http://localhost:8766/callback"
  }
}
```

#### How to get Zoho credentials
1. Go to https://api-console.zoho.in/
2. Create a **Server-based Application**
3. Set **Redirect URI** to `http://localhost:8766/callback`
4. Copy the **Client ID** and **Client Secret** into `connectors.json`

### Step 3: Register with Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json`:

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

> Replace the path with wherever you extracted the agent.

### Step 4: Restart Claude Desktop

Close and reopen Claude Desktop. The agent's tools will appear automatically.

---

## First-Time Authentication

When you first ask Claude to fetch Zoho data, it will:
1. Open a browser window to Zoho's login page
2. You log in and approve access
3. Tokens are saved locally to `storage\tokens.json`
4. All future requests use the saved tokens automatically

---

## Packaging as a Standalone Executable (Optional)

To distribute without requiring Python:

```bash
pip install pyinstaller
pyinstaller --onefile --name recklabs-agent main.py
```

The executable will be in `dist\recklabs-agent.exe`. Update the Claude Desktop config to point to this file instead of `python main.py`.

---

## Available Tools in Claude Desktop

Once installed, you can use these commands in Claude:

| Say to Claude | What it does |
|---|---|
| "Authenticate with Zoho" | Opens browser OAuth flow |
| "Fetch my Zoho leads" | Returns latest 20 leads |
| "Get 50 Zoho contacts" | Returns contacts with pagination |
| "Search Zoho leads for Acme" | Runs criteria search |
| "Run the lead_generation skill" | Executes multi-step workflow |
| "List available skills" | Shows all loaded skill files |

---

## Adding New Connectors

1. Create `connectors/yourapp_connector.py` inheriting `BaseConnector`
2. Register it in `registry/connector_registry.py`
3. Add tools in `tools/yourapp_tools.py`
4. Import tools in `main.py`

No changes needed to the MCP server itself.

---

## Troubleshooting

**Tools not showing in Claude Desktop**
- Check `storage\agent.log` for errors
- Verify the path in `claude_desktop_config.json` is correct
- Ensure Python is on your system PATH

**Authentication fails**
- Confirm `client_id` and `client_secret` are set in `config\connectors.json`
- Verify redirect URI matches what's configured in Zoho API Console
- Delete `storage\tokens.json` and re-authenticate

**Import errors on startup**
- Run `pip install -r requirements.txt` again
- Confirm you're using Python 3.10+
