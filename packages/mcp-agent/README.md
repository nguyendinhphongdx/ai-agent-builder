# lc-agent-mcp

MCP server that exposes your [AgentForge](https://github.com/your-repo) agents
as tools for any Model Context Protocol client (Claude Desktop, Cursor, …).

## Install

No install needed — invoked via `npx`.

## Configure

### Claude Desktop

Edit your `claude_desktop_config.json`:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "lc-agent": {
      "command": "npx",
      "args": ["-y", "lc-agent-mcp@latest"],
      "env": {
        "AGENTFORGE_API_URL": "https://your-host.com/api",
        "AGENTFORGE_API_TOKEN": "afpt_xxx..."
      }
    }
  }
}
```

### Cursor / other MCP hosts

Same shape — point to whatever config file the host uses.

## How it works

On startup the server calls `GET /external/agents` once and registers one MCP
tool per agent named `chat_with_<slug>`. Claude (or Cursor) sees them as
distinct tools and picks the right one from the agent's description.

Each tool accepts:

- `message` (required) — the message to send to the agent
- `conversation_id` (optional) — pass back a value returned from a previous
  call to continue the same thread

## Required token scopes

Create a token at `/settings` → API Tokens with at least:

- `agents:read`
- `agents:chat`

## License

MIT
