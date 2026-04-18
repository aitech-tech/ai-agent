"""
ZohoConnector — orchestrator for Zoho CRM + Zoho Books.

Responsibilities:
  - Shared OAuth2 authentication (one token set covers both services)
  - Service detection after auth (CRM and/or Books may not be subscribed)
  - Delegates CRM calls to ZohoCRMClient
  - Delegates Books calls to ZohoBooksClient
  - Graceful handling when either service is unavailable

Auth layer: zoho_mcp.zoho_auth.ZohoAuth (open-source, github.com/asklokesh/zoho-crm-mcp-server)
HTTP layer: our own clean client (no debug prints, MCP stdio safe)
"""
import os
import logging
from typing import Any

import requests

from connectors.base_connector import BaseConnector, ConnectorError, AuthenticationError
from connectors.zoho_crm import ZohoCRMClient
from connectors.zoho_books import ZohoBooksClient
from auth.zoho_oauth import save_tokens, load_tokens, run_browser_oauth_flow
from config.settings import load_connector_config

logger = logging.getLogger(__name__)


def _init_zoho_auth(client_id: str, client_secret: str, redirect_uri: str, tokens: dict):
    """Bridge our tokens into ZohoAuth env vars and return a ZohoAuth instance."""
    from zoho_mcp.zoho_auth import ZohoAuth
    os.environ["ZOHO_CLIENT_ID"] = client_id
    os.environ["ZOHO_CLIENT_SECRET"] = client_secret
    os.environ["ZOHO_REDIRECT_URI"] = redirect_uri
    if tokens.get("access_token"):
        os.environ["ZOHO_ACCESS_TOKEN"] = tokens["access_token"]
    if tokens.get("refresh_token"):
        os.environ["ZOHO_REFRESH_TOKEN"] = tokens["refresh_token"]
    return ZohoAuth()


