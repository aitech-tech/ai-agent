"""
build_release.py — ReckLabs Platform release packager.

Build pipeline (in order):
  1. Encrypt all skills/base/*.json  ->  skills/base/*.json.enc
  2. Package zip — includes .json.enc, excludes .env and plaintext .json base skills
  3. Validate zip — fails hard if any sensitive file is found inside
  4. Report final zip path and size

Usage:
    python scripts/build_release.py
    python scripts/build_release.py --version 1.0.1
"""
import subprocess
import sys
import zipfile
import argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = Path(__file__).parent

# ------------------------------------------------------------------
# Exclusion rules
# ------------------------------------------------------------------

# Top-level directories to exclude entirely
EXCLUDE_DIRS = {
    ".git",
    ".gitignore",
    ".claude",
    "__pycache__",
    "venv",
    "env",
    ".venv",
    "dist",
    "build",
    "storage",
    "scripts",   # internal build tools — not for distribution
    ".vscode",
    ".idea",
    "website",
}

# Exact relative POSIX paths to exclude (matched with as_posix())
EXCLUDE_FILES = {
    # Secrets — never ship
    ".env",
    # Old flat skills superseded by 2-layer system
    "skills/lead_generation.json",
    "skills/contact_enrichment.json",
    "skills/intent_map.json",   # re-generated from base skills
    # Runtime data
    "storage/tokens.json",
    "storage/agent.log",
    "storage/health.json",
    "storage/dashboard_snapshot.html",
}

# Extensions to exclude
EXCLUDE_EXTENSIONS = {".pyc", ".pyo", ".pyd"}


def should_exclude(path: Path) -> bool:
    parts = path.relative_to(ROOT).parts
    rel = path.relative_to(ROOT)

    # Top-level dir match
    if parts[0] in EXCLUDE_DIRS:
        return True

    # Exact file match (posix-normalised for cross-platform safety)
    rel_posix = rel.as_posix()
    if rel_posix in EXCLUDE_FILES:
        return True

    # Any .env* file except .env.example
    if path.name.startswith(".env") and path.name != ".env.example":
        return True

    # Plaintext base skills — only encrypted versions ship
    if (len(parts) >= 3 and parts[0] == "skills" and parts[1] == "base"
            and path.suffix == ".json"):
        return True

    # Bad extensions
    for ext in EXCLUDE_EXTENSIONS:
        if path.name.endswith(ext):
            return True

    return False


# ------------------------------------------------------------------
# Step 1 — Encrypt base skills
# ------------------------------------------------------------------

def encrypt_skills() -> None:
    print("[1/3] Encrypting base skills...")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "encrypt_base_skills.py")],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("ERROR: Encryption failed.")
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)
    for line in result.stdout.strip().splitlines():
        print(f"  {line}")
    print("  Base skills encrypted.\n")


# ------------------------------------------------------------------
# Step 2 — Package zip
# ------------------------------------------------------------------

def build_zip(version: str) -> Path:
    print("[2/3] Packaging release zip...")
    zip_name = f"recklabs-ai-agent-v{version}.zip"
    out_dir = ROOT / "dist"
    out_dir.mkdir(exist_ok=True)
    zip_path = out_dir / zip_name

    if zip_path.exists():
        zip_path.unlink()

    inner = f"recklabs-ai-agent-v{version}"
    file_count = 0
    included = []

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(ROOT.rglob("*")):
            if not file.is_file():
                continue
            if should_exclude(file):
                continue
            arcname = inner + "/" + file.relative_to(ROOT).as_posix()
            zf.write(file, arcname)
            included.append(arcname)
            file_count += 1

        # Ensure empty storage/ dir exists — installer writes into it at runtime
        try:
            zf.mkdir(f"{inner}/storage")
        except AttributeError:
            pass  # Python < 3.11 — storage dir will be created by installer

    size_kb = zip_path.stat().st_size // 1024
    print(f"  Files packaged: {file_count}")
    print(f"  Output: {zip_path}  ({size_kb} KB)\n")
    return zip_path, included


# ------------------------------------------------------------------
# Step 3 — Validate zip (import and call validate_release)
# ------------------------------------------------------------------

def validate_zip(zip_path: Path) -> None:
    print("[3/3] Validating release zip...")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "validate_release.py"), str(zip_path)],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print("BUILD FAILED — validation errors above. Zip deleted.")
        zip_path.unlink(missing_ok=True)
        sys.exit(1)
    print("  Validation passed.\n")


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ReckLabs release packager")
    parser.add_argument("--version", default="1.0.1", help="Version number (default: 1.0.1)")
    parser.add_argument("--skip-encrypt", action="store_true", help="Skip encryption step (use existing .json.enc)")
    args = parser.parse_args()

    print("=" * 60)
    print(f"  ReckLabs Release Build  v{args.version}")
    print("=" * 60 + "\n")

    if not args.skip_encrypt:
        encrypt_skills()

    zip_path, _ = build_zip(args.version)
    validate_zip(zip_path)

    print("=" * 60)
    print(f"  BUILD COMPLETE: {zip_path.name}")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Upload to GitHub Release:")
    print(f"     gh release upload v{args.version} dist/recklabs-ai-agent-v{args.version}.zip dist/skill_manifest.json dist/*.json.enc --clobber")
    print()


if __name__ == "__main__":
    main()
