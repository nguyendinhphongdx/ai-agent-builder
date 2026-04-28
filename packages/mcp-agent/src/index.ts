#!/usr/bin/env node
/**
 * lc-agent MCP server — exposes your AgentForge agents as MCP tools.
 *
 * Configure in Claude Desktop / Cursor:
 *
 *   {
 *     "mcpServers": {
 *       "lc-agent": {
 *         "command": "npx",
 *         "args": ["-y", "lc-agent-mcp@latest"],
 *         "env": {
 *           "AGENTFORGE_API_URL": "https://your-host.com/api",
 *           "AGENTFORGE_API_TOKEN": "afpt_xxx..."
 *         }
 *       }
 *     }
 *   }
 *
 * On startup we call ``GET /external/agents`` once and register one MCP tool
 * per agent. Re-launching Claude Desktop picks up new agents.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

import { LcAgentClient } from "./client.js";
import { registerAgentTools } from "./tools.js";

const API_URL = (process.env.AGENTFORGE_API_URL ?? "").replace(/\/$/, "");
const API_TOKEN = process.env.AGENTFORGE_API_TOKEN ?? "";

if (!API_URL) {
  console.error(
    "lc-agent-mcp: missing AGENTFORGE_API_URL env. " +
      "Set it to your backend's /api base, e.g. https://yourapp.com/api",
  );
  process.exit(1);
}
if (!API_TOKEN) {
  console.error(
    "lc-agent-mcp: missing AGENTFORGE_API_TOKEN env. " +
      "Create a personal access token at /settings → API Tokens with scopes " +
      "agents:read + agents:chat.",
  );
  process.exit(1);
}

const client = new LcAgentClient(API_URL, API_TOKEN);

const server = new McpServer({
  name: "lc-agent",
  version: "0.1.0",
});

// ── Bootstrap: fetch agents and register a tool per agent ─────────
async function bootstrap(): Promise<void> {
  let agents;
  try {
    agents = await client.listAgents();
  } catch (e) {
    console.error("lc-agent-mcp: failed to list agents —", (e as Error).message);
    process.exit(1);
  }

  if (agents.length === 0) {
    console.error(
      "lc-agent-mcp: token has access to 0 agents. Create at least one agent " +
        "in the dashboard, then restart this MCP server.",
    );
  }

  const names = registerAgentTools(server, client, agents);
  console.error(
    `lc-agent-mcp: registered ${names.length} tool(s): ${names.join(", ") || "(none)"}`,
  );
}

await bootstrap();

// ── Wire stdio transport ──────────────────────────────────────────
const transport = new StdioServerTransport();
await server.connect(transport);
