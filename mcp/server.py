#!/usr/bin/env python3
"""stdio MCP server for dockyard — extend with agent-specific tools."""

from __future__ import annotations

import json
import sys

AGENT_NAME = "dockyard"
SERVER_NAME = "dockyard"


def _send(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def _handle(req: dict) -> dict | None:
    method = req.get("method")
    req_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": "0.1.0"},
            },
        }
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "agent_ping",
                        "description": f"Health check for {AGENT_NAME}",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                        },
                    }
                ]
            },
        }
    if method == "tools/call" and req.get("params", {}).get("name") == "agent_ping":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {"ok": True, "agent": AGENT_NAME, "surface": "mcp"}
                        ),
                    }
                ]
            },
        }
    if method == "notifications/initialized":
        return None
    if req_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not implemented: {method}"},
        }
    return None


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = _handle(req)
        if resp is not None:
            _send(resp)


if __name__ == "__main__":
    main()
