"""
Platform-level MCP tools — license management, platform status, and skill file updates.
These are the tools Claude uses to interact with the ReckLabs platform layer.
"""
import json
import logging
from datetime import datetime

import requests

from license.license_manager import activate_license, get_license_status
from config.settings import (
    PLATFORM_VERSION, MCP_SERVER_VERSION,
    SKILLS_DIR, SKILLS_BASE_DIR, SKILLS_UPDATE_URL,
)

logger = logging.getLogger(__name__)

_VERSIONS_FILE = SKILLS_DIR / "skill_versions.json"


def _load_local_versions() -> dict:
    if _VERSIONS_FILE.exists():
        try:
            return json.loads(_VERSIONS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_local_versions(versions: dict) -> None:
    _VERSIONS_FILE.write_text(json.dumps(versions, indent=2), encoding="utf-8")


# ------------------------------------------------------------------
# License tools
# ------------------------------------------------------------------

def check_license(params: dict) -> dict:
    """Return current license status and plan details."""
    return {"success": True, "data": get_license_status()}


def activate_license_key(params: dict) -> dict:
    """Activate a ReckLabs license key. Params: {key: str}"""
    key = params.get("key", "").strip()
    if not key:
        return {"success": False, "error": "missing_param", "message": "'key' parameter required"}
    return activate_license(key)


def get_platform_status(params: dict) -> dict:
    """Return platform version, registered connectors, and license status."""
    from registry.connector_registry import registry
    from config.settings import load_selected_connectors
    return {
        "success": True,
        "data": {
            "platform": "ReckLabs AI Agent",
            "platform_version": PLATFORM_VERSION,
            "mcp_server_version": MCP_SERVER_VERSION,
            "registered_connectors": registry.list_connectors(),
            "selected_connectors": load_selected_connectors(),
            "skill_versions": _load_local_versions(),
            "license": get_license_status(),
        },
    }


# ------------------------------------------------------------------
# Skill update tools (Layer 4 — Periodic Skill File Updates)
# ------------------------------------------------------------------

def check_skill_updates(params: dict) -> dict:
    """
    Check whether updated base skill files are available from the ReckLabs update server.
    Compares locally installed versions against the latest release manifest.
    """
    local_versions = _load_local_versions()
    # Strip _comment key if present
    local_versions = {k: v for k, v in local_versions.items() if not k.startswith("_")}

    try:
        resp = requests.get(SKILLS_UPDATE_URL, timeout=10)
        resp.raise_for_status()
        manifest = resp.json()
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Cannot reach update server. Check your internet connection.",
            "local_versions": local_versions,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Update check failed: {exc}",
            "local_versions": local_versions,
        }

    available_updates = []
    up_to_date = []

    for skill_name, remote_info in manifest.get("skills", {}).items():
        local_ver = local_versions.get(skill_name, {}).get("version", "0.0")
        remote_ver = remote_info.get("version", "0.0")
        if remote_ver > local_ver:
            available_updates.append({
                "skill": skill_name,
                "installed_version": local_ver,
                "available_version": remote_ver,
                "changelog": remote_info.get("changelog", ""),
            })
        else:
            up_to_date.append(skill_name)

    return {
        "success": True,
        "data": {
            "up_to_date": len(available_updates) == 0,
            "available_updates": available_updates,
            "up_to_date_skills": up_to_date,
            "manifest_version": manifest.get("version", "unknown"),
            "released_at": manifest.get("released_at", ""),
        },
    }


def apply_skill_updates(params: dict) -> dict:
    """
    Download and apply available base skill file updates from the ReckLabs update server.
    Only the base layer (.json.enc) is replaced — client customisations are never touched.
    After applying, skill definitions are automatically reloaded.
    """
    local_versions = _load_local_versions()
    local_versions = {k: v for k, v in local_versions.items() if not k.startswith("_")}

    try:
        resp = requests.get(SKILLS_UPDATE_URL, timeout=10)
        resp.raise_for_status()
        manifest = resp.json()
    except Exception as exc:
        return {"success": False, "error": f"Cannot fetch update manifest: {exc}"}

    applied = []
    skipped = []
    failed = []

    for skill_name, remote_info in manifest.get("skills", {}).items():
        local_ver = local_versions.get(skill_name, {}).get("version", "0.0")
        remote_ver = remote_info.get("version", "0.0")

        if remote_ver <= local_ver:
            skipped.append(skill_name)
            continue

        url = remote_info.get("url", "")
        if not url:
            failed.append({"skill": skill_name, "error": "No download URL in manifest"})
            continue

        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            enc_path = SKILLS_BASE_DIR / f"{skill_name}.json.enc"
            enc_path.write_bytes(r.content)
            local_versions[skill_name] = {
                "version": remote_ver,
                "updated_at": datetime.utcnow().isoformat(),
            }
            applied.append({
                "skill": skill_name,
                "version": remote_ver,
                "changelog": remote_info.get("changelog", ""),
            })
            logger.info("Applied skill update: %s -> v%s", skill_name, remote_ver)
        except Exception as exc:
            failed.append({"skill": skill_name, "error": str(exc)})
            logger.error("Failed to update skill %s: %s", skill_name, exc)

    if applied:
        _save_local_versions(local_versions)
        # Reload skill executor so updated files take effect immediately
        try:
            from tools.skill_tools import reload_skills
            reload_skills({})
        except Exception as exc:
            logger.warning("Could not auto-reload skills: %s", exc)

    return {
        "success": True,
        "data": {
            "applied": applied,
            "skipped": skipped,
            "failed": failed,
            "message": (
                f"Updated {len(applied)} skill(s). "
                f"{len(skipped)} already up to date. "
                f"{len(failed)} failed."
            ),
        },
    }


# ------------------------------------------------------------------
# Tool registry
# ------------------------------------------------------------------

PLATFORM_TOOLS = [
    {
        "name": "check_license",
        "description": "Check your ReckLabs license status and current plan (Free/Starter/Professional/Enterprise).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "fn": check_license,
    },
    {
        "name": "activate_license",
        "description": "Activate a ReckLabs license key to unlock additional connectors and features.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "License key in format XXXX-XXXX-XXXX-XXXX"},
            },
            "required": ["key"],
        },
        "fn": activate_license_key,
    },
    {
        "name": "get_platform_status",
        "description": "Get ReckLabs platform version, registered connectors, skill versions, and license info.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "fn": get_platform_status,
    },
    {
        "name": "check_skill_updates",
        "description": (
            "Check whether updated base skill files are available from the ReckLabs subscription update server. "
            "Shows installed vs available versions and changelogs."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "fn": check_skill_updates,
    },
    {
        "name": "apply_skill_updates",
        "description": (
            "Download and apply the latest base skill file updates from ReckLabs. "
            "Only the encrypted base layer is replaced — your client customisations are never touched. "
            "Requires an active subscription."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "fn": apply_skill_updates,
    },
]
