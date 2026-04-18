"""
ZohoBooksClient — HTTP client for Zoho Books API v3.

Not a BaseConnector subclass. Instantiated by ZohoConnector (orchestrator)
which passes a shared request function that handles auth headers and token refresh.

Most Zoho Books endpoints require an organization_id query param.
check_access() fetches the org list and stores the first org_id automatically.
"""
import logging
from config.settings import ZOHO_BOOKS_API_BASE
from connectors.base_connector import ConnectorError

logger = logging.getLogger(__name__)


class ZohoBooksClient:

    def __init__(self, request_fn):
        self._request = request_fn  # callable: (url, params) -> dict
        self._org_id: str = None

    def _url(self, endpoint: str) -> str:
        return f"{ZOHO_BOOKS_API_BASE}/{endpoint}"

    def _org_params(self, extra: dict = None) -> dict:
        params = {"organization_id": self._org_id} if self._org_id else {}
        if extra:
            params.update(extra)
        return params

    def check_access(self) -> bool:
        """
        Lightweight availability check — hits organizations endpoint.
        Also captures the organization_id for subsequent calls.
        """
        logger.info("Checking Zoho Books access...")
        try:
            data = self._request(self._url("organizations"), {})
            orgs = data.get("organizations", [])
            if orgs:
                self._org_id = str(orgs[0].get("organization_id", ""))
                logger.info("Books available: True (org_id: %s)", self._org_id)
            else:
                logger.warning("Books available: True but no organizations returned — Books may not be subscribed")
            return True
        except Exception as exc:
            logger.warning("Books available: False — reason: %s", exc)
            return False

    def get_organizations(self) -> list:
        return self._request(self._url("organizations"), {}).get("organizations", [])

    def get_invoices(self, limit: int = 20, page: int = 1, status: str = None) -> list:
        params = self._org_params({"per_page": min(limit, 200), "page": page})
        if status:
            params["status"] = status
        return self._request(self._url("invoices"), params).get("invoices", [])

    def get_bills(self, limit: int = 20, page: int = 1, status: str = None) -> list:
        params = self._org_params({"per_page": min(limit, 200), "page": page})
        if status:
            params["status"] = status
        return self._request(self._url("bills"), params).get("bills", [])

    def get_customers(self, limit: int = 20, page: int = 1) -> list:
        params = self._org_params({"per_page": min(limit, 200), "page": page,
                                    "contact_type": "customer"})
        return self._request(self._url("contacts"), params).get("contacts", [])

    def get_vendors(self, limit: int = 20, page: int = 1) -> list:
        params = self._org_params({"per_page": min(limit, 200), "page": page,
                                    "contact_type": "vendor"})
        return self._request(self._url("contacts"), params).get("contacts", [])
