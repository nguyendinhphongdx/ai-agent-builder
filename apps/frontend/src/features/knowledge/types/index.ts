export interface KnowledgeBase {
  id: string;
  name: string;
  description: string | null;
  embedding_provider: string;
  embedding_model: string;
  chunk_size: number;
  chunk_overlap: number;
  retrieval_top_k: number;
  total_documents: number;
  total_chunks: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface KBDocument {
  id: string;
  knowledge_base_id: string;
  filename: string;
  file_type: string;
  file_size: number | null;
  chunk_count: number;
  status: "pending" | "processing" | "ready" | "failed";
  error_message: string | null;
  created_at: string;
}
