export interface Tool {
  id: string;
  name: string;
  description: string;
  tool_type: ToolType;
  config: Record<string, unknown>;
  input_schema: JsonSchema;
  output_schema: JsonSchema | null;
  is_active: boolean;
  timeout_seconds: number;
  created_at: string;
  updated_at: string;
}

export type ToolType =
  | "http_request"
  | "code_exec"
  | "db_query"
  | "web_scrape"
  | "custom_function";

export interface ToolCreateInput {
  name: string;
  description: string;
  tool_type: ToolType;
  config: Record<string, unknown>;
  input_schema: JsonSchema;
  output_schema?: JsonSchema;
  timeout_seconds?: number;
}

export interface ToolUpdateInput {
  name?: string;
  description?: string;
  config?: Record<string, unknown>;
  input_schema?: JsonSchema;
  is_active?: boolean;
  timeout_seconds?: number;
}

export interface ToolTestResult {
  success: boolean;
  result: string | null;
  error: string | null;
  latency_ms: number;
}

export interface JsonSchema {
  type: string;
  properties?: Record<string, { type: string; description?: string; default?: unknown }>;
  required?: string[];
}

export const TOOL_TYPE_META: Record<
  ToolType,
  { label: string; description: string; icon: string; color: string }
> = {
  http_request: {
    label: "HTTP Request",
    description: "Call an external API endpoint",
    icon: "globe",
    color: "blue",
  },
  code_exec: {
    label: "Code Executor",
    description: "Execute Python code in a sandbox",
    icon: "code",
    color: "violet",
  },
  db_query: {
    label: "Database Query",
    description: "Query a database with read-only access",
    icon: "database",
    color: "emerald",
  },
  web_scrape: {
    label: "Web Scraper",
    description: "Extract content from web pages",
    icon: "globe",
    color: "amber",
  },
  custom_function: {
    label: "Custom Function",
    description: "User-defined Python function",
    icon: "wrench",
    color: "rose",
  },
};
