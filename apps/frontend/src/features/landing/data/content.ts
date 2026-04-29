/**
 * Landing page content. Centralised so copy edits don't require touching JSX.
 * Keep names ASCII to avoid CSS-class collisions in any consumer.
 */
import type { LucideIcon } from "lucide-react";
import {
  BookOpen,
  Bot,
  Code2,
  GitBranch,
  Globe,
  Layers,
  Network,
  Plug,
  ServerCog,
  ShieldCheck,
  Workflow,
  Wrench,
  Zap,
} from "lucide-react";

export const SITE = {
  name: "AgentForge",
  domain: "agentforge.dev",
  url: "https://agentforge.dev",
  tagline: "The open platform for production AI agents",
  description:
    "Build AI agents that connect to your tools and knowledge. Deploy them as a chat widget, an API, or inside Claude — all from one open-source platform.",
  github: "https://github.com/agentforge/agentforge",
  twitter: "@agentforge",
  discord: "https://discord.gg/agentforge",
  docs: "/docs",
  email: "hello@agentforge.dev",
};

export const NAV_LINKS = [
  { href: "#capabilities", label: "Capabilities" },
  { href: "#integrate", label: "Integrate" },
  { href: "#compare", label: "Compare" },
  { href: "#how", label: "How it works" },
] as const;

export const HERO_STATS: { value: string; label: string }[] = [
  { value: "5 min", label: "To set up" },
  { value: "Free", label: "Forever, MIT" },
  { value: "Realtime", label: "Streaming chat" },
  { value: "3", label: "Ways to ship" },
];

export const TRUST_LOGOS: { name: string; sub: string }[] = [
  { name: "LangGraph", sub: "Stateful runtime" },
  { name: "LangChain", sub: "Tools & retrievers" },
  { name: "OpenAI", sub: "GPT-4o" },
  { name: "Anthropic", sub: "Claude" },
  { name: "Ollama", sub: "Local LLMs" },
  { name: "pgvector", sub: "RAG storage" },
  { name: "PostgreSQL", sub: "Source of truth" },
  { name: "RabbitMQ", sub: "Async dispatch" },
];

export interface Capability {
  id: string;
  icon: LucideIcon;
  title: string;
  description: string;
  /** Span 1 (compact) or 2 (wide) on the lg bento grid. */
  span: 1 | 2;
}

export const CAPABILITIES: Capability[] = [
  {
    id: "agents",
    icon: Bot,
    title: "Agents you actually ship",
    description:
      "Compose system prompt, model, tools, and knowledge bases into a single config — versioned, ownable, deployable.",
    span: 2,
  },
  {
    id: "tools",
    icon: Wrench,
    title: "Tools without boilerplate",
    description:
      "Wire up HTTP, database, web scrape, and code execution in a form. JSON Schema converts to typed tool inputs at runtime.",
    span: 1,
  },
  {
    id: "rag",
    icon: BookOpen,
    title: "RAG that scales with you",
    description:
      "Drop in PDFs, DOCX, MD, HTML. Auto-chunked, embedded, indexed in pgvector — no vendor vector DB to babysit.",
    span: 1,
  },
  {
    id: "workflows",
    icon: Workflow,
    title: "Visual workflow editor",
    description:
      "When chat isn't enough: chain steps, branch on conditions, fan out to subgraphs, gate with human-in-the-loop.",
    span: 2,
  },
  {
    id: "multi",
    icon: Network,
    title: "Multi-agent collaboration",
    description:
      "Supervisor delegates to worker agents. Peer mode runs sequentially with synthesis. Mix providers freely.",
    span: 2,
  },
  {
    id: "selfhost",
    icon: ShieldCheck,
    title: "Built for self-host",
    description:
      "JWT in httpOnly cookies. Encrypted credentials. Sandboxed code. Async dispatcher with retry + DLQ. No telemetry.",
    span: 1,
  },
];

export interface IntegrationPath {
  id: string;
  icon: LucideIcon;
  title: string;
  tagline: string; // 1 short phrase under title in tab
  pitch: string; // longer description shown above editor
  filename: string;
  language: "html" | "typescript" | "json";
  code: string;
}

