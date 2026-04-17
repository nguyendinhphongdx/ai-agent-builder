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

// --- Node categories for palette grouping ---
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

// --- Handle / Port definitions ---
export interface HandlePort {
  id: string;
  type: "main" | "conditional" | "sub";
  label?: string;
  maxConnections?: number;
  required?: boolean;
}

// Sub-connection definition for AI nodes (model, memory, tools)
export interface SubConnection {
  id: string;
  label: string;
  required?: boolean;
  maxConnections?: number;
}

// --- Config field (temporary — removed in Phase 3 with per-node panels) ---
export interface ConfigField {
  key: string;
  label: string;
  type: "text" | "textarea" | "select" | "number" | "boolean" | "json";
  placeholder?: string;
  options?: { label: string; value: string }[];
  defaultValue?: unknown;
}

// --- Node type definition ---
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
  /** Sub-connections rendered at the bottom (model, memory, tool slots) */
  subConnections?: SubConnection[];
  /** @deprecated Will be removed — use per-node panel.tsx instead */
  configFields?: ConfigField[];
}

// --- Props passed to per-node components ---
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

// --- Registry entry ---
export interface NodeRegistryEntry {
  definition: NodeTypeDefinition;
  node: ComponentType<NodeContentProps>;
  panel: ComponentType<PanelProps>;
}
