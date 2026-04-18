"""
Skill file encryption/decryption using AES-256 via Fernet (cryptography package).

Phase 1 architecture per PDF:
  - Base skill files (.json.enc in skills/base/) are encrypted — our IP
  - Only the licensed MCP server runtime can decrypt and execute the base layer
  - Client customisation layer (skills/client/) stays plain JSON, always editable

Phase 1: Key embedded in runtime (obfuscated).
Phase 2+: Key fetched from Recklabs license server after activation.
"""
import json
import base64
import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Phase 1: Platform-embedded key. Obfuscated in production builds.
# Phase 2: Replaced with license-server-issued key per activation.
_PLATFORM_SECRET = "ReckLabs_MCP_Platform_v1_2024_AI_Connector_Stable"


def _get_fernet():
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        raise RuntimeError(
            "cryptography package required. Run: pip install cryptography"
        )
    raw = hashlib.sha256(_PLATFORM_SECRET.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(raw))


def encrypt_skill(skill_data: dict) -> bytes:
    """Encrypt a skill dict to bytes for storage as .json.enc file."""
    return _get_fernet().encrypt(json.dumps(skill_data, indent=2).encode("utf-8"))


def decrypt_skill(encrypted_data: bytes) -> dict:
    """Decrypt a .json.enc skill file back to a dict."""
    try:
        return json.loads(_get_fernet().decrypt(encrypted_data).decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Failed to decrypt skill: {e}")


def save_encrypted_skill(skill_data: dict, path: Path) -> None:
    """Encrypt and save a skill dict to a .json.enc file."""
    path.write_bytes(encrypt_skill(skill_data))
    logger.info("Encrypted skill saved: %s", path.name)


def load_encrypted_skill(path: Path) -> dict:
    """Load and decrypt a .json.enc skill file."""
    return decrypt_skill(path.read_bytes())
