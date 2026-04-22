import type { ComponentType } from "react";
import type { LucideIcon } from "lucide-react";
import {
  Workflow,
  Bot,
  Database,
  GitBranch,
  Globe,
  Zap,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────────────────────
// Node categories — for palette grouping only. Separate from NodeConnectionType
// which controls edge compatibility.
// ─────────────────────────────────────────────────────────────────────────────
export type NodeCategory = "trigger" | "flow" | "ai" | "data" | "logic" | "integration";

export interface CategoryMeta {
  key: NodeCategory;
  label: string;
  description: string;
  icon: LucideIcon;
}

export const NODE_CATEGORIES: CategoryMeta[] = [
  {
    key: "trigger",
    label: "Triggers",
    description: "Webhook, schedule, and event triggers",
    icon: Zap,
  },
  {
    key: "ai",
    label: "AI",
    description: "LLM calls, agents, and AI tools",
    icon: Bot,
  },
  {
    key: "integration",
    label: "Action in an app",
    description: "HTTP requests, tools, and external services",
    icon: Globe,
  },
  {
    key: "data",
    label: "Data transformation",
    description: "Code, templates, variables, and data processing",
    icon: Database,
  },
  {
    key: "logic",
    label: "Flow control",
    description: "Branch, merge, loop, filter, and delay",
    icon: GitBranch,
  },
  {
    key: "flow",
    label: "Core",
    description: "Start, end, and human input nodes",
    icon: Workflow,
  },
];

// ─────────────────────────────────────────────────────────────────────────────
// NodeConnectionType — n8n-style enum of typed connection points.
// `main` = regular data flow. `ai_*` = specialised AI sub-connections.
// ─────────────────────────────────────────────────────────────────────────────
export const NodeConnectionTypes = {
  Main: "main",
  AiAgent: "ai_agent",
  AiEmbedding: "ai_embedding",
  AiLanguageModel: "ai_languageModel",
  AiMemory: "ai_memory",
  AiOutputParser: "ai_outputParser",
  AiRetriever: "ai_retriever",
  AiReranker: "ai_reranker",
  AiTextSplitter: "ai_textSplitter",
  AiTool: "ai_tool",
  AiVectorStore: "ai_vectorStore",
} as const;

export type NodeConnectionType =
  (typeof NodeConnectionTypes)[keyof typeof NodeConnectionTypes];

export const AI_CONNECTION_TYPES: NodeConnectionType[] = [
  NodeConnectionTypes.AiAgent,
  NodeConnectionTypes.AiEmbedding,
  NodeConnectionTypes.AiLanguageModel,
  NodeConnectionTypes.AiMemory,
  NodeConnectionTypes.AiOutputParser,
  NodeConnectionTypes.AiRetriever,
  NodeConnectionTypes.AiReranker,
  NodeConnectionTypes.AiTextSplitter,
  NodeConnectionTypes.AiTool,
  NodeConnectionTypes.AiVectorStore,
];

export function isAiConnectionType(type: NodeConnectionType): boolean {
  return AI_CONNECTION_TYPES.includes(type);
}

// ─────────────────────────────────────────────────────────────────────────────
// NodeFilter — limits which node types can plug into a port. Mirrors n8n's
// INodeFilter. `undefined` = no constraint. `nodes = []` = allow none.
// ─────────────────────────────────────────────────────────────────────────────
export interface NodeFilter {
  nodes?: string[];          // allow list — only these node types
  excludedNodes?: string[];  // deny list
}

// ─────────────────────────────────────────────────────────────────────────────
// HandlePort — one connection point on a node.
// ─────────────────────────────────────────────────────────────────────────────
export interface HandlePort {
  id: string;
  type: NodeConnectionType;
  label?: string;
  maxConnections?: number;
  required?: boolean;
  filter?: NodeFilter;
}

// ─────────────────────────────────────────────────────────────────────────────
// Config field (will be removed when all nodes have custom panels)
// ─────────────────────────────────────────────────────────────────────────────
export interface ConfigField {
  key: string;
  label: string;
  type: "text" | "textarea" | "select" | "number" | "boolean" | "json";
  placeholder?: string;
  options?: { label: string; value: string }[];
  defaultValue?: unknown;
}

// ─────────────────────────────────────────────────────────────────────────────
// NodeTypeDefinition
// ─────────────────────────────────────────────────────────────────────────────
export interface NodeTypeDefinition {
  type: string;
  label: string;
  description: string;
  icon: LucideIcon;
  color: string;
  category: NodeCategory;
  handles: {
    inputs: HandlePort[];
    outputs: HandlePort[];
  };
  canDelete?: boolean;
  defaultData?: () => Record<string, unknown>;
  canConnect?: (targetType: string) => boolean;
  /** Tailwind rounding classes. Default: "rounded-xl". Use for pill shapes etc. */
  shape?: string;
  /** @deprecated Will be removed — use per-node panel.tsx instead */
  configFields?: ConfigField[];
}

// ─────────────────────────────────────────────────────────────────────────────
// Props
// ─────────────────────────────────────────────────────────────────────────────
export interface NodeContentProps {
  id: string;
  data: NodeData;
}

export interface PanelProps {
  id: string;
  data: NodeData;
}

export interface NodeData {
  nodeType: string;
  label: string;
  config: Record<string, unknown>;
  _customHandles?: boolean;
}

export interface NodeRegistryEntry {
  definition: NodeTypeDefinition;
  node: ComponentType<NodeContentProps>;
  panel: ComponentType<PanelProps>;
}
