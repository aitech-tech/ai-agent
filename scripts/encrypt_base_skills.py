"""
encrypt_base_skills.py — ReckLabs Platform utility.

Encrypts plain .json files in skills/base/ to .json.enc files using AES-256.
Run this before distributing the platform to protect base skill IP.

Usage:
    python scripts/encrypt_base_skills.py
    python scripts/encrypt_base_skills.py --skill lead_generation
    python scripts/encrypt_base_skills.py --decrypt   (verify by decrypting)
"""
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from skills.skill_crypto import encrypt_skill, decrypt_skill, save_encrypted_skill, load_encrypted_skill
from config.settings import SKILLS_BASE_DIR


def encrypt_all(skill_name: str = None, delete_plain: bool = False):
    """Encrypt all (or one) plain .json base skills to .json.enc."""
    if not SKILLS_BASE_DIR.exists():
        print(f"ERROR: skills/base/ not found at {SKILLS_BASE_DIR}")
        sys.exit(1)

    pattern = f"{skill_name}.json" if skill_name else "*.json"
    files = list(SKILLS_BASE_DIR.glob(pattern))

    if not files:
        print(f"No plain .json files found in {SKILLS_BASE_DIR}")
        return

    for plain_path in files:
        if plain_path.suffix != ".json":
            continue
        try:
            data = json.loads(plain_path.read_text(encoding="utf-8"))
            enc_path = plain_path.with_suffix(".json.enc")
            # .with_suffix replaces .json → .json.enc doesn't work directly;
            # need to handle the double extension manually
            enc_path = plain_path.parent / (plain_path.stem + ".json.enc")
            save_encrypted_skill(data, enc_path)
            print(f"  Encrypted: {plain_path.name} -> {enc_path.name}")
            if delete_plain:
                plain_path.unlink()
                print(f"  Deleted plain: {plain_path.name}")
        except Exception as e:
            print(f"  ERROR encrypting {plain_path.name}: {e}")


def verify_all(skill_name: str = None):
    """Decrypt and pretty-print all .json.enc files to verify they're readable."""
    pattern = f"{skill_name}.json.enc" if skill_name else "*.json.enc"
    files = list(SKILLS_BASE_DIR.glob(pattern))

    if not files:
        print("No .json.enc files found to verify.")
        return

    for enc_path in files:
        try:
            data = load_encrypted_skill(enc_path)
            print(f"\n--- {enc_path.name} ---")
            print(json.dumps(data, indent=2))
        except Exception as e:
            print(f"  ERROR decrypting {enc_path.name}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ReckLabs base skill encryptor")
    parser.add_argument("--skill", help="Encrypt/verify a single skill by name")
    parser.add_argument("--decrypt", action="store_true", help="Verify by decrypting (show content)")
    parser.add_argument("--delete-plain", action="store_true", help="Delete plain .json after encrypting")
    args = parser.parse_args()

    if args.decrypt:
        print("Verifying encrypted skills...\n")
        verify_all(args.skill)
    else:
        print("Encrypting base skills...\n")
        encrypt_all(args.skill, delete_plain=args.delete_plain)
        print("\nDone. Use --decrypt to verify.")
