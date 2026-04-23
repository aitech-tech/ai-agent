"""
Central configuration for ReckLabs AI Agent — Zoho Books build.
All secrets come from the .env file or environment variables. Never hardcode credentials here.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env", override=False)
STORAGE_DIR = BASE_DIR / "storage"

# Skills: 2-layer system (base = encrypted IP, client = user customisation)
SKILLS_DIR = BASE_DIR / "skills"
SKILLS_BASE_DIR = SKILLS_DIR / "base"
SKILLS_CLIENT_DIR = SKILLS_DIR / "client"
SKILLS_CLIENT_DOCS_DIR = SKILLS_DIR / "client_docs"

# Storage files
TOKENS_FILE = STORAGE_DIR / "tokens.json"
LICENSE_FILE = STORAGE_DIR / "license.json"
HEALTH_FILE = STORAGE_DIR / "health.json"

# Config files
CONNECTOR_CONFIG_FILE = BASE_DIR / "config" / "connector_config.json"

# MCP server identity
MCP_SERVER_NAME = "recklabs-ai-agent"
MCP_SERVER_VERSION = "1.2.0"
PLATFORM_VERSION = "1.2.0"

# Zoho OAuth2 — India endpoints
ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID", "")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET", "")
ZOHO_REDIRECT_URI = os.getenv("ZOHO_REDIRECT_URI", "http://localhost:8000/callback")
ZOHO_SCOPES = "ZohoBooks.fullaccess.ALL"
ZOHO_AUTH_URL = "https://accounts.zoho.in/oauth/v2/auth"
ZOHO_TOKEN_URL = "https://accounts.zoho.in/oauth/v2/token"
ZOHO_BOOKS_API_BASE = "https://www.zohoapis.in/books/v3"

# Skill update manifest URL
SKILLS_UPDATE_URL = os.getenv(
    "SKILLS_UPDATE_URL",
    "https://github.com/aitech-tech/ai-agent/releases/latest/download/skill_manifest.json"
)

RECKLABS_LICENSE_API_URL = os.getenv("RECKLABS_LICENSE_API_URL", "")

# Tool exposure mode: "customer" (default) or "developer"
# customer: exposes router tools + auth/org + safe lookup + CUD raw tools
# developer: exposes all 91 tools (51 raw + 40 report scripts)
RECKLABS_TOOL_MODE = os.getenv("RECKLABS_TOOL_MODE", "customer").lower().strip()

# Debug escape hatch: set to "true" to expose all raw tools in customer mode
RECKLABS_CUSTOMER_EXPOSE_RAW = os.getenv("RECKLABS_CUSTOMER_EXPOSE_RAW", "false").lower() == "true"

# Raw tool names exposed in customer mode:
#   Auth/org (4) + safe lookup tools (12) + CUD per entity (27) = 43 total
CUSTOMER_MODE_RAW_TOOL_NAMES: frozenset = frozenset({
    # Auth & Org
    "zoho_books_authenticate",
    "zoho_books_connection_status",
    "zoho_books_list_organizations",
    "zoho_books_get_organization",
    # Safe lookup tools (needed to prepare write workflows without guessing IDs)
    "zoho_books_list_contacts",
    "zoho_books_get_contact",
    "zoho_books_list_items",
    "zoho_books_get_item",
    "zoho_books_list_taxes",
    "zoho_books_get_tax",
    "zoho_books_get_invoice",
    "zoho_books_get_estimate",
    "zoho_books_get_sales_order",
    "zoho_books_get_purchase_order",
    "zoho_books_get_expense",
    "zoho_books_get_customer_payment",
    # Contacts CUD
    "zoho_books_create_contact",
    "zoho_books_update_contact",
    "zoho_books_delete_contact",
    # Invoices
    "zoho_books_create_invoice",
    "zoho_books_update_invoice",
    "zoho_books_delete_invoice",
    # Estimates
    "zoho_books_create_estimate",
    "zoho_books_update_estimate",
    "zoho_books_delete_estimate",
    # Sales Orders
    "zoho_books_create_sales_order",
    "zoho_books_update_sales_order",
    "zoho_books_delete_sales_order",
    # Purchase Orders
    "zoho_books_create_purchase_order",
    "zoho_books_update_purchase_order",
    "zoho_books_delete_purchase_order",
    # Expenses
    "zoho_books_create_expense",
    "zoho_books_update_expense",
    "zoho_books_delete_expense",
    # Items
    "zoho_books_create_item",
    "zoho_books_update_item",
    "zoho_books_delete_item",
    # Taxes
    "zoho_books_create_tax",
    "zoho_books_update_tax",
    "zoho_books_delete_tax",
    # Customer Payments
    "zoho_books_create_customer_payment",
    "zoho_books_update_customer_payment",
    "zoho_books_delete_customer_payment",
})


def filter_connector_tools(tools: list, mode: str = RECKLABS_TOOL_MODE) -> list:
    """Return tools filtered by mode.
    developer: all tools unchanged.
    customer: only CUSTOMER_MODE_RAW_TOOL_NAMES (safe lookup + auth/org + CUD; no heavy list/report tools).
             If RECKLABS_CUSTOMER_EXPOSE_RAW=true, all raw tools are exposed (debug only).
    """
    if mode != "customer":
        return tools
    if RECKLABS_CUSTOMER_EXPOSE_RAW:
        return tools
    return [t for t in tools if t["name"] in CUSTOMER_MODE_RAW_TOOL_NAMES]


def load_connector_config_v2() -> dict:
    """Load v1.2.0 connector config."""
    if CONNECTOR_CONFIG_FILE.exists():
        try:
            return json.loads(CONNECTOR_CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def load_selected_connectors() -> list[str]:
    """Return selected connectors. Migrates legacy 'zoho' → 'zoho_books'."""
    cfg = load_connector_config_v2()
    selected = cfg.get("selected_connectors", [])
    if not isinstance(selected, list) or not selected:
        return ["zoho_books"]
    migrated = []
    for name in selected:
        if name == "zoho":
            import logging
            logging.getLogger(__name__).warning(
                "Legacy 'zoho' connector name detected — migrating to 'zoho_books'."
            )
            if "zoho_books" not in migrated:
                migrated.append("zoho_books")
        elif name == "zoho_crm":
            import logging
            logging.getLogger(__name__).warning(
                "zoho_crm is not active in this build — skipping."
            )
        else:
            migrated.append(name)
    return list(dict.fromkeys(migrated)) or ["zoho_books"]


def get_connector_config(connector_id: str) -> dict:
    """Get config for a specific connector."""
    cfg = load_connector_config_v2()
    return cfg.get("connectors", {}).get(connector_id, {})


def ensure_storage():
    """Ensure all runtime directories and default files exist."""
    STORAGE_DIR.mkdir(exist_ok=True)
    (SKILLS_BASE_DIR / "zoho_books").mkdir(parents=True, exist_ok=True)
    (SKILLS_CLIENT_DIR / "zoho_books").mkdir(parents=True, exist_ok=True)
    (SKILLS_CLIENT_DOCS_DIR / "zoho_books").mkdir(parents=True, exist_ok=True)

    if not TOKENS_FILE.exists():
        TOKENS_FILE.write_text("{}")
    if not LICENSE_FILE.exists():
        LICENSE_FILE.write_text('{"key": null, "activated": false, "tier": "free"}')
    if not HEALTH_FILE.exists():
        HEALTH_FILE.write_text("{}")
