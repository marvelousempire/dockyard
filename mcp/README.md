# Dockyard — MCP

Dedicated **Model Context Protocol** server for `dockyard`. Cursor / Claude Code load via `agents/dockyard/.mcp.json`.

## Quick start

```bash
cd agents/dockyard
python3 mcp/server.py
```

Register in the parent repo `.mcp.json` or merge the agent-local `.mcp.json` entry:

- **Server id:** `dockyard`
- **Command:** `python3 mcp/server.py`
- **cwd:** `agents/dockyard`

Add tools in `server.py`; keep one MCP per agent (DRY: no shared mega-server).
