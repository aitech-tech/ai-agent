"""
Regression tests for skill failure propagation.

Covers the bug where execute_skill / run_skill_by_intent returned success:true
even when the underlying tool returned {"success": false}.
All skills use zoho_books.* namespace.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.skill_executor import SkillExecutor, SkillError


def _failing_tool(params: dict) -> dict:
    return {"success": False, "error": "tool_not_mapped", "message": "Test failing tool"}


def _ok_tool(params: dict) -> dict:
    return {"success": True, "data": [{"id": "1", "name": "Test"}]}


def _make_executor(tools: dict) -> SkillExecutor:
    ex = SkillExecutor(tools)
    ex._skills.clear()
    return ex


def _inject_skill(executor: SkillExecutor, skill_id: str, skill: dict) -> None:
    executor._skills[skill_id] = skill


# ---------------------------------------------------------------------------
# A. Skill failure propagation — on_error: stop (default)
# ---------------------------------------------------------------------------

def test_failing_tool_fails_skill():
    """A tool returning success:false must cause execute_skill to raise SkillError."""
    executor = _make_executor({"failing_tool": _failing_tool})
    _inject_skill(executor, "zoho_books.test_skill", {
        "name": "test_skill",
        "version": "1.0",
        "steps": [
            {"step_name": "fetch", "tool": "failing_tool", "params": {}}
        ]
    })

    raised = False
    try:
        executor.execute_skill("zoho_books.test_skill")
    except SkillError as e:
        raised = True
        assert "tool_not_mapped" in str(e), f"Error should mention tool_not_mapped, got: {e}"

    assert raised, "SkillError should have been raised when tool returns success:false"
    print("PASS: test_failing_tool_fails_skill")


def test_failing_tool_step_marked_as_error():
    """Failed step must be recorded as status:error, not status:ok."""
    executor = _make_executor({"failing_tool": _failing_tool, "ok_tool": _ok_tool})
    _inject_skill(executor, "zoho_books.two_step", {
        "name": "two_step",
        "version": "1.0",
        "steps": [
            {"step_name": "fetch", "tool": "failing_tool", "params": {}, "on_error": "continue"},
            {"step_name": "process", "tool": "ok_tool", "params": {}},
        ]
    })

    result = executor.execute_skill("zoho_books.two_step")
    step_result = result["results"]["fetch"]
    assert step_result["status"] == "error", \
        f"Failed step should have status:error, got: {step_result['status']}"
    assert result["status"] == "completed", "Skill should complete when on_error:continue"
    print("PASS: test_failing_tool_step_marked_as_error")


# ---------------------------------------------------------------------------
# B. on_error: continue
# ---------------------------------------------------------------------------

def test_on_error_continue_allows_skill_to_proceed():
    """With on_error:continue, skill runs subsequent steps and returns completed."""
    executor = _make_executor({"failing_tool": _failing_tool, "ok_tool": _ok_tool})
    _inject_skill(executor, "zoho_books.resilient", {
        "name": "resilient",
        "version": "1.0",
        "steps": [
            {"step_name": "step1", "tool": "failing_tool", "params": {}, "on_error": "continue"},
            {"step_name": "step2", "tool": "ok_tool", "params": {}},
        ]
    })

    result = executor.execute_skill("zoho_books.resilient")
    assert result["status"] == "completed"
    assert result["results"]["step1"]["status"] == "error"
    assert result["results"]["step2"]["status"] == "ok"
    print("PASS: test_on_error_continue_allows_skill_to_proceed")


def test_on_error_stop_halts_skill():
    """With on_error:stop (default), skill must halt and raise on the first failure."""
    executor = _make_executor({"failing_tool": _failing_tool, "ok_tool": _ok_tool})
    _inject_skill(executor, "zoho_books.strict", {
        "name": "strict",
        "version": "1.0",
        "steps": [
            {"step_name": "step1", "tool": "failing_tool", "params": {}},
            {"step_name": "step2", "tool": "ok_tool", "params": {}},
        ]
    })

    raised = False
    try:
        executor.execute_skill("zoho_books.strict")
    except SkillError:
        raised = True

    assert raised, "SkillError must be raised when on_error:stop and tool fails"
    print("PASS: test_on_error_stop_halts_skill")


# ---------------------------------------------------------------------------
# C. Skill list quality
# ---------------------------------------------------------------------------

def test_no_duplicate_skill_ids():
    """Default-loaded skills should have unique IDs."""
    executor = SkillExecutor({})
    ids = [s["id"] for s in executor.list_skills()]
    duplicates = [x for x in ids if ids.count(x) > 1]
    assert not duplicates, f"Duplicate skill IDs found: {set(duplicates)}"
    print("PASS: test_no_duplicate_skill_ids")


def test_all_default_skills_are_namespaced():
    """All loaded skills must have namespaced IDs (zoho_books.skill_name)."""
    executor = SkillExecutor({})
    skills = executor.list_skills()
    if not skills:
        print("SKIP: test_all_default_skills_are_namespaced (no skills loaded)")
        return
    non_namespaced = [s["id"] for s in skills if "." not in s["id"]]
    assert not non_namespaced, f"Non-namespaced skills found: {non_namespaced}"
    print(f"PASS: test_all_default_skills_are_namespaced ({len(skills)} skills, all namespaced)")


def test_list_skills_has_id_and_display_name():
    """Each skill entry must have id, name, display_name, connector fields."""
    executor = SkillExecutor({})
    _inject_skill(executor, "zoho_books.invoice_review_test", {
        "name": "invoice_review_test",
        "description": "Test invoice review",
        "version": "1.0",
        "steps": []
    })
    skills = executor.list_skills()
    entry = next((s for s in skills if s["id"] == "zoho_books.invoice_review_test"), None)
    assert entry is not None, "zoho_books.invoice_review_test not found in list_skills"
    assert entry["id"] == "zoho_books.invoice_review_test"
    assert entry["name"] == "zoho_books.invoice_review_test"
    assert "display_name" in entry, "display_name field missing"
    assert entry["connector"] == "zoho_books"
    print(f"PASS: test_list_skills_has_id_and_display_name (display_name={entry['display_name']})")


# ---------------------------------------------------------------------------
# D. Intent routing
# ---------------------------------------------------------------------------

def test_intent_routing_fails_honestly_on_tool_failure():
    """run_skill_by_intent must return success:false when tool returns success:false."""
    from tools.skill_tools import set_executor, run_skill_by_intent

    executor = _make_executor({"zoho_books_list_invoices": _failing_tool})
    _inject_skill(executor, "zoho_books.invoice_review", {
        "name": "invoice_review",
        "version": "2.0",
        "steps": [
            {"step_name": "fetch_invoices", "tool": "zoho_books_list_invoices", "params": {"limit": 20}}
        ]
    })
    executor._intent_map = {"show invoices": "zoho_books.invoice_review"}

    set_executor(executor)
    result = run_skill_by_intent({"query": "show invoices"})

    assert result.get("success") is False, \
        f"Expected success:false when underlying tool fails, got: {result}"
    error = result.get("error", "")
    assert "tool_not_mapped" in error or "failed" in error.lower(), \
        f"Error message not descriptive enough: {result}"
    print("PASS: test_intent_routing_fails_honestly_on_tool_failure")


if __name__ == "__main__":
    test_failing_tool_fails_skill()
    test_failing_tool_step_marked_as_error()
    test_on_error_continue_allows_skill_to_proceed()
    test_on_error_stop_halts_skill()
    test_no_duplicate_skill_ids()
    test_all_default_skills_are_namespaced()
    test_list_skills_has_id_and_display_name()
    test_intent_routing_fails_honestly_on_tool_failure()
    print("\nAll skill failure regression tests passed.")
