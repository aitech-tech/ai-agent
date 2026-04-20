"""Generate a PDF of the full session context document."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Preformatted,
    Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

OUTPUT = "a:/ReckLabs/code/ai-agent/dist/recklabs-agent-session-context.pdf"

CONTENT = [
    ("h1", "ReckLabs AI Agent — Full Session Context"),
    ("meta", "Generated: 2026-04-20  |  Model: claude-sonnet-4-6  |  Project: a:/ReckLabs/code/ai-agent/"),

    ("h2", "Project Overview"),
    ("body", "ReckLabs AI Agent is a Phase 1 MVP local MCP (Model Context Protocol) agent that bridges Claude Desktop to business connectors (Zoho CRM, Zoho Books, etc.). End users are non-technical — they download an installer, run it, open Claude Desktop, and use natural language to interact with their business data."),
    ("body", "Key product constraint: Zoho's official MCP endpoint is not yet documented/released. Until it is, all connectors must default to legacy_direct_api mode. The official_mcp mode is stubbed out and returns not_ready errors."),

    ("h2", "Architecture"),
    ("code", """\
Claude Desktop (LLM)
      ↓ MCP stdio (JSON-RPC 2.0)
  agent/mcp_server.py         ← MCP server entry point
      ↓
  tools/                      ← MCP tool handlers
      ↓
  agent/skill_executor.py     ← Executes skill JSON files as multi-step workflows
      ↓
  connectors/zoho_crm/        ← Connector implementation
  connectors/zoho_books/
      ↓
  legacy_direct_api           ← Working demo mode (HTTP API directly)
  official_mcp (stub)         ← Future mode, returns not_ready"""),
    ("body", "Skill system: Skills are JSON files in skills/base/<connector>/*.json (base, some encrypted .json.enc) and skills/client/<connector>/*.json (client overrides). Skills are registered with namespaced IDs like zoho_crm.lead_generation."),
    ("body", "Registry: registry/connector_registry.py — singleton that holds connector classes. zoho_crm and zoho_books are registered by default. The old merged zoho connector is hidden behind env var RECKLABS_ENABLE_LEGACY_ZOHO_CONNECTOR=1."),

    ("h2", "Session Work Completed"),
    ("body", "This session implemented a 10-finding code review. All fixes are applied and all tests pass."),

    ("h3", "Finding 1 (P0) — Installer wrote mode: official_mcp by default"),
    ("body", "Problem: Fresh install produced connector_config.json with mode: official_mcp and mcp_url: null, breaking the agent immediately on first run."),
    ("body", "Fix — config/connector_config.json:"),
    ("code", """\
{
  "_comment": "official_mcp is the target production backend. legacy_direct_api
               is the demo/default until automated Zoho MCP provisioning is
               implemented.",
  "version": "1.1.0",
  "selected_connectors": ["zoho_crm", "zoho_books"],
  "connectors": {
    "zoho_crm": {
      "mode": "legacy_direct_api",
      "enabled": true,
      "official_mcp": {
        "provisioning": "recklabs_managed",
        "mcp_url": null,
        "status": "not_ready"
      },
      "fallback_mode": "legacy_direct_api"
    },
    "zoho_books": {
      "mode": "legacy_direct_api",
      "enabled": true,
      "official_mcp": {
        "provisioning": "recklabs_managed",
        "mcp_url": null,
        "status": "not_ready"
      },
      "fallback_mode": "legacy_direct_api"
    }
  }
}"""),
    ("body", "Fix — connectors/zoho_crm/connector.py and connectors/zoho_books/connector.py:"),
    ("code", 'self._mode = self.config.get("mode", "legacy_direct_api")  # was "official_mcp"'),
    ("body", "Fix — installer/install.bat Python one-liner updated to write legacy_direct_api and status: not_ready for each selected connector."),

    ("h3", "Finding 2 (P0) — execute_skill() masked tool failures as success"),
    ("body", "Problem: When a tool returned {\"success\": false}, execute_skill() recorded it as status: ok and the skill returned success: true. run_skill_by_intent(\"show leads\") returned success: true even when all data fetching failed."),
    ("body", "Fix — agent/skill_executor.py (inside the step execution loop):"),
    ("code", """\
