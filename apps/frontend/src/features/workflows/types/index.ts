export interface Workflow {
  id: string;
  name: string;
  description: string | null;
  agent_id: string | null;
  version: number;
  is_active: boolean;
  viewport: { x: number; y: number; zoom: number };
  created_at: string;
  updated_at: string;
}

export interface WorkflowNode {
  id: string;
  workflow_id: string;
  node_type: WorkflowNodeType;
  label: string | null;
  config: Record<string, unknown>;
  position_x: number;
  position_y: number;
  width: number | null;
  height: number | null;
}

export interface WorkflowEdge {
  id: string;
  workflow_id: string;
  source_node_id: string;
  target_node_id: string;
  source_handle: string | null;
  target_handle: string | null;
  label: string | null;
  style: Record<string, unknown>;
}

export type WorkflowNodeType =
  | "start"
  | "end"
  | "llm"
  | "tool"
  | "condition"
  | "human_input"
  | "code"
  | "knowledge_retrieval"
  | "merge"
  | "agent"
  | "http_request"
  | "delay"
  | "template"
  | "switch"
  | "loop"
  | "filter"
  | "set_variable"
  | "webhook_trigger";

export interface WorkflowDetail extends Workflow {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export interface WorkflowCreateInput {
  name: string;
  description?: string;
}

export interface WorkflowSaveInput {
  name?: string;
  description?: string;
  nodes: Omit<WorkflowNode, "workflow_id">[];
  edges: Omit<WorkflowEdge, "workflow_id">[];
  viewport?: { x: number; y: number; zoom: number };
}

export interface NodeTypeDefinition {
  type: WorkflowNodeType;
  label: string;
  description: string;
  icon: string;
  color: string;
  handles: {
    inputs: number;
    outputs: number;
    conditionalOutputs?: string[];
  };
  configFields: ConfigField[];
}

export interface ConfigField {
  key: string;
  label: string;
  type: "text" | "textarea" | "select" | "number" | "boolean" | "json";
  placeholder?: string;
  options?: { label: string; value: string }[];
  defaultValue?: unknown;
}
