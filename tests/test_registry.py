"""Regression tests for connector registry — Zoho Books only build."""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def _fresh_registry():
    from registry.connector_registry import ConnectorRegistry, _register_defaults
    reg = ConnectorRegistry.__new__(ConnectorRegistry)
    reg._classes = {}
    reg._instances = {}
    reg._versions = {}
    _register_defaults(reg)
    return reg


def test_only_zoho_books_registered():
    """Default registry must contain only zoho_books."""
    reg = _fresh_registry()
    connectors = reg.list_connectors()
    assert connectors == ["zoho_books"], \
        f"Expected ['zoho_books'] only, got: {connectors}"
    print(f"PASS: test_only_zoho_books_registered ({connectors})")


def test_zoho_crm_not_registered():
    """zoho_crm must NOT be registered in this build."""
    reg = _fresh_registry()
    connectors = reg.list_connectors()
    assert "zoho_crm" not in connectors, \
        f"zoho_crm should not be registered. Got: {connectors}"
    print("PASS: test_zoho_crm_not_registered")


def test_legacy_zoho_not_registered():
    """Legacy merged 'zoho' connector must NOT be registered."""
    os.environ.pop("RECKLABS_ENABLE_LEGACY_ZOHO_CONNECTOR", None)
    reg = _fresh_registry()
    connectors = reg.list_connectors()
    assert "zoho" not in connectors, \
        f"'zoho' should not be registered. Got: {connectors}"
    print("PASS: test_legacy_zoho_not_registered")


def test_zoho_books_connector_class_loads():
    """ZohoBooksConnector class must load and instantiate without errors."""
    from connectors.zoho_books.connector import ZohoBooksConnector
    conn = ZohoBooksConnector(config={})
    assert conn.name == "zoho_books"
    assert hasattr(conn, "_mode") is False  # v1.2.0 has no _mode attr
    assert conn._api_base == "https://www.zohoapis.in/books/v3"
    print("PASS: test_zoho_books_connector_class_loads")


def test_zoho_books_connector_health_check():
    """ZohoBooksConnector.health_check() must return connector=zoho_books."""
    from connectors.zoho_books.connector import ZohoBooksConnector
    conn = ZohoBooksConnector(config={})
    health = conn.health_check()
    assert health["connector"] == "zoho_books"
    assert health["mode"] == "direct_api"
    assert health["status"] == "unauthenticated"
    print(f"PASS: test_zoho_books_connector_health_check ({health})")


def test_catalog_contains_zoho_books_as_available():
    """CONNECTOR_CATALOG must list zoho_books as 'available'."""
    from registry.connector_registry import CONNECTOR_CATALOG
    assert "zoho_books" in CONNECTOR_CATALOG
    assert CONNECTOR_CATALOG["zoho_books"]["status"] == "available"
    print("PASS: test_catalog_contains_zoho_books_as_available")


def test_catalog_lists_zoho_crm_as_coming_soon():
    """CONNECTOR_CATALOG must list zoho_crm as 'coming_soon' (not active)."""
    from registry.connector_registry import CONNECTOR_CATALOG
    assert "zoho_crm" in CONNECTOR_CATALOG
    assert CONNECTOR_CATALOG["zoho_crm"]["status"] == "coming_soon"
    print("PASS: test_catalog_lists_zoho_crm_as_coming_soon")


def test_registry_get_zoho_books():
    """registry.get('zoho_books') must return a ZohoBooksConnector instance."""
    from registry.connector_registry import registry
    from connectors.zoho_books.connector import ZohoBooksConnector
    conn = registry.get("zoho_books")
    assert isinstance(conn, ZohoBooksConnector)
    print("PASS: test_registry_get_zoho_books")


if __name__ == "__main__":
    test_only_zoho_books_registered()
    test_zoho_crm_not_registered()
    test_legacy_zoho_not_registered()
    test_zoho_books_connector_class_loads()
    test_zoho_books_connector_health_check()
    test_catalog_contains_zoho_books_as_available()
    test_catalog_lists_zoho_crm_as_coming_soon()
    test_registry_get_zoho_books()
    print("\nAll registry tests passed.")