class ZohoConnector(BaseConnector):
    """
    Single entry point for all Zoho services.
    Internally routes to ZohoCRMClient or ZohoBooksClient based on action
    and detected service availability.
    """

    name = "zoho"
    upstream = "github.com/asklokesh/zoho-crm-mcp-server"

    def __init__(self):
        cfg = load_connector_config("zoho")
        config = {
            "client_id": cfg.get("client_id") or os.getenv("ZOHO_CLIENT_ID", ""),
            "client_secret": cfg.get("client_secret") or os.getenv("ZOHO_CLIENT_SECRET", ""),
            "redirect_uri": cfg.get("redirect_uri") or os.getenv(
                "ZOHO_REDIRECT_URI", "http://localhost:8000/callback"
            ),
        }
        super().__init__(config)
        self._zoho_auth = None
        self._crm: ZohoCRMClient = None
        self._books: ZohoBooksClient = None
        self._service_status: dict = {"crm_available": False, "books_available": False}

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self) -> dict:
        client_id = self.config.get("client_id")
        client_secret = self.config.get("client_secret")

        if not client_id or not client_secret:
            return {
                "status": "config_required",
                "message": "Zoho credentials not configured in config/connectors.json.",
            }

        tokens = load_tokens("zoho")

        try:
            self._zoho_auth = _init_zoho_auth(
                client_id, client_secret, self.config["redirect_uri"], tokens
            )
        except Exception as exc:
            raise AuthenticationError("zoho", f"Auth init failed: {exc}")

        if not self._zoho_auth.is_authenticated():
            try:
                new_tokens = run_browser_oauth_flow(
                    client_id, client_secret, self.config["redirect_uri"]
                )
                self._zoho_auth = _init_zoho_auth(
                    client_id, client_secret, self.config["redirect_uri"], new_tokens
                )
            except Exception as exc:
                raise AuthenticationError("zoho", str(exc))

        self._authenticated = True
        self._init_clients()
        self._detect_services()

        return {
            "status": "ok",
            "message": "Authentication successful.",
            "services": self._service_status,
        }

    def get_auth_url(self) -> str:
        if self._zoho_auth:
            return self._zoho_auth.generate_auth_url()
        client_id = self.config.get("client_id", "YOUR_CLIENT_ID")
        os.environ.setdefault("ZOHO_CLIENT_ID", client_id)
        os.environ.setdefault("ZOHO_CLIENT_SECRET", "placeholder")
        os.environ.setdefault("ZOHO_REDIRECT_URI", self.config.get("redirect_uri", "http://localhost:8000/callback"))
        from zoho_mcp.zoho_auth import ZohoAuth
        return ZohoAuth().generate_auth_url()

    def exchange_code(self, code: str) -> dict:
        if not self._zoho_auth:
            raise AuthenticationError("zoho", "Call authenticate() before exchange_code()")
        from auth.zoho_oauth import exchange_code_for_tokens
        token_data = exchange_code_for_tokens(
            code, self.config["client_id"],
            self.config["client_secret"], self.config["redirect_uri"]
        )
        save_tokens("zoho", token_data)
        self._zoho_auth = _init_zoho_auth(
            self.config["client_id"], self.config["client_secret"],
            self.config["redirect_uri"], token_data
        )
        self._authenticated = True
        self._init_clients()
        self._detect_services()
        return {"status": "ok", "message": "Tokens stored.", "services": self._service_status}

    # ------------------------------------------------------------------
    # Shared HTTP client (no debug prints — MCP stdio safe)
    # ------------------------------------------------------------------

    def _make_request(self, url: str, params: dict = None) -> dict:
        """Single HTTP client shared by both CRM and Books clients."""
        if not self._zoho_auth:
            raise AuthenticationError("zoho", "Not authenticated. Call authenticate() first.")

        headers = self._zoho_auth.get_auth_headers()
        resp = requests.get(url, headers=headers, params=params or {}, timeout=15)

        if resp.status_code == 401:
            logger.info("Token expired — refreshing")
            new_token = self._zoho_auth.refresh_access_token()
            tokens = load_tokens("zoho")
            tokens["access_token"] = new_token
            save_tokens("zoho", tokens)
            headers = self._zoho_auth.get_auth_headers()
            resp = requests.get(url, headers=headers, params=params or {}, timeout=15)

        if not resp.ok:
            raise ConnectorError("zoho", f"API {resp.status_code}: {resp.text[:200]}", resp.status_code)

        return resp.json()

    # ------------------------------------------------------------------
    # Service detection
    # ------------------------------------------------------------------

    def _init_clients(self):
        self._crm = ZohoCRMClient(self._make_request)
        self._books = ZohoBooksClient(self._make_request)

    def _detect_services(self):
        self._service_status["crm_available"] = self._crm.check_access()
        self._service_status["books_available"] = self._books.check_access()

    def get_service_status(self) -> dict:
        return self._service_status.copy()

    # ------------------------------------------------------------------
    # CRM operations (guarded)
    # ------------------------------------------------------------------

    def _require_crm(self):
        if not self._service_status.get("crm_available"):
            raise ConnectorError("zoho", "Zoho CRM not available for this account.")
        if not self._crm:
            raise ConnectorError("zoho", "CRM client not initialised. Authenticate first.")

    def get_leads(self, **kw) -> list:
        self._require_crm()
        return self._execute_with_retry(self._crm.get_leads, **kw)

    def get_contacts(self, **kw) -> list:
        self._require_crm()
        return self._execute_with_retry(self._crm.get_contacts, **kw)

    def get_accounts(self, **kw) -> list:
        self._require_crm()
        return self._execute_with_retry(self._crm.get_accounts, **kw)

    def get_deals(self, **kw) -> list:
        self._require_crm()
        return self._execute_with_retry(self._crm.get_deals, **kw)

    def search_leads(self, **kw) -> list:
        self._require_crm()
        return self._execute_with_retry(self._crm.search_leads, **kw)

    # ------------------------------------------------------------------
    # Books operations (guarded)
    # ------------------------------------------------------------------

    def _require_books(self):
        if not self._service_status.get("books_available"):
            raise ConnectorError("zoho", "Zoho Books not available for this account.")
        if not self._books:
            raise ConnectorError("zoho", "Books client not initialised. Authenticate first.")

    def get_organizations(self) -> list:
        self._require_books()
        return self._execute_with_retry(self._books.get_organizations)

    def get_invoices(self, **kw) -> list:
        self._require_books()
        return self._execute_with_retry(self._books.get_invoices, **kw)

    def get_bills(self, **kw) -> list:
        self._require_books()
        return self._execute_with_retry(self._books.get_bills, **kw)

    def get_customers(self, **kw) -> list:
        self._require_books()
        return self._execute_with_retry(self._books.get_customers, **kw)

    def get_vendors(self, **kw) -> list:
        self._require_books()
        return self._execute_with_retry(self._books.get_vendors, **kw)

    # ------------------------------------------------------------------
    # execute() dispatcher
    # ------------------------------------------------------------------

    def execute(self, action: str, params: dict) -> Any:
        actions = {
            # Auth
            "authenticate":     lambda p: self.authenticate(),
            "get_auth_url":     lambda p: {"url": self.get_auth_url()},
            "exchange_code":    lambda p: self.exchange_code(p["code"]),
            "service_status":   lambda p: self.get_service_status(),
            # CRM
            "get_leads":        lambda p: self.get_leads(limit=p.get("limit", 20), page=p.get("page", 1), fields=p.get("fields")),
            "get_contacts":     lambda p: self.get_contacts(limit=p.get("limit", 20), page=p.get("page", 1), fields=p.get("fields")),
            "get_accounts":     lambda p: self.get_accounts(limit=p.get("limit", 20)),
            "get_deals":        lambda p: self.get_deals(limit=p.get("limit", 20)),
            "search_leads":     lambda p: self.search_leads(criteria=p["criteria"]),
            # Books
            "get_organizations": lambda p: self.get_organizations(),
            "get_invoices":     lambda p: self.get_invoices(limit=p.get("limit", 20), page=p.get("page", 1), status=p.get("status")),
            "get_bills":        lambda p: self.get_bills(limit=p.get("limit", 20), page=p.get("page", 1), status=p.get("status")),
            "get_customers":    lambda p: self.get_customers(limit=p.get("limit", 20)),
            "get_vendors":      lambda p: self.get_vendors(limit=p.get("limit", 20)),
        }
        if action not in actions:
            raise ConnectorError("zoho", f"Unknown action: {action}")
        return actions[action](params)

    def health_check(self) -> dict:
        return {
            "connector": self.name,
            "status": "ok" if self._authenticated else "unauthenticated",
            "authenticated": self._authenticated,
            "services": self._service_status,
            "upstream": self.upstream,
        }