# Treat explicit success:false from the tool as a step failure
if isinstance(output, dict) and output.get("success") is False:
    err_msg = output.get("error", "tool_failure")
    results[step_name] = {"status": "error", "output": output}
    step_outputs[step_name] = output
    logger.warning(
        "Skill '%s' step '%s' tool returned success:false — %s",
        name, step_name, err_msg
    )
    if on_error != "continue":
        raise SkillError(
            f"Skill '{name}' failed at step '{step_name}': {err_msg}"
        )
    continue"""),

    ("h3", "Finding 3 (P1) — Flat and namespaced skills both loaded, causing duplicates"),
    ("body", "Problem: _load_all() loaded both flat skills (e.g., lead_generation) and namespaced skills (e.g., zoho_crm.lead_generation), resulting in duplicate IDs in list_skills()."),
    ("body", "Fix — _load_all() rewritten: primary path is namespaced connector dir scanning (skills/base/<connector>/*.json[.enc]). Legacy flat loading moved to bottom, gated behind RECKLABS_ENABLE_LEGACY_FLAT_SKILLS=1."),
    ("code", """\
def _load_all(self) -> None:
    # Primary: namespaced connector skills
    if SKILLS_BASE_DIR.exists():
        for connector_dir in SKILLS_BASE_DIR.iterdir():
            if connector_dir.is_dir():
                connector_name = connector_dir.name
                connector_names: set[str] = set()
                for f in connector_dir.iterdir():
                    if f.is_file():
                        if f.name.endswith(".json.enc"):
                            connector_names.add(f.name[:-9])
                        elif f.suffix == ".json" and f.stem not in RESERVED_SKILL_FILES:
                            connector_names.add(f.stem)
                for skill_name in connector_names:
                    self._load_connector_skill(connector_name, skill_name)

    # Legacy flat loading — disabled by default
    if os.environ.get("RECKLABS_ENABLE_LEGACY_FLAT_SKILLS") == "1":
        logger.warning("Legacy flat skill loading enabled")
        # ... scans flat dirs and calls self._load_skill(name)"""),

    ("h3", "Finding 4 (P1) — list_skills() exposed internal names, not namespaced IDs"),
    ("body", "Problem: list_skills() returned the raw skill name field (e.g., lead_generation) instead of the registry key (zoho_crm.lead_generation)."),
    ("body", "Fix — list_skills() rewritten:"),
    ("code", """\
def list_skills(self) -> list[dict]:
    out = []
    for n, s in self._skills.items():
        raw_name = s.get("name", n)
        display_name = (
            raw_name.split(".")[-1].replace("_", " ").title()
            if "." in n else raw_name
        )
        connector = s.get("connector", n.split(".")[0] if "." in n else "")
        out.append({
            "id": n,
            "name": n,
            "display_name": display_name,
            "description": s.get("description", ""),
            "version": s.get("version", "1.0"),
            "connector": connector,
            "llm_provider": s.get("llm_provider", "claude"),
            "supports": s.get("supports", ["text"]),
            "steps": len(s.get("steps", [])),
        })
    return out"""),

    ("h3", "Finding 5 (P1) — RemoteMCPClient gave vague errors"),
    ("body", "Problem: The stub MCP client gave generic error messages with no machine-readable backend_status field."),
    ("body", "Fix — connectors/remote_mcp_client.py complete rewrite:"),
    ("code", """\
class RemoteMCPClient:
    backend_status = "not_ready"
    requires_provisioning = True
    supports_official_mcp = True
    official_mcp_ready = False
    recommended_mode = "legacy_direct_api"

    def __init__(self, server_url: str | None, connector_name: str):
        self.server_url = server_url
        self.connector_name = connector_name
        self._connected = False

    def _not_ready_error(self, operation: str) -> dict:
        if not self.server_url:
            return {
                "success": False, "error": "not_configured",
                "backend_status": self.backend_status,
                "requires_provisioning": self.requires_provisioning,
                "recommended_mode": self.recommended_mode,
                "message": "Official MCP URL is not configured. ...",
                "next_step": "Visit recklabs.com/setup to provision.",
            }
        return {
            "success": False, "error": "not_implemented",
            "backend_status": self.backend_status,
            "requires_provisioning": self.requires_provisioning,
            "recommended_mode": self.recommended_mode,
            "message": "RemoteMCPClient transport not yet implemented. ...",
        }

    def list_tools(self) -> dict:
        return self._not_ready_error("list_tools")

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        return self._not_ready_error(f"call_tool:{tool_name}")

    def connection_status(self) -> dict:
        return {
            "connected": False,
            "backend_status": self.backend_status,
            "requires_provisioning": self.requires_provisioning,
            "official_mcp_ready": self.official_mcp_ready,
            "recommended_mode": self.recommended_mode,
            "server_url": self.server_url,
        }"""),

    ("h3", "Finding 6 (P2) — Legacy merged zoho connector always registered"),
    ("body", "Problem: The old merged ZohoConnector (pre-split) was registered as \"zoho\" in every registry init, polluting the connector list."),
    ("body", "Fix — registry/connector_registry.py:"),
    ("code", """\
import os
# ...
if os.environ.get("RECKLABS_ENABLE_LEGACY_ZOHO_CONNECTOR") == "1":
    try:
        from connectors.zoho_connector import ZohoConnector
        reg.register("zoho", ZohoConnector, version="1.0.0", api_version="v2")
        logger.warning("Legacy merged ZohoConnector registered")
    except ImportError as e:
        logger.warning("Legacy ZohoConnector not available: %s", e)"""),

    ("h3", "Finding 7 — Regression tests added"),
    ("body", "tests/test_skill_failure.py — 8 tests:"),
    ("bullet", "test_failing_tool_fails_skill — success:false tool → SkillError raised"),
    ("bullet", "test_failing_tool_step_marked_as_error — Failed step → status:error"),
    ("bullet", "test_on_error_continue_allows_skill_to_proceed — on_error:continue → skill completes"),
    ("bullet", "test_on_error_stop_halts_skill — default → SkillError raised"),
    ("bullet", "test_no_duplicate_skill_ids — No duplicate IDs in list_skills()"),
    ("bullet", "test_all_default_skills_are_namespaced — All 8 skills have . in ID"),
    ("bullet", "test_list_skills_has_id_and_display_name — Each skill has id, name, display_name, connector"),
    ("bullet", "test_intent_routing_fails_honestly_on_tool_failure — run_skill_by_intent returns success:false"),
    ("body", "tests/test_registry.py — 5 tests:"),
    ("bullet", "test_zoho_not_registered_by_default — \"zoho\" absent from default registry"),
    ("bullet", "test_zoho_crm_and_books_registered — Both connectors present"),
    ("bullet", "test_legacy_zoho_registered_when_env_var_set — Env var enables legacy"),
    ("bullet", "test_connector_default_mode_is_legacy — Both connectors default to legacy_direct_api"),
    ("bullet", "test_official_mcp_mode_returns_not_ready — official_mcp config → success:false"),
    ("body", "tests/test_connector_config.py — Added test_default_config_uses_legacy_mode:"),
    ("code", """\
def test_default_config_uses_legacy_mode():
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    for connector_id, connector_cfg in cfg.get("connectors", {}).items():
        assert connector_cfg.get("mode") == "legacy_direct_api"
        assert connector_cfg.get("official_mcp", {}).get("status") == "not_ready\""""),

    ("h3", "Finding 8 — Verification results"),
    ("body", "All 5 test suites PASS:"),
    ("bullet", "test_connector_config.py: 3 tests PASS"),
    ("bullet", "test_skill_loading.py: 2 tests PASS"),
    ("bullet", "test_tool_loading.py: 4 tests PASS"),
    ("bullet", "test_skill_failure.py: 8 tests PASS"),
    ("bullet", "test_registry.py: 5 tests PASS"),
    ("body", "MCP smoke test confirmed:"),
    ("bullet", "tools/list: 25 tools returned"),
    ("bullet", "list_skills: 8 skills, all namespaced (zoho_books.*, zoho_crm.*)"),
    ("bullet", "run_skill_by_intent(\"show leads\"): returns success:false with error 'Skill zoho_crm.lead_generation failed at step fetch_leads: connector_error'"),

    ("h2", "Pending Work"),
    ("bullet", "Rebuild release zip — dist/recklabs-ai-agent-v1.0.1.zip was built BEFORE the code review fixes. Needs rebuild: venv/Scripts/python scripts/build_release.py --version 1.0.1"),
    ("bullet", "GitHub release upload — gh CLI not installed; upload manually or install gh."),
    ("bullet", "RemoteMCPClient transport — Blocked on Zoho publishing official MCP endpoint docs."),
    ("bullet", "tool_map.json placeholders — connectors/zoho_crm/tool_map.json and connectors/zoho_books/tool_map.json have TO_BE_CONFIGURED for official MCP tool names."),
    ("bullet", "RECKLABS_CONNECTOR_BOOTSTRAP_URL — Backend provisioning endpoint not yet live."),

    ("h2", "Key Files Reference"),
    ("table", [
        ["File", "Purpose"],
        ["agent/mcp_server.py", "MCP stdio server entry point"],
        ["agent/skill_executor.py", "Skill workflow engine"],
        ["tools/skill_tools.py", "run_skill_by_intent, set_executor"],
        ["connectors/zoho_crm/connector.py", "Zoho CRM connector, defaults to legacy_direct_api"],
        ["connectors/zoho_books/connector.py", "Zoho Books connector, defaults to legacy_direct_api"],
        ["connectors/remote_mcp_client.py", "Stub for future official MCP transport"],
        ["registry/connector_registry.py", "Connector class registry + CONNECTOR_CATALOG"],
        ["config/connector_config.json", "Runtime connector config (mode, credentials)"],
        ["config/settings.py", "Loads connector config, handles zoho migration"],
        ["installer/install.bat", "Windows installer, writes connector_config.json"],
        ["skills/base/zoho_crm/*.json.enc", "Encrypted base skills for CRM (4 skills)"],
        ["skills/base/zoho_books/*.json.enc", "Encrypted base skills for Books (4 skills)"],
        ["scripts/build_release.py", "Builds dist/recklabs-ai-agent-vX.Y.Z.zip"],
        ["tests/test_skill_failure.py", "8 regression tests for skill failure propagation"],
        ["tests/test_registry.py", "5 regression tests for connector registry"],
        ["tests/test_connector_config.py", "3 tests for config loading and migration"],
    ]),

    ("h2", "Environment"),
    ("bullet", "Platform: Windows 11, bash shell via Claude Code CLI"),
    ("bullet", "Python venv: venv/Scripts/python (venv/Scripts/pip)"),
    ("bullet", "Claude model: claude-sonnet-4-6"),
    ("bullet", "Date: 2026-04-20"),
    ("bullet", "Working directory: a:/ReckLabs/code/ai-agent/"),
    ("bullet", "User email: mehethescienceman@gmail.com"),

    ("h2", "Env Vars Reference"),
    ("bullet", "RECKLABS_ENABLE_LEGACY_ZOHO_CONNECTOR=1 — registers old merged ZohoConnector as 'zoho'"),
    ("bullet", "RECKLABS_ENABLE_LEGACY_FLAT_SKILLS=1 — enables flat (non-namespaced) skill loading"),
]


