"""
MCP Server — implements the Model Context Protocol over stdio.
Claude Desktop communicates with this server via JSON-RPC 2.0 over stdin/stdout.

Protocol reference: https://modelcontextprotocol.io/docs/concepts/transports
"""
import json
import logging
import sys
from typing import Any

from config.settings import MCP_SERVER_NAME, MCP_SERVER_VERSION

logger = logging.getLogger(__name__)


class MCPServer:
    """
    Minimal MCP server implementation using stdio transport.
    Registers tools from all tool modules and dispatches calls.
    """

    def __init__(self):
        self._tools: dict[str, dict] = {}  # name -> {schema, fn}

    def register_tools(self, tool_list: list[dict]) -> None:
        """Register a list of tool definitions. Each must have: name, description, input_schema, fn."""
        for tool in tool_list:
            self._tools[tool["name"]] = tool
            logger.debug("Registered tool: %s", tool["name"])
        logger.info("Registered %d tools", len(tool_list))

    # ------------------------------------------------------------------
    # JSON-RPC primitives
    # ------------------------------------------------------------------

    def _send(self, obj: dict) -> None:
        """Write a JSON-RPC message to stdout."""
        line = json.dumps(obj, ensure_ascii=False)
        sys.stdout.write(line + "\n")
        sys.stdout.flush()

    def _send_result(self, req_id: Any, result: Any) -> None:
        self._send({"jsonrpc": "2.0", "id": req_id, "result": result})

    def _send_error(self, req_id: Any, code: int, message: str) -> None:
        self._send({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message},
        })

    # ------------------------------------------------------------------
    # MCP method handlers
    # ------------------------------------------------------------------

    def _handle_initialize(self, req_id: Any, params: dict) -> None:
        self._send_result(req_id, {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": MCP_SERVER_NAME, "version": MCP_SERVER_VERSION},
            "capabilities": {"tools": {}},
        })

    def _handle_tools_list(self, req_id: Any, params: dict) -> None:
        tools_out = []
        for name, tool in self._tools.items():
            tools_out.append({
                "name": name,
                "description": tool["description"],
                "inputSchema": tool["input_schema"],
            })
        self._send_result(req_id, {"tools": tools_out})

    def _handle_tools_call(self, req_id: Any, params: dict) -> None:
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self._tools:
            self._send_error(req_id, -32601, f"Tool not found: {tool_name}")
            return

        try:
            fn = self._tools[tool_name]["fn"]
            result = fn(arguments)
            # MCP tools/call result format
            self._send_result(req_id, {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2, ensure_ascii=False),
                    }
                ],
                "isError": not result.get("success", True),
            })
        except Exception as e:
            logger.exception("Error executing tool %s", tool_name)
            self._send_result(req_id, {
                "content": [{"type": "text", "text": f"Tool error: {e}"}],
                "isError": True,
            })

    def _handle_ping(self, req_id: Any, params: dict) -> None:
        self._send_result(req_id, {})

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _dispatch(self, message: dict) -> None:
        req_id = message.get("id")
        method = message.get("method", "")
        params = message.get("params", {})

        handlers = {
            "initialize": self._handle_initialize,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "ping": self._handle_ping,
        }

        if method in handlers:
            handlers[method](req_id, params)
        elif req_id is not None:
            # Unknown method with an ID → return error
            self._send_error(req_id, -32601, f"Method not found: {method}")
        # Notifications (no id) are silently ignored

    def run(self) -> None:
        """Read JSON-RPC messages from stdin and dispatch them."""
        logger.info(
            "MCP server '%s' v%s starting on stdio",
            MCP_SERVER_NAME, MCP_SERVER_VERSION
        )
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON received: %s", e)
                self._send_error(None, -32700, f"Parse error: {e}")
                continue

            try:
                self._dispatch(message)
            except Exception as e:
                logger.exception("Unhandled dispatch error")
                self._send_error(message.get("id"), -32603, f"Internal error: {e}")
