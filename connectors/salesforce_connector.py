"""
Salesforce connector stub — wraps LokiMCPUniverse/salesforce-mcp-server.

Status: coming_soon
Upstream: github.com/LokiMCPUniverse/salesforce-mcp-server
Official: github.com/salesforcecli/mcp (official Salesforce CLI MCP — Node.js)
Package:  salesforce-mcp-server-h>=0.1.0  (add to requirements.txt when going live)

Implementation plan when activating:
  pip install salesforce-mcp-server-h
  Import SalesforceClient, wrap with BaseConnector.
  Actions: soql_query, sosl_search, get_object, create_record, update_record, run_apex.
  Auth: Salesforce OAuth2 / Connected App credentials in connectors.json.
"""
from connectors.base_connector import BaseConnector, ConnectorError


class SalesforceConnector(BaseConnector):
    name = "salesforce"
    upstream = "github.com/LokiMCPUniverse/salesforce-mcp-server"
    status = "coming_soon"

    def __init__(self):
        super().__init__({})

    def authenticate(self) -> dict:
        return {"status": "coming_soon", "message": "Salesforce connector is coming soon."}

    def execute(self, action: str, params: dict):
        raise ConnectorError(self.name, "Salesforce connector is coming soon.")

    def health_check(self) -> dict:
        return {"connector": self.name, "status": "coming_soon", "upstream": self.upstream}
