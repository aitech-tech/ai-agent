"""
ConnectorRegistry — dynamic connector loader, instance manager, and catalog.

Phase 1 architecture:
  - Registry holds implemented connector classes + pinned version metadata
  - CONNECTOR_CATALOG lists all planned connectors (available, coming_soon, planned)
  - This catalog drives the website connector library browser
"""
import json
import logging
from pathlib import Path
from typing import Type

from connectors.base_connector import BaseConnector

logger = logging.getLogger(__name__)


# Full connector catalog per PDF Phase 1 specification.
# status: "available" | "coming_soon" | "planned"
CONNECTOR_CATALOG: dict[str, dict] = {
    # CRM
    "zoho_crm": {
        "name": "Zoho CRM",
        "category": "CRM",
        "status": "available",
        "description": "Full Zoho CRM integration — leads, contacts, accounts, search.",
        "plans": ["free", "starter", "professional", "enterprise"],
        "icon": "🏢",
    },
    "zoho_books": {
        "name": "Zoho Books",
        "category": "Accounting & Finance",
        "status": "available",
        "description": "Zoho Books — invoices, bills, customers, vendors, organizations. Shared OAuth with Zoho CRM.",
        "plans": ["free", "starter", "professional", "enterprise"],
        "icon": "📚",
    },
    "hubspot": {
        "name": "HubSpot",
        "category": "CRM",
        "status": "coming_soon",
        "description": "HubSpot CRM — contacts, deals, pipelines.",
        "plans": ["starter", "professional", "enterprise"],
        "icon": "🟠",
    },
    "salesforce": {
        "name": "Salesforce",
        "category": "CRM",
        "status": "coming_soon",
        "description": "Salesforce CRM — leads, opportunities, accounts.",
        "plans": ["professional", "enterprise"],
        "icon": "☁️",
    },
    # Accounting & Finance
    "quickbooks": {
        "name": "QuickBooks",
        "category": "Accounting & Finance",
        "status": "coming_soon",
        "description": "QuickBooks Online — invoices, expenses, reports.",
        "plans": ["starter", "professional", "enterprise"],
        "icon": "📊",
    },
    "tally": {
        "name": "Tally",
        "category": "Accounting & Finance",
        "status": "planned",
        "description": "Tally ERP 9 / Tally Prime — Indian accounting, GST, invoices.",
        "plans": ["starter", "professional", "enterprise"],
        "icon": "📒",
    },
    # Lead Generation
    "apollo": {
        "name": "Apollo.io",
        "category": "Lead Generation",
        "status": "coming_soon",
        "description": "Apollo.io — prospect search, lead enrichment, email sequences.",
        "plans": ["professional", "enterprise"],
        "icon": "🎯",
    },
    "lusha": {
        "name": "Lusha",
        "category": "Lead Generation",
        "status": "planned",
        "description": "Lusha — B2B contact data enrichment.",
        "plans": ["professional", "enterprise"],
        "icon": "🔍",
    },
    "hunter": {
        "name": "Hunter.io",
        "category": "Lead Generation",
        "status": "planned",
        "description": "Hunter.io — email finder and verifier.",
        "plans": ["starter", "professional", "enterprise"],
        "icon": "🏹",
    },
    # Communication
    "gmail": {
        "name": "Gmail",
        "category": "Communication",
        "status": "coming_soon",
        "description": "Gmail — read, compose, and send emails via AI.",
        "plans": ["starter", "professional", "enterprise"],
        "icon": "📧",
    },
    "outlook": {
        "name": "Outlook",
        "category": "Communication",
        "status": "planned",
        "description": "Microsoft Outlook — emails, calendar, contacts.",
        "plans": ["professional", "enterprise"],
        "icon": "📨",
    },
    "slack": {
        "name": "Slack",
        "category": "Communication",
        "status": "planned",
        "description": "Slack — send messages, read channels, manage notifications.",
        "plans": ["professional", "enterprise"],
        "icon": "💬",
    },
    # Productivity
    "google_drive": {
        "name": "Google Drive",
        "category": "Productivity",
        "status": "coming_soon",
        "description": "Google Drive — read, create, and organize files and folders.",
        "plans": ["starter", "professional", "enterprise"],
        "icon": "📁",
    },
    "notion": {
        "name": "Notion",
        "category": "Productivity",
        "status": "planned",
        "description": "Notion — databases, pages, and workspaces.",
        "plans": ["professional", "enterprise"],
        "icon": "📝",
    },
}


