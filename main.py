"""
ReckLabs AI Agent — MCP server entry point (Phase 1).

Architecture:
  - Tools layer: Zoho CRM tools + Skill tools + Health tools + Platform tools
  - Skills layer: 2-layer system (base encrypted + client customisation)
  - Connectors layer: Registry with versioning + full catalog
  - License layer: Tier-based access management

Configure Claude Desktop to launch this via the MCP config.
See installer/install.bat for one-click setup.
"""
import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path so all imports resolve
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import ensure_storage
from agent.mcp_server import MCPServer
from agent.skill_executor import SkillExecutor
from tools.zoho_tools import ZOHO_TOOLS
from tools.skill_tools import SKILL_TOOLS, set_executor
from tools.health_tools import HEALTH_TOOLS
from tools.platform_tools import PLATFORM_TOOLS

# ------------------------------------------------------------------
# Logging — file only; stdout is reserved for MCP JSON-RPC protocol
# ------------------------------------------------------------------
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


def main():
    ensure_storage()
    logger.info("Starting ReckLabs AI Agent v1.0.0 (Phase 1)")

    # Collect all tool definitions
    all_tools = ZOHO_TOOLS + SKILL_TOOLS + HEALTH_TOOLS + PLATFORM_TOOLS

    # Wire skill executor (skills call tools by name)
    tool_registry = build_tool_registry(all_tools)
    executor = SkillExecutor(tool_registry)
    set_executor(executor)

    # Build and start MCP server
    server = MCPServer()
    server.register_tools(all_tools)

    logger.info(
        "Platform ready — %d tools registered across %d modules",
        len(all_tools),
        4,  # zoho, skill, health, platform
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
