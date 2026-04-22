"""
Script loader — discovers and registers product report scripts as MCP tools.

Call load_product_tools("zoho_books") to get a list of MCP-ready tool dicts
for all validated scripts in products/zoho_books/.
"""
import importlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_product_tools(product_name: str) -> list[dict]:
    """
    Import every .py file in products/<product_name>/ (skipping _* and __init__),
    validate each as a report script, and return a sorted list of MCP tool dicts.
    """
    pkg_name = f"products.{product_name}"
    try:
        pkg = importlib.import_module(pkg_name)
    except ImportError as e:
        logger.error("Cannot import product package '%s': %s", pkg_name, e)
        return []

    pkg_dir = Path(pkg.__file__).parent
    tools: list[dict] = []

    for py_file in sorted(pkg_dir.glob("*.py")):
        stem = py_file.stem
        if stem.startswith("_"):
            continue

        module_name = f"{pkg_name}.{stem}"
        try:
            module = importlib.import_module(module_name)
        except Exception as e:
            logger.warning("Skipping '%s': import error: %s", module_name, e)
            continue

        tool_name = getattr(module, "TOOL_NAME", None)
        tool_desc = getattr(module, "TOOL_DESCRIPTION", None)
        run_fn = getattr(module, "run", None)

        if not tool_name:
            logger.warning("Skipping '%s': missing TOOL_NAME", module_name)
            continue
        if not tool_desc:
            logger.warning("Skipping '%s': missing TOOL_DESCRIPTION", module_name)
            continue
        if not callable(run_fn):
            logger.warning("Skipping '%s': 'run' is not callable", module_name)
            continue
        if not str(tool_name).startswith("zb_"):
            logger.warning(
                "Skipping '%s': TOOL_NAME '%s' does not start with zb_",
                module_name, tool_name,
            )
            continue

        tool_params = getattr(module, "TOOL_PARAMS", {})
        tools.append({
            "name": tool_name,
            "description": tool_desc,
            "input_schema": {
                "type": "object",
                "properties": tool_params,
                "required": [],
            },
            "fn": make_safe_fn(tool_name, run_fn),
        })
        logger.debug("Loaded product tool: %s", tool_name)

    tools.sort(key=lambda t: t["name"])
    return tools


def make_safe_fn(tool_name: str, run_fn):
    """
    Wrap a script's run() function so that exceptions and non-dict returns
    are converted to a standard error response instead of crashing the server.
    """
    def _fn(params: dict) -> dict:
        try:
            result = run_fn(params or {})
        except Exception as e:
            logger.exception("Error in product tool '%s'", tool_name)
            return {
                "success": False,
                "tool": tool_name,
                "error": "script_exception",
                "message": str(e),
                "raw_data_returned": False,
            }

        if not isinstance(result, dict):
            logger.error("Product tool '%s' returned non-dict: %r", tool_name, result)
            return {
                "success": False,
                "tool": tool_name,
                "error": "invalid_script_result",
                "message": "Script returned a non-dict result",
                "raw_data_returned": False,
            }

        result.setdefault("success", True)
        result.setdefault("tool", tool_name)
        return result

    _fn.__name__ = f"safe_{tool_name}"
    return _fn


def load_manifest(product_name: str) -> dict:
    """Read products/<product_name>/manifest.json. Returns {} if missing or invalid."""
    try:
        pkg = importlib.import_module(f"products.{product_name}")
        manifest_path = Path(pkg.__file__).parent / "manifest.json"
        if manifest_path.exists():
            return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Could not load manifest for '%s': %s", product_name, e)
    return {}
