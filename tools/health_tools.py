"""
Connector health MCP tools — Phase 1 Connector Health Dashboard.

Checks status of all registered connectors and writes health.json for the dashboard.
open_health_dashboard generates a self-contained HTML snapshot and opens it in the browser.
"""
import json
import logging
import webbrowser
from datetime import datetime
from pathlib import Path

from registry.connector_registry import registry
from config.settings import HEALTH_FILE

logger = logging.getLogger(__name__)

_DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>ReckLabs — Connector Health Dashboard</title>
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    :root{{--bg:#0f0f13;--surface:#1a1a24;--border:#2e2e48;--accent:#7c6aff;
          --text:#e8e8f0;--muted:#8888a8;--green:#34d399;--red:#f87171;--yellow:#fbbf24;--radius:10px}}
    body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
          background:var(--bg);color:var(--text);padding:2rem;line-height:1.5}}
    h1{{font-size:1.5rem;font-weight:800;margin-bottom:0.3rem;color:var(--accent)}}
    .ts{{color:var(--muted);font-size:0.85rem;margin-bottom:2rem}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:1rem}}
    .card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:1.5rem}}
    .card-head{{display:flex;align-items:center;justify-content:space-between;margin-bottom:0.8rem}}
    .name{{font-weight:700;font-size:1rem}}
    .badge{{padding:0.2rem 0.7rem;border-radius:100px;font-size:0.75rem;font-weight:700}}
    .ok{{background:rgba(52,211,153,.15);color:var(--green);border:1px solid rgba(52,211,153,.3)}}
    .error{{background:rgba(248,113,113,.15);color:var(--red);border:1px solid rgba(248,113,113,.3)}}
    .unknown{{background:rgba(251,191,36,.15);color:var(--yellow);border:1px solid rgba(251,191,36,.3)}}
    .detail{{font-size:0.82rem;color:var(--muted)}}
    .detail span{{color:var(--text)}}
  </style>
</head>
<body>
  <h1>ReckLabs Connector Health</h1>
  <p class="ts">Last updated: {timestamp}</p>
  <div class="grid">{cards}</div>
</body>
</html>"""

_CARD_TEMPLATE = """
  <div class="card">
    <div class="card-head">
      <span class="name">{name}</span>
      <span class="badge {badge_class}">{status_label}</span>
    </div>
    <div class="detail">Authenticated: <span>{auth}</span></div>
    {extra}
  </div>"""


def _build_dashboard_html(health_data: dict) -> str:
    ts = health_data.get("timestamp", datetime.utcnow().isoformat())
    cards_html = ""
    for name, info in health_data.get("connectors", {}).items():
        status = info.get("status", "unknown")
        badge = "ok" if status == "ok" else ("error" if status == "error" else "unknown")
        label = status.upper()
        auth = "Yes" if info.get("authenticated") else "No"
        extra = ""
        if info.get("error"):
            extra = f'<div class="detail" style="color:var(--red)">Error: <span>{info["error"]}</span></div>'
        cards_html += _CARD_TEMPLATE.format(
            name=name.title(),
            badge_class=badge,
            status_label=label,
            auth=auth,
            extra=extra,
        )
    return _DASHBOARD_TEMPLATE.format(timestamp=ts, cards=cards_html)


def get_connector_health(params: dict) -> dict:
    """Check health of all registered connectors and update health.json."""
    results = registry.health_check_all()
    health_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "connectors": results,
    }
    try:
        HEALTH_FILE.write_text(json.dumps(health_data, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("Could not write health file: %s", e)
    return {"success": True, "data": health_data}


def open_health_dashboard(params: dict) -> dict:
    """Generate a fresh health dashboard HTML snapshot and open it in the browser."""
    results = registry.health_check_all()
    health_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "connectors": results,
    }
    try:
        HEALTH_FILE.write_text(json.dumps(health_data, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("Could not write health file: %s", e)

    html = _build_dashboard_html(health_data)
    dashboard_path = Path(HEALTH_FILE.parent) / "dashboard_snapshot.html"
    dashboard_path.write_text(html, encoding="utf-8")

    webbrowser.open(dashboard_path.as_uri())
    return {
        "success": True,
        "data": {
            "connectors_checked": len(results),
            "message": "Health dashboard opened in browser",
            "path": str(dashboard_path),
        },
    }


HEALTH_TOOLS = [
    {
        "name": "get_connector_health",
        "description": "Check health and connection status of all registered connectors.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "fn": get_connector_health,
    },
    {
        "name": "open_health_dashboard",
        "description": "Open the local connector health dashboard in your browser.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "fn": open_health_dashboard,
    },
]
