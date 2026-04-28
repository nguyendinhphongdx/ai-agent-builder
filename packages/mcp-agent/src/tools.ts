/**
 * Convert lc-agent agents into per-agent MCP tools.
 *
 * Strategy: one tool per agent named ``chat_with_<slug>``. The MCP host
 * (Claude Desktop, Cursor, …) sees a list of distinct tools and can pick
 * the right one based on the agent's description rather than asking the
 * caller to remember UUIDs.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { AgentSummary, LcAgentClient } from "./client.js";

/** Lowercase slug, kebab-case, only [a-z0-9_]. Empty fallback "agent". */
function slugify(name: string): string {
  const slug = name
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "") // strip diacritics
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 40);
  return slug || "agent";
}

/**
 * Register one tool per agent. Returns the list of registered tool names so
 * caller can log/diagnose. Re-registering the same tool name is a no-op
 * (MCP SDK overwrites).
 */
export function registerAgentTools(
  server: McpServer,
  client: LcAgentClient,
  agents: AgentSummary[],
): string[] {
  const used = new Set<string>();
  const registered: string[] = [];

  for (const agent of agents) {
    // Disambiguate slug collisions (e.g. two agents both named "support") by
    // suffixing the agent's id-prefix.
    let toolName = `chat_with_${slugify(agent.name)}`;
    if (used.has(toolName)) {
      toolName = `${toolName}_${agent.id.slice(0, 6)}`;
    }
    used.add(toolName);

    const description =
      (agent.description?.trim() || `Chat with ${agent.name}`) +
      ` (model: ${agent.model_id})`;

    server.tool(
      toolName,
      description,
      {
        message: z.string().describe("Message to send to the agent"),
        conversation_id: z
          .string()
          .optional()
          .describe(
            "Optional conversation ID returned from a previous call to continue the same thread",
          ),
      },
      async ({ message, conversation_id }) => {
        const res = await client.chat(agent.id, message, conversation_id);
        // Surface conversation_id so the host can chain follow-ups.
        const meta = `\n\n_conversation_id: ${res.conversation_id}_`;
        return {
          content: [{ type: "text" as const, text: res.response + meta }],
        };
      },
    );
    registered.push(toolName);
  }

  return registered;
}
