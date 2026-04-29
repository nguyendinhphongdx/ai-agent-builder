export interface Agent {
  id: string;
  name: string;
  description: string | null;
  avatar_url: string | null;
  system_prompt: string;
  model_id: string;                 // "provider/model" — VD "openai/gpt-4o"
  credential_id: string | null;
  llm_config: Record<string, unknown>;
  welcome_message: string | null;
  max_turns: number;
  is_published: boolean;
  status: string;
  tools: ToolBrief[];
  knowledge_bases: KnowledgeBaseBrief[];
  // Hub provenance — set when this agent was forked from a template.
  template_id: string | null;
  template_version_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgentListItem {
  id: string;
  name: string;
  description: string | null;
  avatar_url: string | null;
  model_id: string;
  credential_id: string | null;
  status: string;
  is_published: boolean;
  created_at: string;
}

export interface ToolBrief {
  id: string;
  name: string;
  description: string;
  tool_type: string;
}

export interface KnowledgeBaseBrief {
  id: string;
  name: string;
  description: string | null;
  embedding_provider: string;
  embedding_model: string;
  total_documents: number;
  total_chunks: number;
}

export interface AgentCreateInput {
  name: string;
  description?: string;
  system_prompt: string;
  model_id?: string;
  credential_id?: string | null;
  llm_config?: Record<string, unknown>;
  welcome_message?: string;
  max_turns?: number;
}

export interface AgentUpdateInput extends Partial<AgentCreateInput> {
  status?: string;
  is_published?: boolean;
  avatar_url?: string;
}