export const INTEGRATION_PATHS: IntegrationPath[] = [
  {
    id: "embed",
    icon: Globe,
    title: "Embed widget",
    tagline: "One script tag",
    pitch:
      "A drop-in chat bubble for any website. Shadow-DOM isolated, opens to a streaming chat with your agent. Zero config.",
    filename: "index.html",
    language: "html",
    code: `<!-- Drop into any page -->
<script
  src="https://cdn.agentforge.dev/embed.js"
  data-agent="cs-bot"
  data-token="afp_pub_..."
  defer
></script>`,
  },
  {
    id: "api",
    icon: Code2,
    title: "REST API + tokens",
    tagline: "From any backend",
    pitch:
      "Personal access tokens with scopes, per-token rate limits, and conversation continuity. Works from any language.",
    filename: "agent.ts",
    language: "typescript",
    code: `import { AgentForge } from "@agentforge/sdk";

const af = new AgentForge({ token: process.env.AF_TOKEN });

const res = await af.agents.run("cs-bot", {
  message: "How do I reset my password?",
  stream: true,
});

for await (const event of res) {
  if (event.type === "token") process.stdout.write(event.content);
}`,
  },
  {
    id: "mcp",
    icon: Plug,
    title: "MCP server",
    tagline: "Claude · Cursor · Zed",
    pitch:
      "Expose your agent as a Model Context Protocol server. Any MCP-aware client connects instantly — no glue code.",
    filename: "claude_desktop_config.json",
    language: "json",
    code: `{
  "mcpServers": {
    "agentforge": {
      "command": "npx",
      "args": ["-y", "@agentforge/mcp"],
      "env": { "AGENTFORGE_TOKEN": "afp_..." }
    }
  }
}`,
  },
];

export interface ComparisonRow {
  feature: string;
  agentforge: string;
  langflow: string;
  dify: string;
  diy: string;
}

export const COMPARISON_ROWS: ComparisonRow[] = [
  {
    feature: "Self-host (single command)",
    agentforge: "yes",
    langflow: "yes",
    dify: "yes",
    diy: "—",
  },
  {
    feature: "License",
    agentforge: "MIT",
    langflow: "MIT",
    dify: "Custom",
    diy: "yours",
  },
  {
    feature: "Visual workflow editor",
    agentforge: "yes",
    langflow: "yes",
    dify: "yes",
    diy: "—",
  },
  {
    feature: "Multi-agent (supervisor + peer)",
    agentforge: "yes",
    langflow: "partial",
    dify: "partial",
    diy: "—",
  },
  {
    feature: "Embed widget out of the box",
    agentforge: "yes",
    langflow: "—",
    dify: "yes",
    diy: "—",
  },
  {
    feature: "REST API with scoped tokens",
    agentforge: "yes",
    langflow: "yes",
    dify: "yes",
    diy: "—",
  },
  {
    feature: "MCP server channel",
    agentforge: "yes",
    langflow: "—",
    dify: "—",
    diy: "—",
  },
  {
    feature: "Async dispatcher (retry + DLQ)",
    agentforge: "yes",
    langflow: "—",
    dify: "partial",
    diy: "—",
  },
  {
    feature: "Code-first agent specs",
    agentforge: "yes",
    langflow: "partial",
    dify: "—",
    diy: "yes",
  },
  {
    feature: "Time to first agent",
    agentforge: "5 min",
    langflow: "10 min",
    dify: "10 min",
    diy: "days",
  },
];

export interface HowStep {
  step: string;
  title: string;
  description: string;
  icon: LucideIcon;
}

export const HOW_STEPS: HowStep[] = [
  {
    step: "01",
    title: "Spin it up",
    description:
      "Clone the repo, run docker compose up. Postgres, Redis, RabbitMQ, backend, and frontend boot together.",
    icon: ServerCog,
  },
  {
    step: "02",
    title: "Compose your agent",
    description:
      "Pick a model, write instructions, attach tools and knowledge bases. Test it in the live preview pane.",
    icon: Layers,
  },
  {
    step: "03",
    title: "Wire workflows",
    description:
      "When chat isn't enough, drop into the visual editor. Branch, loop, gate, and chain agents together.",
    icon: GitBranch,
  },
  {
    step: "04",
    title: "Ship anywhere",
    description:
      "Embed widget for sites, REST API for backends, MCP server for IDE assistants. One agent, three channels.",
    icon: Zap,
  },
];

