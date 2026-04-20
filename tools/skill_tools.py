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


def import_skill_from_word(params: dict) -> dict:
    """
    Import a user-edited Word skill template into validated client JSON.
    Params: {path: str, connector: str}
    """
    path = params.get("path") or params.get("docx_path")
    connector = params.get("connector", "zoho_books")
    if not path:
        return {"success": False, "error": "missing_param", "message": "'path' parameter required"}
    try:
        from skills.word_skill_importer import import_skill_from_word as _import
        result = _import(path, connector=connector)
        if _executor:
            result["loaded_skills"] = _executor.reload()
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_skill_templates(params: dict) -> dict:
    """List editable Word skill templates for a connector."""
    connector = params.get("connector", "zoho_books")
    try:
        from skills.word_skill_importer import list_skill_templates as _list
        return {"success": True, "data": _list(connector=connector)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_client_skills(params: dict) -> dict:
    """List generated client skill JSON files for a connector."""
    connector = params.get("connector", "zoho_books")
    try:
        from skills.word_skill_importer import list_client_skill_files
        return {"success": True, "data": list_client_skill_files(connector=connector)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def validate_client_skill(params: dict) -> dict:
    """Validate a generated client skill JSON file without executing it."""
    path = params.get("path") or params.get("json_path")
    if not path:
        return {"success": False, "error": "missing_param", "message": "'path' parameter required"}
    try:
        import json
        from pathlib import Path
        from skills.word_skill_importer import validate_skill_json

        data = json.loads(Path(path).read_text(encoding="utf-8"))
        validation = validate_skill_json(data)
        return {"success": validation["valid"], "data": validation}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_skill_by_intent(params: dict) -> dict:
    """
    Match a natural language query to a skill via the intent map, then execute it.
    Params: {query: str, context: dict}
    """
    if not _executor:
        return {"success": False, "error": "skill_executor_not_initialized"}
    query = params.get("query", "").strip()
    if not query:
        return {"success": False, "error": "missing_param", "message": "'query' parameter required"}
    skill_name = _executor.resolve_intent(query)
    if not skill_name:
        return {
            "success": False,
            "error": "no_intent_match",
            "message": (
                f"No skill matched '{query}'. "
                "Try: 'show leads', 'enrich contacts', 'pipeline review', etc."
            ),
        }
    context = params.get("context", {})
    try:
        result = _executor.execute_skill(skill_name, context)
        return {"success": True, "matched_skill": skill_name, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


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
    {
        "name": "import_skill_from_word",
        "description": (
            "Convert a user-edited Word .docx skill template into validated client skill JSON. "
            "Generated JSON is saved under skills/client/zoho_books/ and reloaded as zoho_books.<skill_id>."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the .docx skill template"},
                "connector": {
                    "type": "string",
                    "description": "Connector namespace. Default: zoho_books",
                    "default": "zoho_books",
                },
            },
            "required": ["path"],
        },
        "fn": import_skill_from_word,
    },
    {
        "name": "list_skill_templates",
        "description": "List editable Word .docx skill templates available for client customization.",
        "input_schema": {
            "type": "object",
            "properties": {
                "connector": {
                    "type": "string",
                    "description": "Connector namespace. Default: zoho_books",
                    "default": "zoho_books",
                },
            },
            "required": [],
        },
        "fn": list_skill_templates,
    },
    {
        "name": "list_client_skills",
        "description": "List generated client skill JSON files and validation status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "connector": {
                    "type": "string",
                    "description": "Connector namespace. Default: zoho_books",
                    "default": "zoho_books",
                },
            },
            "required": [],
        },
        "fn": list_client_skills,
    },
    {
        "name": "validate_client_skill",
        "description": "Validate a generated client skill JSON file before Claude runs it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the generated client skill JSON file"},
            },
            "required": ["path"],
        },
        "fn": validate_client_skill,
    },
    {
        "name": "run_skill_by_intent",
        "description": (
            "Match a natural language query to a skill and execute it. "
            "Example queries: 'show leads', 'enrich contacts', 'pipeline review', 'analyze pipeline'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query, e.g. 'show leads' or 'pipeline review'",
                },
                "context": {
                    "type": "object",
                    "description": "Optional input values passed to skill steps",
                    "default": {},
                },
            },
            "required": ["query"],
        },
        "fn": run_skill_by_intent,
    },
]
