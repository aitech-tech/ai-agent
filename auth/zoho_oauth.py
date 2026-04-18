"""
Zoho OAuth2 — fully automatic flow, zero manual input.

Flow:
  1. Start Flask callback server on localhost:8000 (background daemon thread)
  2. Open browser → Zoho login page
  3. User logs in → Zoho redirects to localhost:8000/callback?code=...
  4. Flask handler captures code, exchanges for tokens, saves to storage/tokens.json
  5. Main thread unblocks via threading.Event → returns success
  No copy-paste. No manual steps.
"""
import json
import logging
import socket
import threading
import webbrowser
from urllib.parse import urlencode, urlparse

import requests

from config.settings import (
    ZOHO_AUTH_URL, ZOHO_TOKEN_URL, ZOHO_REDIRECT_URI,
    ZOHO_SCOPES, TOKENS_FILE, ensure_storage,
)

logger = logging.getLogger(__name__)

# Shared state between Flask thread and main thread
_auth_result: dict = {"tokens": None, "error": None}
_auth_event = threading.Event()


# ------------------------------------------------------------------
# Port check
# ------------------------------------------------------------------

def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("localhost", port))
            return True
        except OSError:
            return False


# ------------------------------------------------------------------
# Flask callback server
# ------------------------------------------------------------------

def _start_callback_server(
    port: int, client_id: str, client_secret: str, redirect_uri: str
) -> None:
    try:
        from flask import Flask, request as flask_req
    except ImportError:
        raise RuntimeError("flask package required. Run: pip install flask")

    import logging as _log
    _log.getLogger("werkzeug").setLevel(_log.ERROR)  # suppress Flask request logs from stdout

    app = Flask(__name__)
    app.logger.setLevel(_log.ERROR)

    @app.route("/callback")
    def callback():
        error = flask_req.args.get("error")
        code = flask_req.args.get("code")

        if error:
            _auth_result["error"] = f"Zoho returned error: {error}"
            _auth_event.set()
            return _html_page("error", "Authentication Failed",
                              f"Zoho returned: {error}"), 400

        if not code:
            _auth_result["error"] = "No authorization code in callback"
            _auth_event.set()
            return _html_page("error", "Authentication Failed",
                              "No authorization code received."), 400

        try:
            logger.info("Authorization code received — exchanging for tokens")
            tokens = exchange_code_for_tokens(code, client_id, client_secret, redirect_uri)
            save_tokens("zoho", tokens)
            _auth_result["tokens"] = tokens
            _auth_event.set()
            logger.info("Authentication successful")
            return _html_page("success", "Zoho Connected",
                              "Authentication successful. You can close this window.")
        except Exception as exc:
            _auth_result["error"] = str(exc)
            _auth_event.set()
            return _html_page("error", "Token Exchange Failed", str(exc)), 500

    thread = threading.Thread(
        target=lambda: app.run(host="localhost", port=port, debug=False, use_reloader=False),
        daemon=True,
        name="zoho-oauth-callback",
    )
    thread.start()


def _html_page(kind: str, title: str, message: str) -> str:
    color = "#38a169" if kind == "success" else "#e53e3e"
    icon = "✓" if kind == "success" else "✗"
    return f"""<!DOCTYPE html>
<html><head><title>{title}</title></head>
<body style="font-family:sans-serif;text-align:center;padding:80px;background:#f9f9f9">
  <h2 style="color:{color}">{icon} {title}</h2>
  <p style="color:#555;font-size:1.1rem">{message}</p>
</body></html>"""


# ------------------------------------------------------------------
# OAuth helpers (token exchange, refresh, storage)
# ------------------------------------------------------------------

def get_authorization_url(
    client_id: str, redirect_uri: str = ZOHO_REDIRECT_URI
) -> str:
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
    code: str, client_id: str, client_secret: str,
    redirect_uri: str = ZOHO_REDIRECT_URI,
) -> dict:
    resp = requests.post(ZOHO_TOKEN_URL, data={
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code": code,
    }, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Token exchange error: {data['error']}")
    return data


def refresh_access_token(
    refresh_token: str, client_id: str, client_secret: str,
) -> dict:
    resp = requests.post(ZOHO_TOKEN_URL, data={
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }, timeout=15)
    resp.raise_for_status()
    return resp.json()


def save_tokens(connector_name: str, tokens: dict) -> None:
    ensure_storage()
    existing = {}
    if TOKENS_FILE.exists():
        try:
            existing = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    existing[connector_name] = tokens
    TOKENS_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    logger.info("Tokens saved for connector: %s", connector_name)


def load_tokens(connector_name: str) -> dict:
    ensure_storage()
    if not TOKENS_FILE.exists():
        return {}
    try:
        data = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
        return data.get(connector_name, {})
    except json.JSONDecodeError:
        return {}


# ------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------

def run_browser_oauth_flow(
    client_id: str,
    client_secret: str,
    redirect_uri: str = ZOHO_REDIRECT_URI,
    timeout: int = 120,
) -> dict:
    """
    Fully automatic OAuth flow:
      - starts local Flask server
      - opens browser
      - waits for Zoho to redirect back
      - captures and exchanges code automatically
      - returns tokens dict
    Raises RuntimeError / TimeoutError on failure.
    """
    port = int(urlparse(redirect_uri).port or 8000)

    # Reset shared state from any previous call
    _auth_result["tokens"] = None
    _auth_result["error"] = None
    _auth_event.clear()

    if not _port_available(port):
        raise RuntimeError(
            f"Port {port} is already in use. "
            "Close the application using it and try again."
        )

    _start_callback_server(port, client_id, client_secret, redirect_uri)

    url = get_authorization_url(client_id, redirect_uri)
    logger.info("Opening browser for authentication...")
    webbrowser.open(url)
    logger.info("Waiting for authorization... (timeout: %ds)", timeout)

    received = _auth_event.wait(timeout=timeout)

    if not received:
        raise TimeoutError(
            f"Authentication timed out after {timeout}s. "
            "Please try again."
        )

    if _auth_result["error"]:
        raise RuntimeError(_auth_result["error"])

    return _auth_result["tokens"]
