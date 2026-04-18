"""
License manager — ReckLabs AI Agent Platform Phase 1.

Phase 1: Local license validation with tier determination from key prefix.
Phase 2+: Key validated against Recklabs license server (HTTPS, authenticated).

Tiers and connector limits per PDF business model:
  free         — up to 1 connector, 3 skills
  starter      — up to 3 connectors, 10 skills
  professional — up to 10 connectors, 50 skills
  enterprise   — unlimited connectors and skills

Key format: XXXX-XXXX-XXXX-XXXX (alphanumeric segments)
Tier prefix:  FREE, STRT, PROF, ENTR
"""
import json
import logging
from datetime import datetime
from pathlib import Path

from config.settings import LICENSE_FILE

logger = logging.getLogger(__name__)

TIERS: dict[str, dict] = {
    "free": {
        "name": "Free",
        "connectors": 1,
        "skills": 3,
        "features": ["Basic skill files", "Community support"],
    },
    "starter": {
        "name": "Starter",
        "connectors": 3,
        "skills": 10,
        "features": ["Basic skill files", "Skill updates", "Email support"],
    },
    "professional": {
        "name": "Professional",
        "connectors": 10,
        "skills": 50,
        "features": ["Advanced skill files", "Workflow builder", "Priority support", "Skill updates"],
    },
    "enterprise": {
        "name": "Enterprise",
        "connectors": -1,    # -1 = unlimited
        "skills": -1,
        "features": ["All connectors", "Custom connectors", "Fine-tuning", "SLA", "White label"],
    },
}

# Key prefix → tier mapping
_PREFIX_TIER: dict[str, str] = {
    "FREE": "free",
    "STRT": "starter",
    "PROF": "professional",
    "ENTR": "enterprise",
}


def load_license() -> dict:
    if LICENSE_FILE.exists():
        try:
            return json.loads(LICENSE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"key": None, "activated": False, "tier": "free"}


def _save_license(data: dict) -> None:
    LICENSE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _valid_format(key: str) -> bool:
    """XXXX-XXXX-XXXX-XXXX — four alphanumeric segments of 4 characters each."""
    parts = key.upper().split("-")
    return len(parts) == 4 and all(len(p) == 4 and p.isalnum() for p in parts)


def _tier_from_key(key: str) -> str:
    prefix = key.upper()[:4]
    return _PREFIX_TIER.get(prefix, "starter")


def activate_license(key: str) -> dict:
    """
    Activate a license key.
    Phase 1: local format validation + tier determination.
    Phase 2: POST to Recklabs license server for server-side validation.
    """
    key = key.strip().upper()
    if not _valid_format(key):
        return {
            "success": False,
            "error": "invalid_key_format",
            "message": "License key must be in format XXXX-XXXX-XXXX-XXXX (e.g. PROF-A1B2-C3D4-E5F6)",
        }

    tier = _tier_from_key(key)
    tier_info = TIERS[tier]

    record = {
        "key": key,
        "activated": True,
        "tier": tier,
        "activated_at": datetime.utcnow().isoformat(),
    }
    _save_license(record)
    logger.info("License activated: tier=%s", tier)

    return {
        "success": True,
        "data": {
            "tier": tier,
            "plan_name": tier_info["name"],
            "connectors_allowed": tier_info["connectors"],
            "skills_allowed": tier_info["skills"],
            "features": tier_info["features"],
            "message": f"License activated. Plan: {tier_info['name']}",
        },
    }


def get_license_status() -> dict:
    lic = load_license()
    tier = lic.get("tier", "free")
    info = TIERS.get(tier, TIERS["free"])
    key = lic.get("key")
    return {
        "activated": lic.get("activated", False),
        "tier": tier,
        "plan_name": info["name"],
        "connectors_allowed": info["connectors"],
        "skills_allowed": info["skills"],
        "features": info["features"],
        "key_preview": f"{key[:4]}****" if key else None,
        "activated_at": lic.get("activated_at"),
    }


def is_connector_allowed(connector_name: str, active_count: int) -> bool:
    """Check whether adding a connector is within the current plan limit."""
    status = get_license_status()
    limit = status["connectors_allowed"]
    if limit == -1:
        return True
    return active_count < limit
