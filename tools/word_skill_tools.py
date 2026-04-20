"""
word_skill_tools.py — MCP tool definitions for the Word skill import system.

Tools:
  import_skill_from_word   — convert a .docx template to client skill JSON
  list_skill_templates     — list available Word templates
  list_client_skills       — list generated client skill JSON files
  validate_client_skill    — validate a generated client skill JSON file
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _importer():
    from skills.word_skill_importer import (
        import_skill_from_word as _import,
        list_skill_templates as _templates,
        list_client_skills as _client_list,
        validate_skill,
        CLIENT_SKILLS_DIR,
    )
    return _import, _templates, _client_list, validate_skill, CLIENT_SKILLS_DIR


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------

def _tool_import_skill_from_word(params: dict) -> dict:
    path = params.get("path") or params.get("filename", "")
    if not path:
        return {"success": False, "error": "Required parameter 'path' or 'filename' not provided."}
    try:
        _import, *_ = _importer()
        result = _import(path)
        return result
    except Exception as e:
        logger.exception("import_skill_from_word failed")
        return {"success": False, "error": str(e)}


def _tool_list_skill_templates(params: dict) -> dict:
    try:
        _, _templates, *_ = _importer()
        templates = _templates()
        return {
            "success": True,
            "count": len(templates),
            "templates": templates,
            "hint": (
                "To import a template, ask: import skill from Word — <filename>"
                if templates else
                "No templates found. Place .docx files in skills/client_docs/zoho_books/"
            ),
        }
    except Exception as e:
        logger.exception("list_skill_templates failed")
        return {"success": False, "error": str(e)}


def _tool_list_client_skills(params: dict) -> dict:
    try:
        _, _, _client_list, *_ = _importer()
        skills = _client_list()
        return {
            "success": True,
            "count": len(skills),
            "client_skills": skills,
            "hint": (
                "Use 'run skill <skill_id>' to execute any skill listed here."
                if skills else
                "No client skills yet. Import a Word template to create one."
            ),
        }
    except Exception as e:
        logger.exception("list_client_skills failed")
        return {"success": False, "error": str(e)}


def _tool_validate_client_skill(params: dict) -> dict:
    skill_id = params.get("skill_id", "").strip()
    if not skill_id:
        return {"success": False, "error": "Required parameter 'skill_id' not provided."}

    try:
        _, _, _, validate_skill, CLIENT_SKILLS_DIR = _importer()

        # Accept "zoho_books.foo" or just "foo"
        name = skill_id.replace("zoho_books.", "")
        skill_path = CLIENT_SKILLS_DIR / f"{name}.json"

        if not skill_path.exists():
            return {"success": False, "error": f"Client skill not found: {skill_id}"}

        skill = json.loads(skill_path.read_text(encoding="utf-8"))
        errors = validate_skill(skill)

        if errors:
            return {
                "success": False,
                "skill_id": f"zoho_books.{name}",
                "valid": False,
                "errors": errors,
            }

        return {
            "success": True,
            "skill_id": f"zoho_books.{name}",
            "valid": True,
            "display_name": skill.get("display_name", name),
            "format": skill.get("format", "unknown"),
            "steps": len(skill.get("steps", [])),
            "approval_required": skill.get("approval_required", False),
        }
    except Exception as e:
        logger.exception("validate_client_skill failed")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# MCP tool definitions
# ---------------------------------------------------------------------------

WORD_SKILL_TOOLS = [
    {
        "name": "import_skill_from_word",
        "description": (
            "Convert a Word (.docx) skill template into a validated client skill JSON file. "
            "Accepts a full file path or just the filename from skills/client_docs/zoho_books/. "
            "Supports both simple business-language templates and advanced table-based templates. "
            "The generated skill loads as zoho_books.<skill_id> and can be run immediately."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Full file path or filename of the .docx template (e.g. 'my_skill.docx' or 'C:/path/to/my_skill.docx')",
                },
            },
            "required": ["path"],
        },
        "fn": _tool_import_skill_from_word,
    },
    {
        "name": "list_skill_templates",
        "description": (
            "List all Word (.docx) skill templates available in skills/client_docs/zoho_books/. "
            "Returns filename, display name, and file size for each template."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "fn": _tool_list_skill_templates,
    },
    {
        "name": "list_client_skills",
        "description": (
            "List all client skill JSON files generated from Word templates. "
            "Shows skill ID, display name, description, format (simple/advanced), "
            "step count, and whether approval is required before running."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "fn": _tool_list_client_skills,
    },
    {
        "name": "validate_client_skill",
        "description": (
            "Validate a generated client skill JSON file against the skill schema. "
            "Checks for required fields, valid tool names, and blocked delete tools. "
            "Use this after importing a Word template to confirm it is ready to run."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "skill_id": {
                    "type": "string",
                    "description": "Skill ID to validate, e.g. 'zoho_books.my_skill' or just 'my_skill'",
                },
            },
            "required": ["skill_id"],
        },
        "fn": _tool_validate_client_skill,
    },
]
