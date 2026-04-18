"""
Zoho CRM connector — wraps zoho_mcp.zoho_auth (github.com/asklokesh/zoho-crm-mcp-server).

Import/wrap pattern per Phase 1 spec:
  - Auth layer: ZohoAuth from zoho-crm-mcp package (OAuth URL generation, code exchange, refresh)
  - HTTP layer: our clean client (no debug prints, compatible with MCP stdio)
  - Token persistence: our storage/tokens.json (ZohoAuth is env-var only)
"""
import os
import logging
from typing import Any

import requests

from connectors.base_connector import BaseConnector, ConnectorError, AuthenticationError
from auth.zoho_oauth import (
    save_tokens, load_tokens, run_browser_oauth_flow
)
from config.settings import ZOHO_API_BASE, load_connector_config

logger = logging.getLogger(__name__)


def _get_zoho_auth(client_id: str, client_secret: str, redirect_uri: str, tokens: dict):
    """
    Instantiate ZohoAuth from zoho-crm-mcp package.
    ZohoAuth reads exclusively from env vars, so we bridge our config/tokens into env vars first.
    """
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
    Zoho CRM connector.
    Auth delegated to zoho_mcp.zoho_auth.ZohoAuth (open-source, curated from GitHub).
    HTTP calls use our clean client to preserve MCP stdio compatibility.
    """

    name = "zoho"
    upstream = "github.com/asklokesh/zoho-crm-mcp-server"

    def __init__(self):
        file_config = load_connector_config("zoho")
        config = {
            "client_id": file_config.get("client_id") or os.getenv("ZOHO_CLIENT_ID", ""),
            "client_secret": file_config.get("client_secret") or os.getenv("ZOHO_CLIENT_SECRET", ""),
            "redirect_uri": file_config.get("redirect_uri") or os.getenv(
                "ZOHO_REDIRECT_URI", "http://localhost:8766/callback"
            ),
        }
        super().__init__(config)
        self._zoho_auth = None

    # ------------------------------------------------------------------
    # Authentication (delegated to zoho_mcp.zoho_auth.ZohoAuth)
    # ------------------------------------------------------------------

    def authenticate(self) -> dict:
        client_id = self.config.get("client_id")
        client_secret = self.config.get("client_secret")

        if not client_id or not client_secret:
            return {
                "status": "config_required",
                "message": (
                    "Zoho client_id and client_secret are not configured. "
                    "Set them in config/connectors.json or via ZOHO_CLIENT_ID / ZOHO_CLIENT_SECRET."
                ),
            }

        tokens = load_tokens("zoho")

        try:
            self._zoho_auth = _get_zoho_auth(
                client_id, client_secret, self.config["redirect_uri"], tokens
            )
        except Exception as e:
            raise AuthenticationError("zoho", f"ZohoAuth init failed: {e}")

        if self._zoho_auth.is_authenticated():
            self._authenticated = True
            return {"status": "ok", "message": "Loaded existing tokens"}

        # No saved tokens — start browser OAuth flow
        try:
            new_tokens = run_browser_oauth_flow(
                client_id, client_secret, self.config["redirect_uri"]
            )
            # Sync new tokens into ZohoAuth env vars
            self._zoho_auth = _get_zoho_auth(
                client_id, client_secret, self.config["redirect_uri"], new_tokens
            )
            self._authenticated = True
            return {"status": "ok", "message": "OAuth flow completed successfully"}
        except Exception as e:
            raise AuthenticationError("zoho", str(e))

    def get_auth_url(self) -> str:
        """Return OAuth URL via zoho_mcp.ZohoAuth."""
        if self._zoho_auth:
            return self._zoho_auth.generate_auth_url()
        client_id = self.config.get("client_id", "YOUR_CLIENT_ID")
        redirect_uri = self.config.get("redirect_uri", "http://localhost:8766/callback")
        from zoho_mcp.zoho_auth import ZohoAuth
        os.environ.setdefault("ZOHO_CLIENT_ID", client_id)
        os.environ.setdefault("ZOHO_CLIENT_SECRET", "placeholder")
        os.environ.setdefault("ZOHO_REDIRECT_URI", redirect_uri)
        return ZohoAuth().generate_auth_url()

    def exchange_code(self, code: str) -> dict:
        """Exchange auth code via zoho_mcp.ZohoAuth, then persist tokens."""
        if not self._zoho_auth:
            raise AuthenticationError("zoho", "Call authenticate() before exchange_code()")
        token_data = self._zoho_auth.exchange_code_for_tokens(code)
        save_tokens("zoho", token_data)
        self._zoho_auth = _get_zoho_auth(
            self.config["client_id"], self.config["client_secret"],
            self.config["redirect_uri"], token_data
        )
        self._authenticated = True
        return {"status": "ok", "message": "Tokens stored successfully"}

    # ------------------------------------------------------------------
    # HTTP client (our own — no debug prints, MCP-safe)
    # ------------------------------------------------------------------

    def _get_headers(self) -> dict:
        """Get auth headers from ZohoAuth; refresh if needed."""
        if not self._zoho_auth:
            raise AuthenticationError("zoho", "Not authenticated. Call authenticate() first.")
        return self._zoho_auth.get_auth_headers()

    def _api_get(self, endpoint: str, params: dict = None) -> dict:
        url = f"{ZOHO_API_BASE}/{endpoint}"
        headers = self._get_headers()
        resp = requests.get(url, headers=headers, params=params or {}, timeout=15)

        if resp.status_code == 401:
            logger.info("Access token expired — refreshing via ZohoAuth")
            new_token = self._zoho_auth.refresh_access_token()
            tokens = load_tokens("zoho")
            tokens["access_token"] = new_token
            save_tokens("zoho", tokens)
            headers = self._get_headers()
            resp = requests.get(url, headers=headers, params=params or {}, timeout=15)

        if not resp.ok:
            raise ConnectorError("zoho", f"API error {resp.status_code}: {resp.text}", resp.status_code)

        return resp.json()

    # ------------------------------------------------------------------
    # CRM operations
    # ------------------------------------------------------------------

    def get_leads(self, limit: int = 20, page: int = 1, fields: list = None) -> list:
        params = {"per_page": min(limit, 200), "page": page}
        if fields:
            params["fields"] = ",".join(fields)
        data = self._execute_with_retry(self._api_get, "Leads", params)
        return data.get("data", [])

    def get_contacts(self, limit: int = 20, page: int = 1, fields: list = None) -> list:
        params = {"per_page": min(limit, 200), "page": page}
        if fields:
            params["fields"] = ",".join(fields)
        data = self._execute_with_retry(self._api_get, "Contacts", params)
        return data.get("data", [])

    def get_accounts(self, limit: int = 20) -> list:
        data = self._execute_with_retry(self._api_get, "Accounts", {"per_page": min(limit, 200)})
        return data.get("data", [])

    def search_leads(self, criteria: str) -> list:
        data = self._execute_with_retry(self._api_get, "Leads/search", {"criteria": criteria})
        return data.get("data", [])

    def get_deals(self, limit: int = 20) -> list:
        """Fetch deals — exposed by zoho_mcp upstream, added here for parity."""
        data = self._execute_with_retry(self._api_get, "Deals", {"per_page": min(limit, 200)})
        return data.get("data", [])

    # ------------------------------------------------------------------
    # BaseConnector.execute dispatcher
    # ------------------------------------------------------------------

    def execute(self, action: str, params: dict) -> Any:
        actions = {
            "get_leads": lambda p: self.get_leads(
                limit=p.get("limit", 20), page=p.get("page", 1), fields=p.get("fields")
            ),
            "get_contacts": lambda p: self.get_contacts(
                limit=p.get("limit", 20), page=p.get("page", 1), fields=p.get("fields")
            ),
            "get_accounts": lambda p: self.get_accounts(limit=p.get("limit", 20)),
            "get_deals": lambda p: self.get_deals(limit=p.get("limit", 20)),
            "search_leads": lambda p: self.search_leads(criteria=p["criteria"]),
            "authenticate": lambda p: self.authenticate(),
            "get_auth_url": lambda p: {"url": self.get_auth_url()},
            "exchange_code": lambda p: self.exchange_code(p["code"]),
        }
        if action not in actions:
            raise ConnectorError("zoho", f"Unknown action: {action}")
        return actions[action](params)

    def health_check(self) -> dict:
        return {
            "connector": self.name,
            "status": "ok",
            "authenticated": self._authenticated,
            "upstream": self.upstream,
        }
