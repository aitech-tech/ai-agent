"""
validate_release.py — ReckLabs release zip security validator.

Fails with exit code 1 if any forbidden file is found inside the zip.
Called automatically by build_release.py after packaging.

Usage:
    python scripts/validate_release.py dist/recklabs-ai-agent-v1.0.1.zip
"""
import sys
import zipfile
from pathlib import Path

# ------------------------------------------------------------------
# Rules
# ------------------------------------------------------------------

# Any zip entry matching these exact names (basename) is forbidden
FORBIDDEN_NAMES = {}

# Any zip entry whose path contains these substrings is forbidden
FORBIDDEN_SUBSTRINGS = {
    "storage/tokens.json",
    "storage/agent.log",
    "storage/health.json",
    "storage/dashboard_snapshot.html",
}

# Any zip entry matching these suffix patterns is forbidden
FORBIDDEN_SUFFIXES = (
    ".pyc",
    ".pyo",
    ".pyd",
)

# Any zip entry path matching these patterns is forbidden
# (checked after stripping the top-level folder prefix e.g. "recklabs-ai-agent-v1.0.1/")
def is_plaintext_base_skill(entry: str) -> bool:
    """skills/base/<name>.json (not .json.enc) must never ship."""
    parts = entry.split("/")
    # strip leading version folder
    if len(parts) > 1:
        parts = parts[1:]
    return (
        len(parts) >= 3
        and parts[0] == "skills"
        and parts[1] == "base"
        and parts[2].endswith(".json")
        and not parts[2].endswith(".json.enc")
    )


# Required entries (relative to inner folder, using glob-style checks)
REQUIRED_CHECKS = [
    ("skills/base/*.json.enc", lambda entries: any(
        "skills/base/" in e and e.endswith(".json.enc") for e in entries
    )),
    (".env.example", lambda entries: any(
        e.endswith("/.env.example") or e == ".env.example" for e in entries
    )),
    ("installer/install.bat", lambda entries: any(
        "installer/install.bat" in e for e in entries
    )),
    ("main.py", lambda entries: any(
        e.endswith("/main.py") for e in entries
    )),
]


# ------------------------------------------------------------------
# Validator
# ------------------------------------------------------------------

def validate(zip_path: Path) -> bool:
    errors = []
    warnings = []

    with zipfile.ZipFile(zip_path) as zf:
        entries = zf.namelist()

    for entry in entries:
        name = entry.split("/")[-1]

        # Forbidden exact names
        if name in FORBIDDEN_NAMES:
            errors.append(f"  FORBIDDEN FILE: {entry}")

        # Forbidden substrings
        for sub in FORBIDDEN_SUBSTRINGS:
            if sub in entry:
                errors.append(f"  FORBIDDEN PATH: {entry}  (matches '{sub}')")

        # Forbidden extensions
        if name.endswith(FORBIDDEN_SUFFIXES):
            errors.append(f"  FORBIDDEN EXT:  {entry}")

        # Plaintext base skills
        if is_plaintext_base_skill(entry):
            errors.append(f"  PLAINTEXT SKILL (IP LEAK): {entry}")

    # Required files must be present
    for label, check in REQUIRED_CHECKS:
        if not check(entries):
            errors.append(f"  MISSING REQUIRED: {label}")

    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print(e)
        return False

    # Summary of what IS included
    enc_skills = [e for e in entries if "skills/base/" in e and e.endswith(".json.enc")]
    print(f"  Encrypted base skills: {len(enc_skills)}")
    for s in enc_skills:
        print(f"    + {s.split('/')[-1]}")
    print(f"  Total entries: {len(entries)}")
    return True


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: validate_release.py <path-to-zip>")
        sys.exit(1)

    zip_path = Path(sys.argv[1])
    if not zip_path.exists():
        print(f"ERROR: zip not found: {zip_path}")
        sys.exit(1)

    ok = validate(zip_path)
    sys.exit(0 if ok else 1)
