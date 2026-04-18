"""
ZohoCRMClient — HTTP client for Zoho CRM API v2.

Not a BaseConnector subclass. Instantiated by ZohoConnector (orchestrator)
which passes a shared request function that handles auth headers and token refresh.
"""
import logging
from config.settings import ZOHO_API_BASE
from connectors.base_connector import ConnectorError

logger = logging.getLogger(__name__)


class ZohoCRMClient:
    """Thin CRM API client. All HTTP goes through the parent connector's request_fn."""

    def __init__(self, request_fn):
        self._request = request_fn  # callable: (url, params) -> dict

    def _url(self, endpoint: str) -> str:
        return f"{ZOHO_API_BASE}/{endpoint}"

    def check_access(self) -> bool:
        """Lightweight availability check — hits users endpoint."""
        logger.info("Checking Zoho CRM access...")
        try:
            self._request(self._url("users"), {"type": "CurrentUser"})
            logger.info("CRM available: True")
            return True
        except Exception:
            logger.info("CRM available: False")
            return False

    def get_leads(self, limit: int = 20, page: int = 1, fields: list = None) -> list:
        params = {"per_page": min(limit, 200), "page": page}
        if fields:
            params["fields"] = ",".join(fields)
        return self._request(self._url("Leads"), params).get("data", [])

    def get_contacts(self, limit: int = 20, page: int = 1, fields: list = None) -> list:
        params = {"per_page": min(limit, 200), "page": page}
        if fields:
            params["fields"] = ",".join(fields)
        return self._request(self._url("Contacts"), params).get("data", [])

    def get_accounts(self, limit: int = 20) -> list:
        return self._request(
            self._url("Accounts"), {"per_page": min(limit, 200)}
        ).get("data", [])

    def get_deals(self, limit: int = 20) -> list:
        return self._request(
            self._url("Deals"), {"per_page": min(limit, 200)}
        ).get("data", [])

    def search_leads(self, criteria: str) -> list:
        return self._request(
            self._url("Leads/search"), {"criteria": criteria}
        ).get("data", [])
