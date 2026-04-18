"""
Notion connector stub — wraps TauroN3/notion-mcp-server-python (notion-mcp-server-python).

Status: coming_soon
Upstream: github.com/TauroN3/notion-mcp-server-python
Package:  notion-mcp-server-python>=0.1.0  (add to requirements.txt when going live)
Official: github.com/makenotion/notion-mcp-server (official Notion MCP server)

Implementation plan when activating:
  pip install notion-mcp-server-python
  Import NotionClient, wrap with BaseConnector.
  Actions: get_page, create_page, update_page, query_database, search_pages.
  Auth: Notion Integration Token stored in connectors.json.
"""
from connectors.base_connector import BaseConnector, ConnectorError


class NotionConnector(BaseConnector):
    name = "notion"
    upstream = "github.com/TauroN3/notion-mcp-server-python"
    status = "coming_soon"

    def __init__(self):
        super().__init__({})

    def authenticate(self) -> dict:
        return {"status": "coming_soon", "message": "Notion connector is coming soon."}

    def execute(self, action: str, params: dict):
        raise ConnectorError(self.name, "Notion connector is coming soon.")

    def health_check(self) -> dict:
        return {"connector": self.name, "status": "coming_soon", "upstream": self.upstream}
