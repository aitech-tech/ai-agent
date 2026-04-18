"""
build_release.py — ReckLabs Platform release packager.

Creates a clean distribution zip (recklabs-ai-agent-vX.Y.Z.zip) ready for
GitHub Releases. The zip contains everything a new user needs: all code,
platform credentials pre-baked into connectors.json, and the installer.

Usage:
    python scripts/build_release.py
    python scripts/build_release.py --version 1.0.1
"""
import sys
import shutil
import zipfile
import argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Files and folders to EXCLUDE from the release zip
EXCLUDE = {
    ".git",
    ".gitignore",
    ".claude",       # Claude Code IDE config — internal only
    "__pycache__",
    "venv",
    "env",
    ".venv",
    "dist",
    "build",
    "storage",       # tokens, logs — not for distribution
    "scripts",       # internal build/dev tools
    ".vscode",
    ".idea",
    "website",       # website is deployed separately, not in the agent zip
}

# Individual files to exclude
EXCLUDE_FILES = {
    "storage/tokens.json",
    "storage/agent.log",
    "storage/health.json",
    "storage/dashboard_snapshot.html",
    # Old flat skill files superseded by the 2-layer base/client system
    "skills/lead_generation.json",
    "skills/contact_enrichment.json",
}

# Skill encrypted files — installer generates these on client machine
EXCLUDE_EXTENSIONS = {".pyc", ".pyo", ".pyd", ".json.enc"}


def should_exclude(path: Path) -> bool:
    parts = path.relative_to(ROOT).parts
    if parts[0] in EXCLUDE:
        return True
    rel = str(path.relative_to(ROOT))
    if rel in EXCLUDE_FILES:
        return True
    name = path.name
    for ext in EXCLUDE_EXTENSIONS:
        if name.endswith(ext):
            return True
    return False


def build_zip(version: str) -> Path:
    zip_name = f"recklabs-ai-agent-v{version}.zip"
    out_dir = ROOT / "dist"
    out_dir.mkdir(exist_ok=True)
    zip_path = out_dir / zip_name

    if zip_path.exists():
        zip_path.unlink()

    inner = f"recklabs-ai-agent-v{version}"
    file_count = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(ROOT.rglob("*")):
            if not file.is_file():
                continue
            if should_exclude(file):
                continue
            arcname = inner + "/" + str(file.relative_to(ROOT))
            zf.write(file, arcname)
            file_count += 1

        # Ensure empty storage/ dir exists in the zip (installer writes into it)
        zf.mkdir(f"{inner}/storage") if hasattr(zf, "mkdir") else None

    size_kb = zip_path.stat().st_size // 1024
    print(f"Built: {zip_path}")
    print(f"Files: {file_count} | Size: {size_kb} KB")
    print()
    print("Next: upload this file to a GitHub Release as a release asset.")
    print("Then update the download link in website/index.html.")
    return zip_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ReckLabs release packager")
    parser.add_argument("--version", default="1.0.0", help="Version number (default: 1.0.0)")
    args = parser.parse_args()
    build_zip(args.version)
