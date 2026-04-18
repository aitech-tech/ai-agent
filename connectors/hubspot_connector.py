"""
HubSpot connector stub — wraps peakmojo/mcp-hubspot (hubspot-mcp-server).

Status: coming_soon
Upstream: github.com/peakmojo/mcp-hubspot
Package:  hubspot-mcp-server>=0.2.1  (add to requirements.txt when going live)

Implementation plan when activating:
  pip install hubspot-mcp-server
  Import HubSpotClient from hubspot_mcp, wrap with BaseConnector.
  Actions: get_contacts, get_deals, search_contacts, create_contact, get_engagements.
"""
from connectors.base_connector import BaseConnector, ConnectorError


class HubSpotConnector(BaseConnector):
    name = "hubspot"
    upstream = "github.com/peakmojo/mcp-hubspot"
    status = "coming_soon"

    def __init__(self):
        super().__init__({})

    def authenticate(self) -> dict:
        return {"status": "coming_soon", "message": "HubSpot connector is coming soon."}

    def execute(self, action: str, params: dict):
        raise ConnectorError(self.name, "HubSpot connector is coming soon.")

    def health_check(self) -> dict:
        return {"connector": self.name, "status": "coming_soon", "upstream": self.upstream}
