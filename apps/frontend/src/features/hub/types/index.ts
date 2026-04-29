export interface TemplateSummary {
  id: string;
  slug: string;
  title: string;
  description: string | null;
  author_name: string;
  category: string | null;
  tags: string[];
  cover_image_url: string | null;
  price_cents: number;
  currency: string;
  is_featured: boolean;
  fork_count: number;
  rating_avg: string | null; // Decimal serialised as string
  rating_count: number;
  published_at: string | null;
}

export interface TemplateDetail extends TemplateSummary {
  user_id: string;
  status: string;
  snapshot: TemplateSnapshot | null;
  current_version: string | null;
  created_at: string;
  updated_at: string;
}

export interface TemplateSnapshot {
  schema_version: number;
  agent: {
    name: string;
    description: string | null;
    avatar_url: string | null;
    system_prompt: string;
    model_id: string;
    llm_config: Record<string, unknown>;
    welcome_message: string | null;
    max_turns: number;
    kb_retrieval_mode: string;
  };
  tools: Array<{
    name: string;
    description: string;
    tool_type: string;
    config: Record<string, unknown>;
    timeout_seconds: number;
  }>;
  knowledge_bases: Array<{
    name: string;
    description: string | null;
    embedding_provider: string | null;
    embedding_model: string | null;
  }>;
  metadata: {
    tool_count?: number;
    kb_count?: number;
    required_credentials?: string[];
  };
}

export interface BrowseResponse {
  items: TemplateSummary[];
  total: number;
  has_more: boolean;
}

export interface BrowseFilters {
  q?: string;
  category?: string;
  tag?: string;
  pricing?: "free" | "paid";
  sort?: "popular" | "newest" | "top-rated" | "cheapest";
  limit?: number;
  offset?: number;
}

export interface PublishInput {
  title: string;
  description?: string;
  author_name?: string;
  category?: string;
  tags?: string[];
  cover_image_url?: string;
  price_cents?: number;
  currency?: string;
}

export interface UpdateTemplateInput {
  title?: string;
  description?: string;
  author_name?: string;
  category?: string;
  tags?: string[];
  cover_image_url?: string;
  price_cents?: number;
  status?: "published" | "archived";
}

export interface ForkResponse {
  agent_id: string;
  template_id: string;
  version_id: string;
  purchase_id: string;
}

export interface Review {
  id: string;
  template_id: string;
  user_id: string;
  user_name: string | null;
  rating: number;       // 1..5
  body: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewInput {
  rating: number;
  body?: string;
}

export interface TemplateVersion {
  id: string;
  template_id: string;
  version: string;
  changelog: string | null;
  is_current: boolean;
  created_at: string;
}

export interface PublishVersionInput {
  bump?: "patch" | "minor" | "major";
  version?: string;        // explicit override (e.g. 0.x → 1.0.0)
  changelog?: string;
}

/** Built-in categories for V1 — matches what filters/dropdown UI offers. */
export const TEMPLATE_CATEGORIES = [
  { value: "support", label: "Customer Support" },
  { value: "marketing", label: "Marketing" },
  { value: "coding", label: "Coding" },
  { value: "writing", label: "Writing" },
  { value: "research", label: "Research" },
  { value: "education", label: "Education" },
  { value: "productivity", label: "Productivity" },
  { value: "other", label: "Other" },
] as const;
