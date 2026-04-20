"""
ConnectorRegistry — connector loader, instance manager, and catalog.

Active connectors: zoho_books (direct API, India endpoint)
Catalog lists planned/coming-soon connectors for the website connector browser.
"""
import logging
from typing import Type

from connectors.base_connector import BaseConnector

logger = logging.getLogger(__name__)


# Full connector catalog — drives the website connector library browser.
# status: "available" | "coming_soon" | "planned"
CONNECTOR_CATALOG: dict[str, dict] = {
    "zoho_books": {
        "name": "Zoho Books",
        "category": "Accounting & Finance",
        "status": "available",
        "description": "Zoho Books — invoices, estimates, sales orders, purchase orders, expenses, items, taxes, contacts, payments. India endpoint (zoho.in). GST-ready.",
        "plans": ["free", "starter", "professional", "enterprise"],
        "icon": "📚",
    },
    "zoho_crm": {
        "name": "Zoho CRM",
        "category": "CRM",
        "status": "coming_soon",
        "description": "Zoho CRM — leads, contacts, accounts, deals. Coming soon.",
        "plans": ["starter", "professional", "enterprise"],
        "icon": "🏢",
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
    Singleton registry: holds active connector classes, cached instances, and version metadata.
    The CONNECTOR_CATALOG above is separate — it drives the website browser for all planned connectors.
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
                f"Connector '{name}' not registered. Active: {list(self._classes)}"
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
    """Register active connectors. Only zoho_books is active in this build."""
    try:
        from connectors.zoho_books.connector import ZohoBooksConnector
        reg.register("zoho_books", ZohoBooksConnector, version="1.2.0", api_version="v3")
    except ImportError as e:
        logger.warning("Could not load ZohoBooksConnector: %s", e)


# Module-level singleton — import this everywhere
registry = ConnectorRegistry()
_register_defaults(registry)
