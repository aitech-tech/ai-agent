"""
ZohoBooksConnector — clean direct API connector for Zoho Books.

Makes direct HTTPS calls to Zoho Books API v3 (India endpoint).
Loads OAuth tokens from storage/tokens.json; refreshes automatically on 401.

Indian accounting defaults (demo values — verify before real use):
  GST:           18%
  TDS:           10%
  Currency:      INR
  Region/domain: India (zoho.in)
  GST treatment: business_gst

IMPORTANT: These are demo/default values. Confirm all tax and accounting
figures with a qualified accountant before use in actual filings.
"""
import logging
from typing import Optional

import requests

from connectors.base_connector import BaseConnector, ConnectorError, AuthenticationError
from config.settings import (
    ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REDIRECT_URI,
    ZOHO_BOOKS_API_BASE,
)
from auth.zoho_oauth import (
    load_tokens, save_tokens, run_browser_oauth_flow, refresh_access_token,
)

logger = logging.getLogger(__name__)

# Indian accounting defaults — demo values, must be verified for real use
DEFAULT_GST_RATE = 18
DEFAULT_TDS_RATE = 10
DEFAULT_CURRENCY = "INR"
DEFAULT_GST_TREATMENT = "business_gst"
DEFAULT_PLACE_OF_CONTACT = "MH"  # Maharashtra — update per user's state

TOKEN_KEY = "zoho_books"


