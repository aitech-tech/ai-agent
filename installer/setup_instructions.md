# ReckLabs AI Agent - Setup Instructions

## Quick Start (Windows)

1. Open the ReckLabs website.
2. Select the connectors you want. In the current release, Zoho is selectable and the other connector cards are disabled until their tool modules are ready.
3. Click **Generate Config File**. This downloads `recklabs_config.json`.
4. Download the ReckLabs AI Agent zip package.
5. Extract the package to a stable folder, for example `C:\ReckLabs\ai-agent\`.
6. Place `recklabs_config.json` next to `installer\install.bat`.
7. Double-click `installer\install.bat`.
8. Restart Claude Desktop completely.
9. In Claude, ask: `Get platform status.`
10. Then ask: `Authenticate with Zoho.`

If `recklabs_config.json` is missing, the installer defaults to the Zoho connector.

---

## What The Installer Does

The installer:

- Finds Python 3.10 or newer.
- Installs Python dependencies from `requirements.txt`.
- Reads `installer\recklabs_config.json` if present.
- Writes selected connectors to `config\connector_config.json`.
- Creates local runtime files under `storage\`.
- Encrypts base skill files when the encryption script is available.
- Creates Word skill template folders under `skills\client_docs\zoho_books\`.
- Keeps generated client skill JSON under `skills\client\zoho_books\`.
- Optionally activates a ReckLabs license key.
- Writes Claude Desktop MCP configuration.

The selected connector config looks like this:

```json
{
  "selected_connectors": ["zoho"],
  "generated_at": "2026-04-19",
  "version": "1.0.1"
}
```

At runtime, `main.py` reads this file and loads only the tools for selected connectors.

---

## Manual Installation

### Prerequisites

- Python 3.10 or higher: https://python.org
- Claude Desktop for Windows: https://claude.ai/download
- Internet access for dependency installation, Zoho authentication, and live Zoho data fetching

### Step 1: Install dependencies

```bash
cd path\to\ai-agent
pip install -r requirements.txt
```

### Step 2: Select connectors

Create `config\connector_config.json`:

```json
{
  "selected_connectors": ["zoho"],
  "version": "1.0.1"
}
```

### Step 3: Configure Zoho OAuth credentials for local development

Create or edit `.env`:

```text
ZOHO_CLIENT_ID=YOUR_ZOHO_CLIENT_ID
ZOHO_CLIENT_SECRET=YOUR_ZOHO_CLIENT_SECRET
ZOHO_REDIRECT_URI=http://localhost:8000/callback
```

To create a Zoho API app:

1. Go to https://api-console.zoho.in/
2. Create a **Server-based Application**.
3. Set **Authorized Redirect URI** to `http://localhost:8000/callback`.
4. Copy the **Client ID** and **Client Secret** into `.env`.

The redirect URI must match exactly.

### Step 4: Register with Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "recklabs-ai-agent": {
      "command": "python",
      "args": ["C:\\ReckLabs\\ai-agent\\main.py"]
    }
  }
}
```

Replace the path with wherever you extracted the agent.

### Step 5: Restart Claude Desktop

Close and reopen Claude Desktop. If it is running in the system tray, quit it there too.

---

## First-Time Zoho Authentication

When you first ask Claude to use Zoho:

1. Claude calls the ReckLabs Zoho authentication tool.
2. A browser window opens to Zoho's login page.
3. You log in and approve access.
4. Zoho redirects to `http://localhost:8000/callback`.
5. Tokens are saved locally to `storage\tokens.json`.
6. Future requests use the saved local tokens automatically.

Useful prompts:

```text
Authenticate with Zoho.
```

```text
Check Zoho service status.
```

---

## Skill Updates

Base skill updates are handled through MCP platform tools.

| Tool | Purpose |
|---|---|
| `check_skill_updates` | Compares local skill versions with the remote `skill_manifest.json`. |
| `apply_skill_updates` | Downloads and applies newer encrypted base skill files. |

Local installed versions are tracked in:

```text
skills\skill_versions.json
```

Only encrypted base skills in `skills\base\` are updated. Client customizations in `skills\client\` are preserved.

---

## Custom Skills In Word

Users customize client skills by editing Microsoft Word `.docx` templates. The agent imports the Word document, validates the workflow, converts it to skill JSON internally, and saves the generated JSON under:

```text
skills\client\zoho_books\<skill_id>.json
```

Editable templates live here:

```text
skills\client_docs\zoho_books\
```

Useful prompts:

```text
List skill templates.
```

```text
Import this Word skill template: C:\ReckLabs\ai-agent\skills\client_docs\zoho_books\zoho_books_skill_template.docx
```

```text
List client skills.
```

```text
Validate this client skill: C:\ReckLabs\ai-agent\skills\client\zoho_books\overdue_invoice_snapshot.json
```

Claude runs imported skills by their namespaced ID, for example:

```text
Run skill zoho_books.overdue_invoice_snapshot.
```

Useful prompts:

```text
Check skill updates.
```

```text
Apply skill updates.
```

---

## Available Tools In Claude Desktop

Once installed, you can use these commands in Claude:

| Say to Claude | What it does |
|---|---|
| `Get platform status` | Shows selected connectors, skill versions, and license status. |
| `Authenticate with Zoho` | Opens browser OAuth flow. |
| `Check Zoho service status` | Shows whether CRM and Books are available. |
| `Fetch my Zoho leads` | Returns recent Zoho CRM leads. |
| `Get 50 Zoho contacts` | Returns contacts with pagination. |
| `Search Zoho leads for Acme` | Runs lead search. |
| `Show my Zoho Books invoices` | Returns recent Zoho Books invoices. |
| `Run pipeline review` | Executes the CRM pipeline review skill. |
| `Check skill updates` | Checks for new base skill releases. |
| `Apply skill updates` | Downloads newer encrypted base skills. |

---

## Troubleshooting

**Tools not showing in Claude Desktop**

- Fully quit Claude Desktop and reopen it.
- Run `installer\install.bat` again.
- Check `storage\agent.log` for errors.
- Verify the path in `claude_desktop_config.json` is correct.
- Ensure Python is installed and working.

**Wrong connector tools are showing**

- Check `config\connector_config.json`.
- Confirm `selected_connectors` includes only the connectors you want.
- Restart Claude Desktop after changing connector selection.

**Authentication fails**

- Confirm `.env` contains valid Zoho OAuth credentials for local development.
- Verify the Zoho redirect URI is `http://localhost:8000/callback`.
- Make sure no other app is using port `8000`.
- Delete `storage\tokens.json` and authenticate again if the token file is corrupt.

**Skill update check fails**

- Check internet connectivity.
- Confirm `SKILLS_UPDATE_URL` points to a valid `skill_manifest.json`.
- Try again later if GitHub Releases is temporarily unavailable.

**Import errors on startup**

- Run `pip install -r requirements.txt` again.
- Confirm you are using Python 3.10+.
