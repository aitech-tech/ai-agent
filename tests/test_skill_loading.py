"""Test namespaced skill loading — Zoho Books only build."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

EXPECTED_SKILLS = [
    "zoho_books.invoice_review",
    "zoho_books.expense_review",
    "zoho_books.customer_review",
    "zoho_books.vendor_review",
    "zoho_books.tax_review",
    "zoho_books.sales_order_review",
    "zoho_books.purchase_order_review",
    "zoho_books.estimate_review",
    "zoho_books.payment_review",
    "zoho_books.create_invoice",
    "zoho_books.create_customer",
    "zoho_books.create_item_with_gst",
]


def test_reserved_files_not_loaded_as_skills():
    """skill_versions.json and intent_map.json must not be loaded as skills."""
    from agent.skill_executor import SkillExecutor
    executor = SkillExecutor({})
    skill_ids = {s["id"] for s in executor.list_skills()}
    assert "skill_versions" not in skill_ids, "skill_versions loaded as skill!"
    assert "intent_map" not in skill_ids, "intent_map loaded as skill!"
    print("PASS: test_reserved_files_not_loaded_as_skills")


def test_all_12_zoho_books_skills_loaded():
    """All 12 expected zoho_books.* skills must be loaded."""
    from agent.skill_executor import SkillExecutor
    executor = SkillExecutor({})
    skill_ids = list(executor._skills.keys())
    missing = [s for s in EXPECTED_SKILLS if s not in skill_ids]
    assert not missing, f"Missing skills: {missing}. Loaded: {skill_ids}"
    print(f"PASS: test_all_12_zoho_books_skills_loaded ({len(skill_ids)} skills)")


def test_no_crm_skills_loaded():
    """No zoho_crm.* skills should be loaded."""
    from agent.skill_executor import SkillExecutor
    executor = SkillExecutor({})
    crm_skills = [sid for sid in executor._skills if sid.startswith("zoho_crm.")]
    assert not crm_skills, f"CRM skills should not be loaded: {crm_skills}"
    print("PASS: test_no_crm_skills_loaded")


def test_all_skills_are_namespaced():
    """All loaded skills must have a namespaced ID (connector.skill_name)."""
    from agent.skill_executor import SkillExecutor
    executor = SkillExecutor({})
    skills = executor.list_skills()
    if not skills:
        print("SKIP: test_all_skills_are_namespaced (no skills loaded)")
        return
    non_namespaced = [s["id"] for s in skills if "." not in s["id"]]
    assert not non_namespaced, f"Non-namespaced skills found: {non_namespaced}"
    print(f"PASS: test_all_skills_are_namespaced ({len(skills)} skills, all namespaced)")


def test_skill_list_fields():
    """list_skills() must return id, name, display_name, connector for each skill."""
    from agent.skill_executor import SkillExecutor
    executor = SkillExecutor({})
    skills = executor.list_skills()
    assert skills, "No skills loaded"
    for skill in skills:
        assert "id" in skill, f"Skill missing 'id': {skill}"
        assert "name" in skill, f"Skill missing 'name': {skill}"
        assert "display_name" in skill, f"Skill missing 'display_name': {skill}"
        assert "connector" in skill, f"Skill missing 'connector': {skill}"
        assert skill["connector"] == "zoho_books", \
            f"All skills should be zoho_books, got: {skill['connector']}"
    print(f"PASS: test_skill_list_fields ({len(skills)} skills checked)")


def test_no_duplicate_skill_ids():
    """list_skills() must not return duplicate IDs."""
    from agent.skill_executor import SkillExecutor
    executor = SkillExecutor({})
    ids = [s["id"] for s in executor.list_skills()]
    duplicates = [x for x in ids if ids.count(x) > 1]
    assert not duplicates, f"Duplicate skill IDs found: {set(duplicates)}"
    print("PASS: test_no_duplicate_skill_ids")


def test_intent_map_zoho_books_only():
    """intent_map.json must map only to zoho_books.* skills."""
    import json
    intent_path = Path(__file__).parent.parent / "skills" / "intent_map.json"
    data = json.loads(intent_path.read_text(encoding="utf-8"))
    for query, skill_id in data.get("mappings", {}).items():
        assert skill_id.startswith("zoho_books."), \
            f"Intent '{query}' maps to non-books skill: {skill_id}"
    print(f"PASS: test_intent_map_zoho_books_only ({len(data.get('mappings', {}))} mappings)")


if __name__ == "__main__":
    test_reserved_files_not_loaded_as_skills()
    test_all_12_zoho_books_skills_loaded()
    test_no_crm_skills_loaded()
    test_all_skills_are_namespaced()
    test_skill_list_fields()
    test_no_duplicate_skill_ids()
    test_intent_map_zoho_books_only()
    print("\nAll skill loading tests passed.")
