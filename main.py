"""
ReckLabs AI Agent — MCP server entry point (Zoho Books build v1.3.0).

Architecture:
  - Tools: Zoho Books tools (51) + Skill tools + Health tools + Platform tools
  - Skills: 2-layer system (base encrypted + client customisation)
  - Connector: zoho_books (direct API, India endpoint, zoho.in)
  - Tool mode: customer (router + CUD only) | developer (all 91 tools)

Configure Claude Desktop to launch this via the MCP config.
See docs/claude-desktop-production-setup.md for setup guide.
"""
import io
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Force UTF-8 on stdin/stdout — Windows defaults to cp1252 which cannot
# encode Unicode characters like ₹, breaking MCP JSON-RPC parsing.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")

from config.settings import (
    ensure_storage, load_selected_connectors,
    RECKLABS_TOOL_MODE, filter_connector_tools,
)
from agent.mcp_server import MCPServer
from agent.skill_executor import SkillExecutor
from tools.skill_tools import SKILL_TOOLS, set_executor
from tools.health_tools import HEALTH_TOOLS
from tools.platform_tools import PLATFORM_TOOLS
from tools.word_skill_tools import WORD_SKILL_TOOLS

LOG_FILE = Path(__file__).parent / "storage" / "agent.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8")],
)
logger = logging.getLogger(__name__)


def build_tool_registry(all_tools: list[dict]) -> dict:
    return {t["name"]: t["fn"] for t in all_tools}


def dedupe_tools(all_tools: list[dict]) -> list[dict]:
    """Return one tool per name, keeping the last definition for duplicates."""
    by_name = {}
    for tool in all_tools:
        by_name[tool["name"]] = tool
    return list(by_name.values())


def _load_connector_tools(selected: list[str]) -> list[dict]:
    """Return tools for selected connectors, filtered by RECKLABS_TOOL_MODE."""
    connector_tools = []
    for name in selected:
        if name == "zoho_books":
            from connectors.zoho_books.tools import ZOHO_BOOKS_TOOLS
            from products.script_loader import load_product_tools
            product_tools = load_product_tools("zoho_books")
            all_raw = list(ZOHO_BOOKS_TOOLS) + list(product_tools)
            filtered = filter_connector_tools(all_raw, RECKLABS_TOOL_MODE)
            connector_tools.extend(filtered)
            logger.info(
                "Loaded tools: zoho_books mode=%s (%d raw tools, %d report scripts → %d exposed)",
                RECKLABS_TOOL_MODE, len(ZOHO_BOOKS_TOOLS), len(product_tools), len(filtered),
            )
        else:
            logger.warning("Connector '%s' selected but not available in this build — skipping", name)
    return connector_tools


def main():
    ensure_storage()
    logger.info("Starting ReckLabs AI Agent v1.3.0 (Zoho Books build, mode=%s)", RECKLABS_TOOL_MODE)

    selected = load_selected_connectors()
    logger.info("Selected connectors: %s", selected)

    connector_tools = _load_connector_tools(selected)

    # In customer mode add router tools; developer mode uses zb_* scripts directly
    if RECKLABS_TOOL_MODE == "customer":
        from tools.zoho_router_tools import ROUTER_TOOLS
        extra_tools = ROUTER_TOOLS
    else:
        extra_tools = []

    all_tools = dedupe_tools(
        connector_tools + extra_tools + SKILL_TOOLS + HEALTH_TOOLS + PLATFORM_TOOLS + WORD_SKILL_TOOLS
    )

    tool_registry = build_tool_registry(all_tools)
    executor = SkillExecutor(tool_registry)
    set_executor(executor)

    server = MCPServer()
    server.register_tools(all_tools)

    logger.info(
        "Platform ready — %d tools registered (%s connector(s) active)",
        len(all_tools),
        ", ".join(selected),
    )

    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("Agent stopped by user")
    except Exception as e:
        logger.exception("Agent crashed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
