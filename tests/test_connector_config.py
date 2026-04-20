"""Test connector config loading and Zoho Books v1.2.0 defaults."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_default_config_is_zoho_books_only():
    """Default connector_config.json must select only zoho_books."""
    import json
    cfg_path = Path(__file__).parent.parent / "config" / "connector_config.json"
    assert cfg_path.exists(), f"connector_config.json not found at {cfg_path}"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    selected = cfg.get("selected_connectors", [])
    assert selected == ["zoho_books"], f"Expected ['zoho_books'], got {selected}"
    assert cfg.get("version") == "1.2.0", f"Expected version 1.2.0, got {cfg.get('version')}"
    print("PASS: test_default_config_is_zoho_books_only")


def test_zoho_books_config_is_direct_api():
    """connector_config.json must set mode=direct_api for zoho_books."""
    import json
    cfg_path = Path(__file__).parent.parent / "config" / "connector_config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    books_cfg = cfg.get("connectors", {}).get("zoho_books", {})
    assert books_cfg.get("mode") == "direct_api", \
        f"zoho_books mode should be direct_api, got: {books_cfg.get('mode')}"
    assert books_cfg.get("enabled") is True, "zoho_books must be enabled"
    print("PASS: test_zoho_books_config_is_direct_api")


def test_zoho_books_standards_present():
    """connector_config.json must include Indian accounting standards."""
    import json
    cfg_path = Path(__file__).parent.parent / "config" / "connector_config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    standards = cfg.get("connectors", {}).get("zoho_books", {}).get("standards", {})
    assert standards.get("currency") == "INR", f"currency should be INR, got {standards.get('currency')}"
    assert standards.get("country") == "IN", f"country should be IN, got {standards.get('country')}"
    assert standards.get("default_gst_rate") == 18, \
        f"default_gst_rate should be 18, got {standards.get('default_gst_rate')}"
    print(f"PASS: test_zoho_books_standards_present (standards: {standards})")


def test_load_selected_connectors_returns_zoho_books():
    """load_selected_connectors() must return ['zoho_books'] from default config."""
    import config.settings as settings
    result = settings.load_selected_connectors()
    assert result == ["zoho_books"], f"Expected ['zoho_books'], got {result}"
    print(f"PASS: test_load_selected_connectors_returns_zoho_books ({result})")


def test_migration_legacy_zoho_to_books():
    """Legacy 'zoho' config entry must migrate to 'zoho_books' only."""
    import json, tempfile, os
    old_config = json.dumps({"selected_connectors": ["zoho"]})
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(old_config)
        tmp = f.name
    try:
        import config.settings as settings
        orig = settings.CONNECTOR_CONFIG_FILE
        settings.CONNECTOR_CONFIG_FILE = Path(tmp)
        result = settings.load_selected_connectors()
        settings.CONNECTOR_CONFIG_FILE = orig
        assert "zoho_books" in result, f"Expected zoho_books in {result}"
        assert "zoho_crm" not in result, f"zoho_crm should not appear, got {result}"
        assert "zoho" not in result, f"'zoho' should be replaced, got {result}"
        print(f"PASS: test_migration_legacy_zoho_to_books ({result})")
    finally:
        os.unlink(tmp)


def test_zoho_crm_skipped_in_load():
    """If zoho_crm appears in config, it must be skipped (not active in this build)."""
    import json, tempfile, os
    cfg = json.dumps({"version": "1.1.0", "selected_connectors": ["zoho_crm", "zoho_books"]})
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(cfg)
        tmp = f.name
    try:
        import config.settings as settings
        orig = settings.CONNECTOR_CONFIG_FILE
        settings.CONNECTOR_CONFIG_FILE = Path(tmp)
        result = settings.load_selected_connectors()
        settings.CONNECTOR_CONFIG_FILE = orig
        assert "zoho_crm" not in result, f"zoho_crm should be skipped, got {result}"
        assert "zoho_books" in result, f"zoho_books should remain, got {result}"
        print(f"PASS: test_zoho_crm_skipped_in_load ({result})")
    finally:
        os.unlink(tmp)


if __name__ == "__main__":
    test_default_config_is_zoho_books_only()
    test_zoho_books_config_is_direct_api()
    test_zoho_books_standards_present()
    test_load_selected_connectors_returns_zoho_books()
    test_migration_legacy_zoho_to_books()
    test_zoho_crm_skipped_in_load()
    print("\nAll connector config tests passed.")