class ConnectorRegistry:
    """
    Singleton registry: holds connector classes, cached instances, and version metadata.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._classes: dict[str, Type[BaseConnector]] = {}
            cls._instance._instances: dict[str, BaseConnector] = {}
            cls._instance._versions: dict[str, dict] = {}
        return cls._instance

    def register(
        self,
        name: str,
        connector_cls: Type[BaseConnector],
        version: str = "1.0.0",
        api_version: str = "v1",
    ) -> None:
        if not issubclass(connector_cls, BaseConnector):
            raise TypeError(f"{connector_cls} must subclass BaseConnector")
        self._classes[name] = connector_cls
        self._versions[name] = {
            "connector_version": version,
            "api_version": api_version,
            "status": "stable",
        }
        logger.info("Registered connector: %s v%s", name, version)

    def get(self, name: str) -> BaseConnector:
        if name not in self._classes:
            raise KeyError(
                f"Connector '{name}' not registered. Available: {list(self._classes)}"
            )
        if name not in self._instances:
            self._instances[name] = self._classes[name]()
        return self._instances[name]

    def list_connectors(self) -> list[str]:
        return list(self._classes.keys())

    def get_version(self, name: str) -> dict:
        return self._versions.get(name, {})

    def get_catalog(self) -> dict:
        """Return full connector catalog (available + coming soon + planned)."""
        return CONNECTOR_CATALOG

    def health_check_all(self) -> dict:
        results = {}
        for name in self._classes:
            try:
                results[name] = self.get(name).health_check()
            except Exception as e:
                results[name] = {"connector": name, "status": "error", "error": str(e)}
        return results


def _register_defaults(reg: ConnectorRegistry) -> None:
    """
    Register all connectors (active + coming-soon stubs).
    Active connectors wrap open-source MCP packages curated from GitHub.
    Stubs are pre-registered so the catalog and health dashboard show them correctly.
    """
    # --- Active connectors ---
    try:
        from connectors.zoho_connector import ZohoConnector
        reg.register("zoho", ZohoConnector, version="1.0.0", api_version="v2")
    except ImportError as e:
        logger.warning("Could not load ZohoConnector: %s", e)

    # --- Coming-soon stubs (curated from GitHub, activate by uncommenting package in requirements.txt) ---
    try:
        from connectors.hubspot_connector import HubSpotConnector
        reg.register("hubspot", HubSpotConnector, version="0.0.0", api_version="v3")
    except ImportError as e:
        logger.warning("Could not load HubSpotConnector: %s", e)

    try:
        from connectors.salesforce_connector import SalesforceConnector
        reg.register("salesforce", SalesforceConnector, version="0.0.0", api_version="v58")
    except ImportError as e:
        logger.warning("Could not load SalesforceConnector: %s", e)

    try:
        from connectors.gmail_connector import GmailConnector
        reg.register("gmail", GmailConnector, version="0.0.0", api_version="v1")
    except ImportError as e:
        logger.warning("Could not load GmailConnector: %s", e)

    try:
        from connectors.google_drive_connector import GoogleDriveConnector
        reg.register("google_drive", GoogleDriveConnector, version="0.0.0", api_version="v3")
    except ImportError as e:
        logger.warning("Could not load GoogleDriveConnector: %s", e)

    try:
        from connectors.slack_connector import SlackConnector
        reg.register("slack", SlackConnector, version="0.0.0", api_version="v2")
    except ImportError as e:
        logger.warning("Could not load SlackConnector: %s", e)

    try:
        from connectors.notion_connector import NotionConnector
        reg.register("notion", NotionConnector, version="0.0.0", api_version="v1")
    except ImportError as e:
        logger.warning("Could not load NotionConnector: %s", e)

    try:
        from connectors.apollo_connector import ApolloConnector
        reg.register("apollo", ApolloConnector, version="0.0.0", api_version="v1")
    except ImportError as e:
        logger.warning("Could not load ApolloConnector: %s", e)


# Module-level singleton — import this everywhere
registry = ConnectorRegistry()
_register_defaults(registry)
