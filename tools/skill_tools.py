"""
Skill MCP tools — expose the skills system as callable MCP tools.
"""
import logging

logger = logging.getLogger(__name__)

# The executor is injected at server startup to avoid circular imports
_executor = None


def set_executor(executor) -> None:
    global _executor
    _executor = executor


def list_skills(params: dict) -> dict:
    """List all available skills."""
    if not _executor:
        return {"success": False, "error": "skill_executor_not_initialized"}
    return {"success": True, "data": _executor.list_skills()}


def run_skill(params: dict) -> dict:
    """
    Execute a named skill.
    Params: {name: str, context: dict}
    """
    if not _executor:
        return {"success": False, "error": "skill_executor_not_initialized"}
    name = params.get("name")
    if not name:
        return {"success": False, "error": "missing_param", "message": "'name' parameter required"}
    context = params.get("context", {})
    try:
        result = _executor.execute_skill(name, context)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def reload_skills(params: dict) -> dict:
    """Reload all skill definitions from disk."""
    if not _executor:
        return {"success": False, "error": "skill_executor_not_initialized"}
    loaded = _executor.reload()
    return {"success": True, "data": {"loaded_skills": loaded}}


SKILL_TOOLS = [
    {
        "name": "list_skills",
        "description": "List all available workflow skills that can be executed.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "fn": list_skills,
    },
    {
        "name": "run_skill",
        "description": "Execute a workflow skill by name. Skills chain multiple connector operations together.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the skill to execute"},
                "context": {
                    "type": "object",
                    "description": "Optional input values for the skill steps",
                    "default": {},
                },
            },
            "required": ["name"],
        },
        "fn": run_skill,
    },
    {
        "name": "reload_skills",
        "description": "Reload skill definitions from disk (useful after adding new skills).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "fn": reload_skills,
    },
]
