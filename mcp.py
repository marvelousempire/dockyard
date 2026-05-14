#!/usr/bin/env python3
"""Dockyard MCP stdio server.

Speaks JSON-RPC 2.0 over stdin/stdout following the Model Context
Protocol (MCP) shape — `initialize`, `tools/list`, `tools/call`. No
third-party dependencies; stdlib only.

Wire it into Claude Code (or any MCP-capable client) by pointing it at
the python script::

    {
      "mcpServers": {
        "dockyard": {
          "command": "python3",
          "args": ["/Users/you/Developer/claude-chat-reader/dockyard/mcp.py"]
        }
      }
    }

Tools exposed (all hit the same Docker socket the HTTP server uses):

    list_containers     start_container    stop_container
    restart_container   remove_container   tail_logs
    list_images         pull_image         remove_image
    list_volumes        list_networks      system_info

This file is intentionally short — the heavy lifting (socket detect,
HTTP-over-unix-socket) lives in ``lib/socket.py`` and is reused.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Optional

# Local imports (no sys.path tricks needed if run with `python3 mcp.py`)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from dockyard.lib.socket import load_config, resolve_socket  # noqa: E402
from dockyard.server import docker_request  # noqa: E402

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "dockyard", "version": "0.2.0"}

# ---------------------------------------------------------------------------
# Tool catalog
# ---------------------------------------------------------------------------

TOOLS: list[dict] = [
    {
        "name": "list_containers",
        "description": "List Docker containers. Default: running only.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "all": {
                    "type": "boolean",
                    "description": "Include stopped containers",
                    "default": False,
                }
            },
        },
    },
    {
        "name": "start_container",
        "description": "Start a container by ID or name.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
    {
        "name": "stop_container",
        "description": "Stop a container by ID or name.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
    {
        "name": "restart_container",
        "description": "Restart a container by ID or name.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
    {
        "name": "remove_container",
        "description": "Remove a container (force=true by default).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "force": {"type": "boolean", "default": True},
            },
            "required": ["id"],
        },
    },
    {
        "name": "tail_logs",
        "description": "Tail the last N log lines for a container.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "lines": {"type": "integer", "default": 100},
            },
            "required": ["id"],
        },
    },
    {
        "name": "list_images",
        "description": "List local Docker images.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "pull_image",
        "description": "Pull an image from a registry.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "e.g. nginx:latest"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "remove_image",
        "description": "Remove an image by ID or tag.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
    {
        "name": "list_volumes",
        "description": "List Docker volumes.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_networks",
        "description": "List Docker networks.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "system_info",
        "description": "Return engine info, version, container/image counts, disk usage.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def _socket() -> str:
    socket_path, _engine = resolve_socket(load_config())
    return socket_path


def _format_container(c: dict) -> str:
    name = (c.get("Names") or ["?"])[0].lstrip("/")
    state = c.get("State", "?")
    image = c.get("Image", "?")
    ports = ", ".join(
        f"{p.get('PublicPort','?')}->{p.get('PrivatePort','?')}/{p.get('Type','?')}"
        for p in (c.get("Ports") or [])
        if p.get("PublicPort")
    )
    short = (c.get("Id") or "")[:12]
    return f"  {state:8} {short}  {name:24} {image}" + (f"  [{ports}]" if ports else "")


def tool_list_containers(args: dict) -> str:
    include_all = bool(args.get("all", False))
    qs = "all=1" if include_all else ""
    status, _h, body = docker_request(_socket(), "GET", f"/containers/json?{qs}")
    if status >= 400:
        raise RuntimeError(f"docker error {status}: {body.decode()}")
    items = json.loads(body)
    if not items:
        return "(no containers)"
    return f"{len(items)} container(s):\n" + "\n".join(_format_container(c) for c in items)


def _container_action(action: str, args: dict, *, force: bool = False) -> str:
    cid = args["id"]
    if action == "remove":
        qs = "force=1" if force else ""
        status, _h, body = docker_request(_socket(), "DELETE", f"/containers/{cid}?{qs}")
    else:
        status, _h, body = docker_request(_socket(), "POST", f"/containers/{cid}/{action}")
    if status >= 400:
        raise RuntimeError(f"docker error {status}: {body.decode()}")
    return f"✅ {action}: {cid}"


def tool_start_container(args: dict) -> str: return _container_action("start", args)
def tool_stop_container(args: dict) -> str: return _container_action("stop", args)
def tool_restart_container(args: dict) -> str: return _container_action("restart", args)
def tool_remove_container(args: dict) -> str:
    return _container_action("remove", args, force=bool(args.get("force", True)))


def tool_tail_logs(args: dict) -> str:
    cid = args["id"]
    lines = int(args.get("lines", 100))
    path = f"/containers/{cid}/logs?stdout=1&stderr=1&follow=0&tail={lines}&timestamps=1"
    status, _h, body = docker_request(_socket(), "GET", path, timeout=10)
    if status >= 400:
        raise RuntimeError(f"docker error {status}: {body.decode()}")
    # Strip 8-byte multiplex headers
    out: list[bytes] = []
    i = 0
    while i + 8 <= len(body):
        size = int.from_bytes(body[i + 4 : i + 8], "big")
        i += 8
        out.append(body[i : i + size])
        i += size
    return b"".join(out).decode("utf-8", errors="replace") or "(no log output)"


def tool_list_images(_args: dict) -> str:
    status, _h, body = docker_request(_socket(), "GET", "/images/json")
    if status >= 400:
        raise RuntimeError(f"docker error {status}: {body.decode()}")
    imgs = json.loads(body)
    if not imgs:
        return "(no images)"
    lines = []
    for img in imgs:
        tag = (img.get("RepoTags") or ["<none>:<none>"])[0]
        size = img.get("Size", 0)
        size_mb = size / (1024 * 1024) if size else 0
        lines.append(f"  {tag:50}  {size_mb:7.1f} MB")
    return f"{len(imgs)} image(s):\n" + "\n".join(lines)


def tool_pull_image(args: dict) -> str:
    name = args["name"]
    if ":" in name:
        from_image, tag = name.split(":", 1)
    else:
        from_image, tag = name, "latest"
    import urllib.parse as up
    path = f"/images/create?fromImage={up.quote(from_image)}&tag={up.quote(tag)}"
    status, _h, body = docker_request(_socket(), "POST", path, timeout=120)
    if status >= 400:
        raise RuntimeError(f"docker error {status}: {body.decode()}")
    return f"✅ pulled {name}"


def tool_remove_image(args: dict) -> str:
    iid = args["id"]
    status, _h, body = docker_request(_socket(), "DELETE", f"/images/{iid}")
    if status >= 400:
        raise RuntimeError(f"docker error {status}: {body.decode()}")
    return f"✅ removed image: {iid}"


def tool_list_volumes(_args: dict) -> str:
    status, _h, body = docker_request(_socket(), "GET", "/volumes")
    if status >= 400:
        raise RuntimeError(f"docker error {status}: {body.decode()}")
    vols = json.loads(body).get("Volumes") or []
    if not vols:
        return "(no volumes)"
    return f"{len(vols)} volume(s):\n" + "\n".join(
        f"  {v['Name']:40}  driver={v.get('Driver','?')}" for v in vols
    )


def tool_list_networks(_args: dict) -> str:
    status, _h, body = docker_request(_socket(), "GET", "/networks")
    if status >= 400:
        raise RuntimeError(f"docker error {status}: {body.decode()}")
    nets = json.loads(body)
    if not nets:
        return "(no networks)"
    return f"{len(nets)} network(s):\n" + "\n".join(
        f"  {n['Name']:30}  driver={n['Driver']}  scope={n['Scope']}" for n in nets
    )


def tool_system_info(_args: dict) -> str:
    status, _h, body = docker_request(_socket(), "GET", "/info")
    if status >= 400:
        raise RuntimeError(f"docker error {status}: {body.decode()}")
    info = json.loads(body)
    return (
        f"Engine: {info.get('ServerVersion','?')}\n"
        f"OS: {info.get('OperatingSystem','?')}\n"
        f"CPUs: {info.get('NCPU','?')}  Memory: {info.get('MemTotal',0)//(1024*1024)} MB\n"
        f"Containers: {info.get('ContainersRunning','?')} running"
        f" / {info.get('Containers','?')} total\n"
        f"Images: {info.get('Images','?')}\n"
        f"Driver: {info.get('Driver','?')}"
    )


TOOL_HANDLERS = {
    "list_containers": tool_list_containers,
    "start_container": tool_start_container,
    "stop_container": tool_stop_container,
    "restart_container": tool_restart_container,
    "remove_container": tool_remove_container,
    "tail_logs": tool_tail_logs,
    "list_images": tool_list_images,
    "pull_image": tool_pull_image,
    "remove_image": tool_remove_image,
    "list_volumes": tool_list_volumes,
    "list_networks": tool_list_networks,
    "system_info": tool_system_info,
}

# ---------------------------------------------------------------------------
# JSON-RPC plumbing
# ---------------------------------------------------------------------------


def _reply(req_id: Any, result: Any = None, error: Optional[dict] = None) -> dict:
    msg = {"jsonrpc": "2.0", "id": req_id}
    if error is not None:
        msg["error"] = error
    else:
        msg["result"] = result
    return msg


def _emit(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def _log(s: str) -> None:
    # MCP servers must NEVER log to stdout (it's the transport).
    sys.stderr.write(f"[dockyard-mcp] {time.strftime('%H:%M:%S')} {s}\n")
    sys.stderr.flush()


def handle(msg: dict) -> Optional[dict]:
    method = msg.get("method")
    req_id = msg.get("id")
    params = msg.get("params") or {}

    if method == "initialize":
        return _reply(
            req_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        )

    if method == "tools/list":
        return _reply(req_id, {"tools": TOOLS})

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        handler = TOOL_HANDLERS.get(name)
        if handler is None:
            return _reply(req_id, error={"code": -32601, "message": f"unknown tool: {name}"})
        try:
            text = handler(args)
            return _reply(
                req_id,
                {"content": [{"type": "text", "text": text}], "isError": False},
            )
        except Exception as e:  # noqa: BLE001
            return _reply(
                req_id,
                {"content": [{"type": "text", "text": f"❌ {e}"}], "isError": True},
            )

    if method == "notifications/initialized":
        # Per spec: no response expected for notifications
        return None

    if req_id is not None:
        return _reply(req_id, error={"code": -32601, "message": f"method not found: {method}"})
    return None


def main() -> int:
    _log(f"starting (tools={len(TOOLS)})")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            _log(f"parse error: {e}")
            continue
        try:
            reply = handle(msg)
        except Exception as e:  # noqa: BLE001
            _log(f"handler error: {e}")
            if msg.get("id") is not None:
                _emit(_reply(msg.get("id"), error={"code": -32603, "message": str(e)}))
            continue
        if reply is not None:
            _emit(reply)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
