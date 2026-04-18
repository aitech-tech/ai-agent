"""
Zoho OAuth2 flow implementation.
Handles authorization URL generation, token exchange, refresh, and local storage.
"""
import json
import logging
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from urllib.parse import urlencode, urlparse, parse_qs

import requests

from config.settings import (
    ZOHO_AUTH_URL, ZOHO_TOKEN_URL, ZOHO_REDIRECT_URI,
    ZOHO_SCOPES, TOKENS_FILE, ensure_storage
)

logger = logging.getLogger(__name__)

_auth_code_holder = {"code": None, "error": None}


class _CallbackHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler to capture the OAuth callback."""

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if "code" in params:
            _auth_code_holder["code"] = params["code"][0]
            body = b"<h2>Authorization successful! You can close this tab.</h2>"
        else:
            _auth_code_holder["error"] = params.get("error", ["unknown"])[0]
            body = b"<h2>Authorization failed. Check the agent console.</h2>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # Suppress default request logging


def _start_callback_server(port: int) -> HTTPServer:
    server = HTTPServer(("localhost", port), _CallbackHandler)
    thread = Thread(target=server.handle_request, daemon=True)
    thread.start()
    return server


def get_authorization_url(client_id: str, redirect_uri: str = ZOHO_REDIRECT_URI) -> str:
    """Build the Zoho OAuth2 authorization URL."""
    params = {
        "response_type": "code",
        "client_id": client_id,
        "scope": ZOHO_SCOPES,
        "redirect_uri": redirect_uri,
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{ZOHO_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_tokens(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str = ZOHO_REDIRECT_URI,
) -> dict:
    """Exchange authorization code for access + refresh tokens."""
    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    resp = requests.post(ZOHO_TOKEN_URL, data=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(
    refresh_token: str,
    client_id: str,
    client_secret: str,
) -> dict:
    """Use the refresh token to obtain a new access token."""
    payload = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }
    resp = requests.post(ZOHO_TOKEN_URL, data=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def save_tokens(connector_name: str, tokens: dict) -> None:
    ensure_storage()
    existing = {}
    if TOKENS_FILE.exists():
        try:
            existing = json.loads(TOKENS_FILE.read_text())
        except json.JSONDecodeError:
            pass
    existing[connector_name] = tokens
    TOKENS_FILE.write_text(json.dumps(existing, indent=2))
    logger.info("Tokens saved for connector: %s", connector_name)


def load_tokens(connector_name: str) -> dict:
    ensure_storage()
    if not TOKENS_FILE.exists():
        return {}
    try:
        data = json.loads(TOKENS_FILE.read_text())
        return data.get(connector_name, {})
    except json.JSONDecodeError:
        return {}


def run_browser_oauth_flow(
    client_id: str,
    client_secret: str,
    redirect_uri: str = ZOHO_REDIRECT_URI,
) -> dict:
    """
    Full browser-based OAuth flow:
    1. Open browser to authorization URL
    2. Start local callback server
    3. Exchange received code for tokens
    4. Save and return tokens
    """
    from urllib.parse import urlparse
    port = int(urlparse(redirect_uri).port or 8766)

    _auth_code_holder["code"] = None
    _auth_code_holder["error"] = None

    server = _start_callback_server(port)
    url = get_authorization_url(client_id, redirect_uri)
    logger.info("Opening browser for Zoho authorization: %s", url)
    webbrowser.open(url)

    # Wait for callback (server.handle_request in thread)
    import time
    for _ in range(60):  # Wait up to 60 seconds
        if _auth_code_holder["code"] or _auth_code_holder["error"]:
            break
        time.sleep(1)

    if _auth_code_holder["error"]:
        raise RuntimeError(f"OAuth error: {_auth_code_holder['error']}")
    if not _auth_code_holder["code"]:
        raise TimeoutError("OAuth flow timed out waiting for authorization code")

    tokens = exchange_code_for_tokens(
        _auth_code_holder["code"], client_id, client_secret, redirect_uri
    )
    save_tokens("zoho", tokens)
    return tokens
