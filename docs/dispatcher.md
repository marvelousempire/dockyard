# Dockyard MCP — wiring into Claude Code / dispatcher

Plan 0013 (Track E-E) adds a `pnpm dockyard:mcp` shortcut so the
dockyard MCP stdio server is one keystroke away from any dispatcher
or AI agent. This doc covers how to plug it into:

1. The main repo's `pnpm dispatch` (Haiku-classifier task router)
2. Claude Code's `mcpServers` config
3. Cursor's MCP integration
4. Generic MCP clients (custom, plain JSON-RPC over stdio)

## Quick test

```bash
# From the repo root:
pnpm dockyard:mcp <<<'{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Expected: a single JSON line with 12 tools (list_containers,
# start_container, ..., system_info).
```

## 1. Wire into `pnpm dispatch`

`src/scripts/dispatch-cli.ts` is the front door for the Haiku-routed
task dispatcher. To route Docker-related questions to the dockyard MCP:

```ts
// inside dispatch-cli.ts route table (illustrative)
if (/(container|docker|image|volume)/i.test(task)) {
  return spawn("pnpm", ["dockyard:mcp"], { stdio: ["pipe","pipe","inherit"] });
}
```

Live equivalent without a code change:

```bash
pnpm dispatch "list my running containers" \
  --mcp 'pnpm dockyard:mcp'
```

## 2. Claude Code (~/.claude/settings.local.json or per-project)

```json
{
  "mcpServers": {
    "dockyard": {
      "command": "python3",
      "args": ["/Users/<you>/Developer/claude-chat-reader/dockyard/mcp.py"]
    }
  }
}
```

Restart Claude Code. The 12 dockyard tools appear under `dockyard:`
in the tool catalog. From any chat:

> "stop my postgres container"

Claude Code routes to `dockyard:stop_container({id: "postgres"})`.

## 3. Cursor

Cursor reads the same MCP config shape:

```json
// ~/.cursor/mcp.json
{
  "mcpServers": {
    "dockyard": {
      "command": "python3",
      "args": ["/Users/<you>/Developer/claude-chat-reader/dockyard/mcp.py"]
    }
  }
}
```

## 4. Generic MCP client

Speak JSON-RPC 2.0 over stdin/stdout:

```bash
{
  printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n'
  printf '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}\n'
  printf '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"list_containers","arguments":{"all":true}}}\n'
} | python3 dockyard/mcp.py
```

## Available tools (v0.3.0)

| Tool | Args | Returns |
|---|---|---|
| `list_containers` | `{all?: bool}` | text block, one line per container |
| `start_container` | `{id: str}` | confirmation |
| `stop_container` | `{id: str}` | confirmation |
| `restart_container` | `{id: str}` | confirmation |
| `remove_container` | `{id: str, force?: bool}` | confirmation |
| `tail_logs` | `{id: str, lines?: int}` | log text (stdout+stderr) |
| `list_images` | `{}` | text block |
| `pull_image` | `{name: "nginx:latest"}` | confirmation |
| `remove_image` | `{id: str}` | confirmation |
| `list_volumes` | `{}` | text block |
| `list_networks` | `{}` | text block |
| `system_info` | `{}` | engine + counts + memory + driver |

## Notes

- The MCP server uses **the same socket** that `dockyard/server.py`
  auto-detects (Colima default → profiles → OrbStack → Docker Desktop
  → native Linux → `DOCKER_HOST` env).
- All output goes to **stdout as JSON-RPC**. Diagnostic logs go to
  **stderr** so they don't corrupt the transport.
- Errors raise `isError: true` content blocks per MCP spec.
- Pull and exec are bounded by a generous timeout (120 s) because
  image pulls can be slow on cold caches.

## When to extend

If you need a new operation (e.g. `inspect_container`, `pause_container`,
`rename_container`), add a handler in `dockyard/mcp.py`:

```python
def tool_my_new_thing(args: dict) -> str:
    ...
TOOLS.append({"name": "my_new_thing", ...})
TOOL_HANDLERS["my_new_thing"] = tool_my_new_thing
```

No restart of Claude Code is needed in dev mode — the MCP server
re-spawns per session, picks up the new tools.