def build_pdf():
    import os
    os.makedirs("a:/ReckLabs/code/ai-agent/dist", exist_ok=True)

    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )

    styles = getSampleStyleSheet()

    s_h1 = ParagraphStyle("H1", parent=styles["Heading1"],
        fontSize=18, spaceAfter=6, spaceBefore=0,
        textColor=colors.HexColor("#1a1a2e"))
    s_h2 = ParagraphStyle("H2", parent=styles["Heading2"],
        fontSize=13, spaceAfter=4, spaceBefore=12,
        textColor=colors.HexColor("#16213e"),
        borderPad=2)
    s_h3 = ParagraphStyle("H3", parent=styles["Heading3"],
        fontSize=11, spaceAfter=3, spaceBefore=8,
        textColor=colors.HexColor("#0f3460"))
    s_body = ParagraphStyle("Body", parent=styles["Normal"],
        fontSize=9, spaceAfter=4, leading=13)
    s_meta = ParagraphStyle("Meta", parent=styles["Normal"],
        fontSize=8, spaceAfter=8, textColor=colors.grey, leading=11)
    s_bullet = ParagraphStyle("Bullet", parent=styles["Normal"],
        fontSize=9, spaceAfter=2, leading=12,
        leftIndent=12, bulletIndent=0)
    s_code = ParagraphStyle("Code", parent=styles["Code"],
        fontSize=7.5, leading=10, leftIndent=8,
        backColor=colors.HexColor("#f5f5f5"),
        fontName="Courier")

    story = []

    for kind, text in CONTENT:
        if kind == "h1":
            story.append(Paragraph(text, s_h1))
            story.append(HRFlowable(width="100%", thickness=1.5,
                color=colors.HexColor("#1a1a2e"), spaceAfter=6))
        elif kind == "h2":
            story.append(Spacer(1, 4*mm))
            story.append(Paragraph(text, s_h2))
            story.append(HRFlowable(width="100%", thickness=0.5,
                color=colors.HexColor("#cccccc"), spaceAfter=4))
        elif kind == "h3":
            story.append(Paragraph(text, s_h3))
        elif kind == "body":
            story.append(Paragraph(text, s_body))
        elif kind == "meta":
            story.append(Paragraph(text, s_meta))
        elif kind == "bullet":
            story.append(Paragraph(f"• {text}", s_bullet))
        elif kind == "code":
            story.append(Spacer(1, 2*mm))
            story.append(Preformatted(text, s_code))
            story.append(Spacer(1, 2*mm))
        elif kind == "table":
            rows = text
            col_widths = [90*mm, 80*mm]
            t = Table(rows, colWidths=col_widths)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.HexColor("#f9f9f9"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(t)
            story.append(Spacer(1, 3*mm))

    doc.build(story)
    print(f"PDF written to: {OUTPUT}")


if __name__ == "__main__":
    build_pdf()