class ZohoBooksConnector(BaseConnector):
    """
    Zoho Books direct API connector (India endpoint).
    Calls Zoho Books API v3 with bearer OAuth tokens.
    Auto-refreshes the access token on 401 responses.
    """

    name = "zoho_books"

    def __init__(self, config: dict = None):
        if config is None:
            from config.settings import get_connector_config
            config = get_connector_config("zoho_books")
        super().__init__(config or {})
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._org_id: Optional[str] = None
        self._client_id = ZOHO_CLIENT_ID
        self._client_secret = ZOHO_CLIENT_SECRET
        self._redirect_uri = ZOHO_REDIRECT_URI
        self._api_base = ZOHO_BOOKS_API_BASE
        self._load_stored_tokens()

    def _load_stored_tokens(self) -> None:
        tokens = load_tokens(TOKEN_KEY)
        if not tokens:
            tokens = load_tokens("zoho")  # migrate from legacy key
        if tokens:
            self._access_token = tokens.get("access_token")
            self._refresh_token = tokens.get("refresh_token")
            if self._access_token:
                self._authenticated = True

    def _headers(self) -> dict:
        if not self._access_token:
            raise AuthenticationError(
                self.name,
                "Not authenticated. Use the zoho_books_authenticate tool to log in."
            )
        return {
            "Authorization": f"Zoho-oauthtoken {self._access_token}",
            "Content-Type": "application/json",
        }

    def _refresh_if_expired(self, resp: requests.Response) -> bool:
        """Return True if token was refreshed (caller should retry the request)."""
        if resp.status_code != 401:
            return False
        if not self._refresh_token:
            raise AuthenticationError(
                self.name,
                "Access token expired and no refresh token available. Please re-authenticate."
            )
        try:
            new_tokens = refresh_access_token(
                self._refresh_token, self._client_id, self._client_secret
            )
            self._access_token = new_tokens["access_token"]
            stored = load_tokens(TOKEN_KEY) or load_tokens("zoho") or {}
            stored["access_token"] = self._access_token
            save_tokens(TOKEN_KEY, stored)
            logger.info("Access token refreshed successfully")
            return True
        except Exception as exc:
            raise AuthenticationError(self.name, f"Token refresh failed: {exc}")

    # ------------------------------------------------------------------
    # HTTP primitives
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict = None) -> dict:
        url = f"{self._api_base}/{path}"
        resp = requests.get(url, headers=self._headers(), params=params or {}, timeout=20)
        if self._refresh_if_expired(resp):
            resp = requests.get(url, headers=self._headers(), params=params or {}, timeout=20)
        if not resp.ok:
            raise ConnectorError(
                self.name,
                f"GET {path} failed {resp.status_code}: {resp.text[:300]}",
                resp.status_code,
            )
        return resp.json()

    def _post(self, path: str, body: dict = None, params: dict = None) -> dict:
        url = f"{self._api_base}/{path}"
        resp = requests.post(
            url, headers=self._headers(), json=body or {}, params=params or {}, timeout=20
        )
        if self._refresh_if_expired(resp):
            resp = requests.post(
                url, headers=self._headers(), json=body or {}, params=params or {}, timeout=20
            )
        if not resp.ok:
            raise ConnectorError(
                self.name,
                f"POST {path} failed {resp.status_code}: {resp.text[:300]}",
                resp.status_code,
            )
        return resp.json()

    def _put(self, path: str, body: dict = None, params: dict = None) -> dict:
        url = f"{self._api_base}/{path}"
        resp = requests.put(
            url, headers=self._headers(), json=body or {}, params=params or {}, timeout=20
        )
        if self._refresh_if_expired(resp):
            resp = requests.put(
                url, headers=self._headers(), json=body or {}, params=params or {}, timeout=20
            )
        if not resp.ok:
            raise ConnectorError(
                self.name,
                f"PUT {path} failed {resp.status_code}: {resp.text[:300]}",
                resp.status_code,
            )
        return resp.json()

    def _delete(self, path: str, params: dict = None) -> dict:
        url = f"{self._api_base}/{path}"
        resp = requests.delete(
            url, headers=self._headers(), params=params or {}, timeout=20
        )
        if self._refresh_if_expired(resp):
            resp = requests.delete(
                url, headers=self._headers(), params=params or {}, timeout=20
            )
        if not resp.ok:
            raise ConnectorError(
                self.name,
                f"DELETE {path} failed {resp.status_code}: {resp.text[:300]}",
                resp.status_code,
            )
        return resp.json() if resp.content else {"message": "deleted"}

    def _org_param(self, organization_id: str = None) -> dict:
        """Resolve organization_id, caching from list_organizations if omitted."""
        org = organization_id or self._org_id
        if not org:
            try:
                data = self._get("organizations")
                orgs = data.get("organizations", [])
                if orgs:
                    self._org_id = orgs[0]["organization_id"]
                    org = self._org_id
            except Exception:
                pass
        return {"organization_id": org} if org else {}

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self) -> dict:
        try:
            tokens = run_browser_oauth_flow(
                self._client_id, self._client_secret, self._redirect_uri
            )
            self._access_token = tokens.get("access_token")
            self._refresh_token = tokens.get("refresh_token")
            save_tokens(TOKEN_KEY, tokens)
            self._authenticated = True
            return {"success": True, "status": "ok", "message": "Zoho Books authenticated."}
        except Exception as exc:
            return {"success": False, "error": "auth_failed", "message": str(exc)}

    def execute(self, action: str, params: dict):
        raise ConnectorError(self.name, "Use the zoho_books_* MCP tools directly.")

    # ------------------------------------------------------------------
    # Organizations
    # ------------------------------------------------------------------

    def list_organizations(self) -> dict:
        data = self._get("organizations")
        orgs = data.get("organizations", [])
        if orgs and not self._org_id:
            self._org_id = orgs[0]["organization_id"]
        return {"success": True, "organizations": orgs, "count": len(orgs)}

    def get_organization(self, organization_id: str) -> dict:
        data = self._get(f"organizations/{organization_id}")
        return {"success": True, "organization": data.get("organization", data)}

    # ------------------------------------------------------------------
    # Contacts
    # ------------------------------------------------------------------

    def list_contacts(
        self, organization_id: str = None, contact_type: str = None, limit: int = 25
    ) -> dict:
        params = {**self._org_param(organization_id), "per_page": limit}
        if contact_type:
            params["contact_type"] = contact_type
        data = self._get("contacts", params)
        items = data.get("contacts", [])
        return {"success": True, "contacts": items, "count": len(items)}

    def get_contact(self, contact_id: str, organization_id: str = None) -> dict:
        data = self._get(f"contacts/{contact_id}", self._org_param(organization_id))
        return {"success": True, "contact": data.get("contact", data)}

    def create_contact(
        self, contact_name: str, organization_id: str = None, **fields
    ) -> dict:
        body = {
            "contact_name": contact_name,
            "currency_code": fields.pop("currency_code", DEFAULT_CURRENCY),
            "gst_treatment": fields.pop("gst_treatment", DEFAULT_GST_TREATMENT),
            **fields,
        }
        data = self._post("contacts", body, self._org_param(organization_id))
        return {
            "success": True,
            "contact": data.get("contact", {}),
            "message": data.get("message", "Contact created"),
        }

    def update_contact(
        self, contact_id: str, organization_id: str = None, **fields
    ) -> dict:
        data = self._put(f"contacts/{contact_id}", fields, self._org_param(organization_id))
        return {
            "success": True,
            "contact": data.get("contact", {}),
            "message": data.get("message", "Contact updated"),
        }

    def delete_contact(self, contact_id: str, organization_id: str = None) -> dict:
        data = self._delete(f"contacts/{contact_id}", self._org_param(organization_id))
        return {
            "success": True,
            "message": data.get("message", "Contact deleted"),
            "contact_id": contact_id,
        }

    # ------------------------------------------------------------------
    # Invoices
    # ------------------------------------------------------------------

    def list_invoices(
        self, organization_id: str = None, status: str = None, limit: int = 25
    ) -> dict:
        params = {**self._org_param(organization_id), "per_page": limit}
        if status:
            params["status"] = status
        data = self._get("invoices", params)
        items = data.get("invoices", [])
        return {"success": True, "invoices": items, "count": len(items)}

    def get_invoice(self, invoice_id: str, organization_id: str = None) -> dict:
        data = self._get(f"invoices/{invoice_id}", self._org_param(organization_id))
        return {"success": True, "invoice": data.get("invoice", data)}

    def create_invoice(
        self, customer_id: str, line_items: list, organization_id: str = None, **fields
    ) -> dict:
        body = {
            "customer_id": customer_id,
            "line_items": line_items,
            "currency_code": fields.pop("currency_code", DEFAULT_CURRENCY),
            **fields,
        }
        data = self._post("invoices", body, self._org_param(organization_id))
        return {
            "success": True,
            "invoice": data.get("invoice", {}),
            "message": data.get("message", "Invoice created"),
        }

    def update_invoice(
        self, invoice_id: str, organization_id: str = None, **fields
    ) -> dict:
        data = self._put(f"invoices/{invoice_id}", fields, self._org_param(organization_id))
        return {
            "success": True,
            "invoice": data.get("invoice", {}),
            "message": data.get("message", "Invoice updated"),
        }

    def delete_invoice(self, invoice_id: str, organization_id: str = None) -> dict:
        data = self._delete(f"invoices/{invoice_id}", self._org_param(organization_id))
        return {
            "success": True,
            "message": data.get("message", "Invoice deleted"),
            "invoice_id": invoice_id,
        }

    # ------------------------------------------------------------------
    # Estimates
    # ------------------------------------------------------------------

    def list_estimates(
        self, organization_id: str = None, status: str = None, limit: int = 25
    ) -> dict:
        params = {**self._org_param(organization_id), "per_page": limit}
        if status:
            params["status"] = status
        data = self._get("estimates", params)
        items = data.get("estimates", [])
        return {"success": True, "estimates": items, "count": len(items)}

    def get_estimate(self, estimate_id: str, organization_id: str = None) -> dict:
        data = self._get(f"estimates/{estimate_id}", self._org_param(organization_id))
        return {"success": True, "estimate": data.get("estimate", data)}

    def create_estimate(
        self, customer_id: str, line_items: list, organization_id: str = None, **fields
    ) -> dict:
        body = {
            "customer_id": customer_id,
            "line_items": line_items,
            "currency_code": fields.pop("currency_code", DEFAULT_CURRENCY),
            **fields,
        }
        data = self._post("estimates", body, self._org_param(organization_id))
        return {
            "success": True,
            "estimate": data.get("estimate", {}),
            "message": data.get("message", "Estimate created"),
        }

    def update_estimate(
        self, estimate_id: str, organization_id: str = None, **fields
    ) -> dict:
        data = self._put(f"estimates/{estimate_id}", fields, self._org_param(organization_id))
        return {
            "success": True,
            "estimate": data.get("estimate", {}),
            "message": data.get("message", "Estimate updated"),
        }

    def delete_estimate(self, estimate_id: str, organization_id: str = None) -> dict:
        data = self._delete(f"estimates/{estimate_id}", self._org_param(organization_id))
        return {
            "success": True,
            "message": data.get("message", "Estimate deleted"),
            "estimate_id": estimate_id,
        }

    # ------------------------------------------------------------------
    # Sales Orders
    # ------------------------------------------------------------------

    def list_sales_orders(
        self, organization_id: str = None, status: str = None, limit: int = 25
    ) -> dict:
        params = {**self._org_param(organization_id), "per_page": limit}
        if status:
            params["status"] = status
        data = self._get("salesorders", params)
        items = data.get("salesorders", [])
        return {"success": True, "sales_orders": items, "count": len(items)}

    def get_sales_order(self, salesorder_id: str, organization_id: str = None) -> dict:
        data = self._get(f"salesorders/{salesorder_id}", self._org_param(organization_id))
        return {"success": True, "sales_order": data.get("salesorder", data)}

    def create_sales_order(
        self, customer_id: str, line_items: list, organization_id: str = None, **fields
    ) -> dict:
        body = {
            "customer_id": customer_id,
            "line_items": line_items,
            "currency_code": fields.pop("currency_code", DEFAULT_CURRENCY),
            **fields,
        }
        data = self._post("salesorders", body, self._org_param(organization_id))
        return {
            "success": True,
            "sales_order": data.get("salesorder", {}),
            "message": data.get("message", "Sales order created"),
        }

    def update_sales_order(
        self, salesorder_id: str, organization_id: str = None, **fields
    ) -> dict:
        data = self._put(
            f"salesorders/{salesorder_id}", fields, self._org_param(organization_id)
        )
        return {
            "success": True,
            "sales_order": data.get("salesorder", {}),
            "message": data.get("message", "Sales order updated"),
        }

    def delete_sales_order(self, salesorder_id: str, organization_id: str = None) -> dict:
        data = self._delete(f"salesorders/{salesorder_id}", self._org_param(organization_id))
        return {
            "success": True,
            "message": data.get("message", "Sales order deleted"),
            "salesorder_id": salesorder_id,
        }

    # ------------------------------------------------------------------
    # Purchase Orders
    # ------------------------------------------------------------------

    def list_purchase_orders(
        self, organization_id: str = None, status: str = None, limit: int = 25
    ) -> dict:
        params = {**self._org_param(organization_id), "per_page": limit}
        if status:
            params["status"] = status
        data = self._get("purchaseorders", params)
        items = data.get("purchaseorders", [])
        return {"success": True, "purchase_orders": items, "count": len(items)}

    def get_purchase_order(self, purchaseorder_id: str, organization_id: str = None) -> dict:
        data = self._get(
            f"purchaseorders/{purchaseorder_id}", self._org_param(organization_id)
        )
        return {"success": True, "purchase_order": data.get("purchaseorder", data)}

    def create_purchase_order(
        self, vendor_id: str, line_items: list, organization_id: str = None, **fields
    ) -> dict:
        body = {
            "vendor_id": vendor_id,
            "line_items": line_items,
            "currency_code": fields.pop("currency_code", DEFAULT_CURRENCY),
            **fields,
        }
        data = self._post("purchaseorders", body, self._org_param(organization_id))
        return {
            "success": True,
            "purchase_order": data.get("purchaseorder", {}),
            "message": data.get("message", "Purchase order created"),
        }

    def update_purchase_order(
        self, purchaseorder_id: str, organization_id: str = None, **fields
    ) -> dict:
        data = self._put(
            f"purchaseorders/{purchaseorder_id}", fields, self._org_param(organization_id)
        )
        return {
            "success": True,
            "purchase_order": data.get("purchaseorder", {}),
            "message": data.get("message", "Purchase order updated"),
        }

    def delete_purchase_order(
        self, purchaseorder_id: str, organization_id: str = None
    ) -> dict:
        data = self._delete(
            f"purchaseorders/{purchaseorder_id}", self._org_param(organization_id)
        )
        return {
            "success": True,
            "message": data.get("message", "Purchase order deleted"),
            "purchaseorder_id": purchaseorder_id,
        }

    # ------------------------------------------------------------------
    # Expenses
    # ------------------------------------------------------------------

    def list_expenses(
        self, organization_id: str = None, status: str = None, limit: int = 25
    ) -> dict:
        params = {**self._org_param(organization_id), "per_page": limit}
        if status:
            params["status"] = status
        data = self._get("expenses", params)
        items = data.get("expenses", [])
        return {"success": True, "expenses": items, "count": len(items)}

    def get_expense(self, expense_id: str, organization_id: str = None) -> dict:
        data = self._get(f"expenses/{expense_id}", self._org_param(organization_id))
        return {"success": True, "expense": data.get("expense", data)}

    def create_expense(
        self, account_id: str, amount: float, organization_id: str = None, **fields
    ) -> dict:
        body = {
            "account_id": account_id,
            "amount": amount,
            "currency_code": fields.pop("currency_code", DEFAULT_CURRENCY),
            **fields,
        }
        data = self._post("expenses", body, self._org_param(organization_id))
        return {
            "success": True,
            "expense": data.get("expense", {}),
            "message": data.get("message", "Expense created"),
        }

    def update_expense(
        self, expense_id: str, organization_id: str = None, **fields
    ) -> dict:
        data = self._put(f"expenses/{expense_id}", fields, self._org_param(organization_id))
        return {
            "success": True,
            "expense": data.get("expense", {}),
            "message": data.get("message", "Expense updated"),
        }

    def delete_expense(self, expense_id: str, organization_id: str = None) -> dict:
        data = self._delete(f"expenses/{expense_id}", self._org_param(organization_id))
        return {
            "success": True,
            "message": data.get("message", "Expense deleted"),
            "expense_id": expense_id,
        }

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------

    def list_items(self, organization_id: str = None, limit: int = 25) -> dict:
        params = {**self._org_param(organization_id), "per_page": limit}
        data = self._get("items", params)
        items = data.get("items", [])
        return {"success": True, "items": items, "count": len(items)}

    def get_item(self, item_id: str, organization_id: str = None) -> dict:
        data = self._get(f"items/{item_id}", self._org_param(organization_id))
        return {"success": True, "item": data.get("item", data)}

    def create_item(
        self, name: str, rate: float, organization_id: str = None, **fields
    ) -> dict:
        body = {
            "name": name,
            "rate": rate,
            "currency_code": fields.pop("currency_code", DEFAULT_CURRENCY),
            **fields,
        }
        data = self._post("items", body, self._org_param(organization_id))
        return {
            "success": True,
            "item": data.get("item", {}),
            "message": data.get("message", "Item created"),
        }

    def update_item(self, item_id: str, organization_id: str = None, **fields) -> dict:
        data = self._put(f"items/{item_id}", fields, self._org_param(organization_id))
        return {
            "success": True,
            "item": data.get("item", {}),
            "message": data.get("message", "Item updated"),
        }

    def delete_item(self, item_id: str, organization_id: str = None) -> dict:
        data = self._delete(f"items/{item_id}", self._org_param(organization_id))
        return {
            "success": True,
            "message": data.get("message", "Item deleted"),
            "item_id": item_id,
        }

    # ------------------------------------------------------------------
    # Taxes
    # ------------------------------------------------------------------

    def list_taxes(self, organization_id: str = None) -> dict:
        data = self._get("settings/taxes", self._org_param(organization_id))
        items = data.get("taxes", [])
        return {"success": True, "taxes": items, "count": len(items)}

    def get_tax(self, tax_id: str, organization_id: str = None) -> dict:
        data = self._get(f"settings/taxes/{tax_id}", self._org_param(organization_id))
        return {"success": True, "tax": data.get("tax", data)}

    def create_tax(
        self,
        tax_name: str,
        organization_id: str = None,
        tax_percentage: float = None,
        **fields,
    ) -> dict:
        body = {
            "tax_name": tax_name,
            "tax_percentage": tax_percentage if tax_percentage is not None else DEFAULT_GST_RATE,
            **fields,
        }
        data = self._post("settings/taxes", body, self._org_param(organization_id))
        return {
            "success": True,
            "tax": data.get("tax", {}),
            "message": data.get("message", "Tax created"),
            "_note": f"Default tax_percentage={DEFAULT_GST_RATE}% (GST demo default). Verify before use.",
        }

    def update_tax(self, tax_id: str, organization_id: str = None, **fields) -> dict:
        data = self._put(
            f"settings/taxes/{tax_id}", fields, self._org_param(organization_id)
        )
        return {
            "success": True,
            "tax": data.get("tax", {}),
            "message": data.get("message", "Tax updated"),
        }

    def delete_tax(self, tax_id: str, organization_id: str = None) -> dict:
        data = self._delete(f"settings/taxes/{tax_id}", self._org_param(organization_id))
        return {
            "success": True,
            "message": data.get("message", "Tax deleted"),
            "tax_id": tax_id,
        }

    # ------------------------------------------------------------------
    # Customer Payments
    # ------------------------------------------------------------------

    def list_customer_payments(
        self, organization_id: str = None, limit: int = 25
    ) -> dict:
        params = {**self._org_param(organization_id), "per_page": limit}
        data = self._get("customerpayments", params)
        items = data.get("customerpayments", [])
        return {"success": True, "customer_payments": items, "count": len(items)}

    def get_customer_payment(self, payment_id: str, organization_id: str = None) -> dict:
        data = self._get(f"customerpayments/{payment_id}", self._org_param(organization_id))
        return {"success": True, "customer_payment": data.get("customerpayment", data)}

    def create_customer_payment(
        self, customer_id: str, amount: float, organization_id: str = None, **fields
    ) -> dict:
        body = {
            "customer_id": customer_id,
            "amount": amount,
            "currency_code": fields.pop("currency_code", DEFAULT_CURRENCY),
            **fields,
        }
        data = self._post("customerpayments", body, self._org_param(organization_id))
        return {
            "success": True,
            "customer_payment": data.get("customerpayment", {}),
            "message": data.get("message", "Customer payment created"),
        }

    def update_customer_payment(
        self, payment_id: str, organization_id: str = None, **fields
    ) -> dict:
        data = self._put(
            f"customerpayments/{payment_id}", fields, self._org_param(organization_id)
        )
        return {
            "success": True,
            "customer_payment": data.get("customerpayment", {}),
            "message": data.get("message", "Customer payment updated"),
        }

    def delete_customer_payment(
        self, payment_id: str, organization_id: str = None
    ) -> dict:
        data = self._delete(
            f"customerpayments/{payment_id}", self._org_param(organization_id)
        )
        return {
            "success": True,
            "message": data.get("message", "Customer payment deleted"),
            "payment_id": payment_id,
        }

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def list_users(self, organization_id: str = None) -> dict:
        data = self._get("users", self._org_param(organization_id))
        items = data.get("users", [])
        return {"success": True, "users": items, "count": len(items)}

    def get_user(self, user_id: str, organization_id: str = None) -> dict:
        data = self._get(f"users/{user_id}", self._org_param(organization_id))
        return {"success": True, "user": data.get("user", data)}

    # ------------------------------------------------------------------
    # Status & Health
    # ------------------------------------------------------------------

    def connection_status(self) -> dict:
        return {
            "success": True,
            "connector": self.name,
            "authenticated": self._authenticated,
            "has_access_token": bool(self._access_token),
            "has_refresh_token": bool(self._refresh_token),
            "cached_org_id": self._org_id,
            "mode": "direct_api",
            "api_base": self._api_base,
            "indian_defaults": {
                "gst_rate_pct": DEFAULT_GST_RATE,
                "tds_rate_pct": DEFAULT_TDS_RATE,
                "currency": DEFAULT_CURRENCY,
                "gst_treatment": DEFAULT_GST_TREATMENT,
                "note": "Demo defaults — verify with your accountant before real use.",
            },
        }

    def health_check(self) -> dict:
        return {
            "connector": self.name,
            "mode": "direct_api",
            "status": "ok" if self._authenticated else "unauthenticated",
            "authenticated": self._authenticated,
        }
