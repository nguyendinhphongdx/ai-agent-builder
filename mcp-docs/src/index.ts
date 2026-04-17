import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import path from "path";
import { fileURLToPath } from "url";
import { loadIndex, getDocContent, type DocIndex } from "./indexer.js";
import {
  search,
  findTableDocs,
  findApiDocs,
  findComponentDocs,
} from "./search.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const docsDir = path.resolve(__dirname, "../../docs");

// Load index
const index: DocIndex = loadIndex(docsDir);

// Create MCP server
const server = new McpServer({
  name: "lc-agent-docs",
  version: "1.0.0",
});

// Tool 1: search_docs
server.tool(
  "search_docs",
  "Search project documentation by keyword. Returns matching doc summaries with relevance scores.",
  {
    query: z.string().describe("Search keywords (e.g. 'websocket streaming', 'tool registry')"),
    domain: z.string().optional().describe("Filter by domain: architecture, conventions, backend, frontend, database, api, flows"),
    limit: z.number().optional().default(5).describe("Max results (default 5)"),
  },
  async ({ query, domain, limit }) => {
    const results = search(index, query, { domain, limit });

    if (results.length === 0) {
      return { content: [{ type: "text" as const, text: "No matching documents found." }] };
    }

    const text = results
      .map(
        (r, i) =>
          `${i + 1}. **${r.doc.title}** (score: ${r.score})\n   ID: \`${r.doc.id}\` | Domain: ${r.doc.domain}\n   ${r.doc.summary}\n   Tags: ${r.matchedTags.join(", ") || r.doc.tags.slice(0, 5).join(", ")}`
      )
      .join("\n\n");

    return { content: [{ type: "text" as const, text }] };
  }
);

// Tool 2: get_doc
server.tool(
  "get_doc",
  "Get full content of a specific documentation file by its ID.",
  {
    doc_id: z.string().describe("Document ID from search results (e.g. 'backend-auth', 'database-table-agents')"),
  },
  async ({ doc_id }) => {
    const entry = index.byId.get(doc_id);
    if (!entry) {
      return { content: [{ type: "text" as const, text: `Document not found: ${doc_id}\n\nAvailable IDs: ${index.entries.map((e) => e.id).join(", ")}` }] };
    }

    const content = getDocContent(docsDir, entry.path);
    return { content: [{ type: "text" as const, text: `# ${entry.title}\n\n${content}` }] };
  }
);

// Tool 3: list_docs
server.tool(
  "list_docs",
  "List all available documentation files, optionally filtered by domain.",
  {
    domain: z.string().optional().describe("Filter: architecture, conventions, backend, frontend, database, api, flows"),
  },
  async ({ domain }) => {
    let entries = index.entries;
    if (domain) {
      entries = index.byDomain.get(domain) || [];
    }

    if (entries.length === 0) {
      const domains = [...index.byDomain.keys()].join(", ");
      return { content: [{ type: "text" as const, text: `No docs found for domain "${domain}". Available: ${domains}` }] };
    }

    const grouped = new Map<string, typeof entries>();
    for (const e of entries) {
      if (!grouped.has(e.domain)) grouped.set(e.domain, []);
      grouped.get(e.domain)!.push(e);
    }

    let text = "";
    for (const [d, docs] of grouped) {
      text += `## ${d} (${docs.length} docs)\n`;
      for (const doc of docs) {
        text += `- \`${doc.id}\` — ${doc.title}\n`;
      }
      text += "\n";
    }

    return { content: [{ type: "text" as const, text: text.trim() }] };
  }
);

// Tool 4: get_schema
server.tool(
  "get_schema",
  "Get database schema documentation for a specific table.",
  {
    table_name: z.string().describe("Table name (e.g. 'agents', 'document_chunks', 'workflow_nodes')"),
  },
  async ({ table_name }) => {
    const doc = findTableDocs(index, table_name);
    if (!doc) {
      const tables = index.entries
        .filter((e) => e.domain === "database")
        .map((e) => e.id)
        .join(", ");
      return { content: [{ type: "text" as const, text: `No schema found for "${table_name}". Available: ${tables}` }] };
    }

    const content = getDocContent(docsDir, doc.path);
    return { content: [{ type: "text" as const, text: `# ${doc.title}\n\n${content}` }] };
  }
);

// Tool 5: get_api
server.tool(
  "get_api",
  "Get API endpoint documentation.",
  {
    endpoint: z.string().describe("Endpoint path or keyword (e.g. '/api/agents', 'websocket', 'auth')"),
  },
  async ({ endpoint }) => {
    const doc = findApiDocs(index, endpoint);
    if (!doc) {
      const endpoints = index.entries
        .filter((e) => e.domain === "api")
        .map((e) => `${e.id}: ${e.title}`)
        .join("\n");
      return { content: [{ type: "text" as const, text: `No API doc found for "${endpoint}". Available:\n${endpoints}` }] };
    }

    const content = getDocContent(docsDir, doc.path);
    return { content: [{ type: "text" as const, text: `# ${doc.title}\n\n${content}` }] };
  }
);

// Tool 6: get_component
server.tool(
  "get_component",
  "Get frontend component or feature documentation.",
  {
    name: z.string().describe("Component or feature name (e.g. 'ChatWindow', 'workflow-editor', 'agents')"),
  },
  async ({ name }) => {
    const docs = findComponentDocs(index, name);
    if (docs.length === 0) {
      const features = index.entries
        .filter((e) => e.domain === "frontend")
        .map((e) => e.id)
        .join(", ");
      return { content: [{ type: "text" as const, text: `No component doc found for "${name}". Available: ${features}` }] };
    }

    const texts = docs.map((doc) => {
      const content = getDocContent(docsDir, doc.path);
      return `# ${doc.title}\n\n${content}`;
    });

    return { content: [{ type: "text" as const, text: texts.join("\n\n---\n\n") }] };
  }
);

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[mcp-docs] Server started on stdio");
}

main().catch(console.error);
