export interface Conversation {
  id: string;
  agent_id: string;
  title: string | null;
  is_pinned: boolean;
  is_archived: boolean;
  total_messages: number;
  total_tokens: number;
  last_message_at: string | null;
  created_at: string;
}

export interface MessageAttachment {
  id: string;
  file_name: string;
  mime_type: string | null;
  size: number | null;
}

/**
 * Rendering context passed through MessageBubble / StreamingBubble /
 * ChatMessageList. Single object so callers can supply avatars, display names,
 * or future role-scoped theming without prop-drilling more fields each time.
 */
export interface ChatRenderMeta {
  user?: {
    name?: string | null;
    avatar?: string | null;
  };
  agent?: {
    name?: string | null;
    avatar?: string | null;
  };
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  content_type: string;
  tool_calls: unknown | null;
  tool_name: string | null;
  attachments?: MessageAttachment[];
  token_usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number } | null;
  latency_ms: number | null;
  llm_model: string | null;
  feedback: string | null;
  created_at: string;
}
