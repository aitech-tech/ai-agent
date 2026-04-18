"""
Central configuration for ReckLabs AI Agent Platform — Phase 1.
All secrets come from environment variables or config files. Never hardcode credentials here.
"""
import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
STORAGE_DIR = BASE_DIR / "storage"

# Skills: 2-layer system (base = encrypted IP, client = user customisation)
SKILLS_DIR = BASE_DIR / "skills"
SKILLS_BASE_DIR = SKILLS_DIR / "base"
SKILLS_CLIENT_DIR = SKILLS_DIR / "client"

# Storage files
TOKENS_FILE = STORAGE_DIR / "tokens.json"
LICENSE_FILE = STORAGE_DIR / "license.json"
HEALTH_FILE = STORAGE_DIR / "health.json"

# Config files
CONNECTORS_CONFIG_FILE = BASE_DIR / "config" / "connectors.json"
CONNECTOR_VERSIONS_FILE = BASE_DIR / "config" / "connector_versions.json"
CONNECTOR_CATALOG_FILE = BASE_DIR / "config" / "connector_catalog.json"

# MCP server identity
MCP_SERVER_NAME = "recklabs-ai-agent"
MCP_SERVER_VERSION = "1.0.0"
PLATFORM_VERSION = "1.0.0"

# Zoho OAuth2 — override via environment variables or connectors.json
ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID", "")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET", "")
ZOHO_REDIRECT_URI = os.getenv("ZOHO_REDIRECT_URI", "http://localhost:8000/callback")
ZOHO_SCOPES = (
    "ZohoCRM.modules.ALL,"
    "ZohoCRM.users.READ,"
    "ZohoBooks.fullaccess.ALL"
)
ZOHO_AUTH_URL = "https://accounts.zoho.in/oauth/v2/auth"
ZOHO_TOKEN_URL = "https://accounts.zoho.in/oauth/v2/token"
ZOHO_API_BASE = "https://www.zohoapis.in/crm/v2"
ZOHO_BOOKS_API_BASE = "https://www.zohoapis.in/books/v3"


def load_connector_config(connector_name: str) -> dict:
    """Load connector-specific config from connectors.json if present."""
    if CONNECTORS_CONFIG_FILE.exists():
        with open(CONNECTORS_CONFIG_FILE) as f:
            data = json.load(f)
        return data.get(connector_name, {})
    return {}


def ensure_storage():
    """Ensure all runtime directories and default files exist."""
    STORAGE_DIR.mkdir(exist_ok=True)
    SKILLS_BASE_DIR.mkdir(parents=True, exist_ok=True)
    SKILLS_CLIENT_DIR.mkdir(parents=True, exist_ok=True)

    if not TOKENS_FILE.exists():
        TOKENS_FILE.write_text("{}")
    if not LICENSE_FILE.exists():
        LICENSE_FILE.write_text('{"key": null, "activated": false, "tier": "free"}')
    if not HEALTH_FILE.exists():
        HEALTH_FILE.write_text("{}")
