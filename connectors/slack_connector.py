"""
Slack connector stub — wraps korotovsky/slack-mcp-server (slack-mcp-server).

Status: coming_soon
Upstream: github.com/korotovsky/slack-mcp-server
Package:  slack-mcp-server>=0.2.1  (add to requirements.txt when going live)

Implementation plan when activating:
  pip install slack-mcp-server
  Import SlackClient from slack_mcp_server, wrap with BaseConnector.
  Actions: send_message, read_channel, list_channels, search_messages, manage_reactions.
  Auth: Slack Bot Token (xoxb-...) stored in connectors.json.
"""
from connectors.base_connector import BaseConnector, ConnectorError


class SlackConnector(BaseConnector):
    name = "slack"
    upstream = "github.com/korotovsky/slack-mcp-server"
    status = "coming_soon"

    def __init__(self):
        super().__init__({})

    def authenticate(self) -> dict:
        return {"status": "coming_soon", "message": "Slack connector is coming soon."}

    def execute(self, action: str, params: dict):
        raise ConnectorError(self.name, "Slack connector is coming soon.")

    def health_check(self) -> dict:
        return {"connector": self.name, "status": "coming_soon", "upstream": self.upstream}
