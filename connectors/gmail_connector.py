"""
Gmail connector stub — wraps taylorwilsdon/google_workspace_mcp (workspace-mcp).

Status: coming_soon
Upstream: github.com/taylorwilsdon/google_workspace_mcp
Package:  workspace-mcp>=1.10.0  (add to requirements.txt when going live)

Implementation plan when activating:
  pip install workspace-mcp
  Import GmailClient from workspace_mcp, wrap with BaseConnector.
  Actions: send_email, read_email, search_emails, list_labels, manage_attachments.
  Auth: Google OAuth2 via workspace-mcp's native OAuth2.1 support.
"""
from connectors.base_connector import BaseConnector, ConnectorError


class GmailConnector(BaseConnector):
    name = "gmail"
    upstream = "github.com/taylorwilsdon/google_workspace_mcp"
    status = "coming_soon"

    def __init__(self):
        super().__init__({})

    def authenticate(self) -> dict:
        return {"status": "coming_soon", "message": "Gmail connector is coming soon."}

    def execute(self, action: str, params: dict):
        raise ConnectorError(self.name, "Gmail connector is coming soon.")

    def health_check(self) -> dict:
        return {"connector": self.name, "status": "coming_soon", "upstream": self.upstream}
